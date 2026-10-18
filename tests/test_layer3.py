"""Layer 3: control sweeps on the Faust side only.

Every spec'd control is swept min → max → min (others at default) over each test
signal plus DC and full-scale inputs, followed by 2 s of silence. The output must
be finite, and never stay denormal for a whole block: that marks a recursive state
stuck in denormals, a CPU hazard (sc.lib code is compiled with -ftz 2, as on the
target). Isolated denormal samples from products of decayed signals are counted but
harmless: the codec's integer conversion makes them 0. Units in defs/ must also settle without DC in the
silent tail and stay finite; regression cases (tests/cases/) may output DC (in + x,
free-running oscillators) or NaN (log of a negative input) on purpose, as scsynth
does, so for them both are reported only.
"""
import numpy as np
import pytest
import soundfile as sf

from tests import faustrun
from tests.conftest import BUILD, ROOT, defs, translation

UNITS = {p.stem for p in (ROOT / "defs").glob("*.scd")}

SR = faustrun.SR
TAIL = 2 * SR
DC_TAIL_MAX = 1e-3
FLT_MIN = np.finfo(np.float32).tiny


def longest_run(mask):
    """Longest run of True along axis 0, over all channels."""
    best = 0
    for col in np.atleast_2d(mask.T):
        edges = np.diff(np.concatenate([[0], col.astype(np.int8), [0]]))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)
        best = max(best, int((ends - starts).max()) if len(starts) else 0)
    return best


def inputs():
    # silence.wav is a long render for statistical comparisons; dc and impulse cover it here
    sigs = {p.stem: sf.read(p, dtype="float32")[0] for p in sorted((ROOT / "signals").glob("*.wav")) if p.stem != "silence"}
    sigs["dc"] = np.full(SR, 0.5, dtype=np.float32)
    sigs["fullscale"] = np.clip(sigs["sweep"] * 2.0, -1, 1) if "sweep" in sigs else np.ones(SR, np.float32)
    return sigs


CASES = [(name, sig) for name, _ in defs() for sig in inputs()]


@pytest.mark.parametrize("name,sig", CASES, ids=[f"{n}/{s}" for n, s in CASES])
def test_control_sweep(name, sig, record):
    t = translation(name)
    if t is None:
        pytest.skip("translation failed (see layer 1)")
    x = np.concatenate([inputs()[sig], np.zeros(TAIL, np.float32)])
    n = len(x)
    tri = 1 - np.abs(np.linspace(-1, 1, n - TAIL))  # 0 → 1 → 0 over the signal
    rows = []
    for ctl, spec in t["controls"].items() or [(None, None)]:
        auto = None
        if ctl is not None:
            sweep = spec["min"] + (spec["max"] - spec["min"]) * tri
            auto = {ctl: np.concatenate([sweep, np.full(TAIL, spec["default"])])}
        y = faustrun.render(BUILD / "faust" / f"{name}.dsp", x, automation=auto)
        tail = y[-TAIL // 2:]
        nonfinite = int((~np.isfinite(y)).sum())
        finite = y[np.isfinite(y)]
        denormal = np.isfinite(y) & (y != 0) & (np.abs(y) < FLT_MIN)
        denormals, run = int(denormal.sum()), longest_run(denormal)
        dc_tail = float(np.abs(tail.mean(axis=0)).max()) if np.isfinite(tail).all() else float("inf")
        peak = float(np.abs(finite).max()) if finite.size else float("nan")
        ok = run < faustrun.BLOCK and (name not in UNITS or (nonfinite == 0 and dc_tail <= DC_TAIL_MAX))
        record(layer=3, **{"def": name}, input=f"{sig} ({ctl or 'no controls'})", peak=peak, dc_tail=dc_tail,
               denormals=f"{denormals} (run {run})", nonfinite=nonfinite, result="pass" if ok else "FAIL")
        rows.append((ctl, ok, nonfinite, run, dc_tail))
    bad = [r for r in rows if not r[1]]
    assert not bad, f"(control, ok, non-finite, longest denormal run, tail DC): {bad}"
