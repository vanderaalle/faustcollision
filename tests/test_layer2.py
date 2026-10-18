"""Layer 2: Faust renders against scsynth NRT renders, per SynthDef × signal × control setting.

The metric and tolerance come from the mapping entries the graph uses (loosest wins).
Faust renders are kept in build/renders/ for listening.
"""
import numpy as np
import pytest
import soundfile as sf

from tests import compare, faustrun
from tests.conftest import BUILD, ROOT, defs, translation

JOBS = [(name, job) for name, meta in defs() for job in meta["jobs"]]


@pytest.mark.parametrize("name,job", JOBS, ids=[f"{n}/{j['tag']}" for n, j in JOBS])
def test_fidelity(name, job, record):
    t = translation(name)
    if t is None:
        pytest.skip("translation failed (see layer 1)")
    x, _ = sf.read(ROOT / "signals" / f"{job['signal']}.wav", dtype="float32")
    ref, _ = sf.read(job["nrt"], dtype="float32", always_2d=True)
    test = faustrun.render(BUILD / "faust" / f"{name}.dsp", x, settings=job["setting"])
    out = BUILD / "renders" / name
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / f"{job['tag']}.wav", test, faustrun.SR, subtype="FLOAT")

    s = compare.score(t["compare"], ref, test)
    ok = s <= t["tol"]
    record(layer=2, **{"def": name}, tag=job["tag"], metric=t["compare"], score=s, tol=t["tol"],
           result="pass" if ok else "FAIL")
    assert np.isfinite(s) and ok, f"{t['compare']} score {s:.4g} > tol {t['tol']}"
