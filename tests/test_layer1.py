"""Layer 1: every SynthDef translates, the Faust compiles, and I/O and controls match the SynthDef."""
from pathlib import Path

import pytest

from translator.codegen import load_table
from tests import faustrun
from tests import conftest
from tests.conftest import ROOT, defs, translation

DEFS = defs()


def test_every_mapping_entry_has_a_case():
    if conftest.PROJECT != ROOT:
        pytest.skip("library check (run without --project)")
    cases = {name for name, meta in DEFS if "/tests/cases/" in meta["source"]}
    missing = []
    for cls, e in load_table().items():
        for rec in (e["operators"].values() if e.get("kind") == "operator" else [e]):
            # a rejected entry (tier "rejected") is covered by a translator test instead
            if e.get("tier") == "rejected" and rec["case"].startswith("tests/test_translator.py::"):
                continue
            if rec["case"] not in cases:
                missing.append(f"{cls}: {rec['case']}")
    assert not missing, f"mapping entries without a regression case: {missing}"


@pytest.mark.parametrize("name,meta", DEFS, ids=[d[0] for d in DEFS])
def test_translates_and_compiles(name, meta, record):
    err = conftest.BUILD / "faust" / f"{name}.error"
    if err.exists():
        record(layer=1, **{"def": name}, result="FAIL", detail=err.read_text().strip())
        pytest.fail(f"translation failed: {err.read_text().strip()}")
    t = translation(name)
    dsp = conftest.BUILD / "faust" / f"{name}.dsp"
    backend = "faust -json" if faustrun.faust_cli() else "libfaust (DawDreamer)"
    info = faustrun.describe_cli(dsp) if faustrun.faust_cli() else faustrun.describe_libfaust(dsp)

    problems = []
    if info["inputs"] != t["inputs"]:
        problems.append(f"inputs {info['inputs']} != {t['inputs']}")
    if info["outputs"] != meta["numOutputs"]:
        problems.append(f"outputs {info['outputs']} != SynthDef's {meta['numOutputs']}")
    if set(info["controls"]) != set(t["controls"]):
        problems.append(f"controls {sorted(info['controls'])} != {sorted(t['controls'])}")
    for k, spec in t["controls"].items():
        got = info["controls"].get(k)
        if got and any(abs(got[f] - spec[f]) > 1e-6 * max(1, abs(spec[f])) for f in ("min", "max", "default")):
            problems.append(f"control {k}: {got} != spec {spec}")
    record(layer=1, **{"def": name}, result="FAIL" if problems else "pass", backend=backend,
           detail="; ".join(problems) or f"{t['inputs']} in, {t['outputs']} out, controls {sorted(t['controls'])}")
    assert not problems, problems
