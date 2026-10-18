"""Shared fixtures: builds once per session (sclang runs once), collects results into report/."""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
REPORT = ROOT / "report"
RESULTS = []


def pytest_addoption(parser):
    parser.addoption("--rebuild", action="store_true", help="rerun the sclang batch and the translator")


def pytest_configure(config):
    if config.getoption("--rebuild") or not (BUILD / "meta").exists():
        subprocess.run([sys.executable, "-m", "translator.build"], cwd=ROOT)  # failures surface in layer 1
    elif not (BUILD / "faust").exists():
        subprocess.run([sys.executable, "-m", "translator.build", "--no-sclang"], cwd=ROOT)


def defs():
    """Every SynthDef the batch saw: (name, meta)."""
    return [(p.stem, json.loads(p.read_text())) for p in sorted((BUILD / "meta").glob("*.json"))]


def translation(name):
    p = BUILD / "faust" / f"{name}.json"
    return json.loads(p.read_text()) if p.exists() else None


@pytest.fixture
def record():
    def add(**row):
        RESULTS.append(row)
    return add


def pytest_sessionfinish(session):
    if not RESULTS:
        return
    REPORT.mkdir(exist_ok=True)
    (REPORT / "results.json").write_text(json.dumps(RESULTS, indent=2))
    lines = [f"# Fidelity report", "", f"Generated {datetime.now():%Y-%m-%d %H:%M} by pytest. Do not edit.", ""]
    for layer, title in [(1, "Layer 1: compile, I/O, controls"), (2, "Layer 2: fidelity vs scsynth NRT"),
                         (3, "Layer 3: control sweeps")]:
        rows = [r for r in RESULTS if r["layer"] == layer]
        if not rows:
            continue
        lines += [f"## {title}", ""]
        if layer == 1:
            lines += ["| SynthDef | Result | Backend | Detail |", "| --- | --- | --- | --- |"]
            lines += [f"| {r['def']} | {r['result']} | {r.get('backend', '')} | {r.get('detail', '')} |" for r in rows]
        elif layer == 2:
            lines += ["| SynthDef | Render | Metric | Score | Tol | Result |", "| --- | --- | --- | --- | --- | --- |"]
            lines += [f"| {r['def']} | {r['tag']} | {r['metric']} | {r['score']:.4g} | {r['tol']:.4g} | {r['result']} |"
                      for r in rows]
        else:
            lines += ["| SynthDef | Input | Peak | DC (tail) | Denormals | Non-finite | Result |",
                      "| --- | --- | --- | --- | --- | --- | --- |"]
            lines += [f"| {r['def']} | {r['input']} | {r['peak']:.3g} | {r['dc_tail']:.2g} | {r['denormals']} | "
                      f"{r['nonfinite']} | {r['result']} |" for r in rows]
        lines.append("")
    (REPORT / "fidelity.md").write_text("\n".join(lines))
