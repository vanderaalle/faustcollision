"""Build everything the tests consume.

    .venv/bin/python -m translator.build [--no-sclang] [--project DIR]

Without --project: the library's own examples/ and tests/cases/, into build/.
With --project DIR: DIR/defs/*.scd into DIR/build/ (signals stay the library's).

1. sclang batch (once): .scsyndef, metadata JSON, scsynth NRT renders.
2. Translate every SynthDef: build/faust/<name>.dsp plus <name>.json
   (I/O, controls, mapping entries used, comparison mode). A failed
   translation writes <name>.error instead and makes the build exit 1.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from . import scsyndef
from .codegen import FAUST_LIB_DIR, TranslationError, load_table, translate

ROOT = Path(__file__).resolve().parent.parent   # the library
BUILD = ROOT / "build"


def sources(project):
    return ["examples", "tests/cases"] if project == ROOT else ["defs"]


def run_sclang(project=ROOT):
    build = project / "build"
    for d in ("synthdefs", "meta", "nrt"):
        shutil.rmtree(build / d, ignore_errors=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(["sclang", str(ROOT / "translator" / "batch.scd"), str(project), "build",
                           f"signals:{ROOT / 'signals'}", *sources(project)],
                          env=env, capture_output=True, text=True, timeout=1800)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("batch:", "ERROR", "ERROR:"))
             and "nonexistent class 'Document'" not in l]
    print("\n".join(lines))
    if proc.returncode != 0:
        sys.exit(f"sclang batch failed (exit {proc.returncode}):\n{proc.stdout[-3000:]}")


def translate_all(project=ROOT):
    build = project / "build"
    out = build / "faust"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    table = load_table()
    failed = []
    for meta_path in sorted((build / "meta").glob("*.json")):
        meta = json.loads(meta_path.read_text())
        name = meta["name"]
        try:
            t = translate(scsyndef.load(meta["scsyndef"]), meta, table)
        except TranslationError as err:
            (out / f"{name}.error").write_text(f"{err}\n")
            print(f"translate: {name}: FAILED: {err}")
            failed.append(name)
            continue
        (out / f"{name}.dsp").write_text(t.code)
        info = {"name": name, "inputs": t.inputs, "outputs": t.outputs, "controls": t.controls,
                "compare": t.compare, "tol": t.tol, "entries": [asdict(e) for e in t.entries]}
        (out / f"{name}.json").write_text(json.dumps(info, indent=2))
        print(f"translate: {name}: {t.inputs} in, {t.outputs} out, {t.compare} ≤ {t.tol}")
    for lib in FAUST_LIB_DIR.glob("*.lib"):   # sc.lib and the generated sctables.lib
        shutil.copy(lib, out / lib.name)
    return failed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-sclang", action="store_true", help="reuse existing sclang outputs")
    ap.add_argument("--project", type=Path, default=ROOT, help="project with a defs/ directory")
    args = ap.parse_args()
    project = args.project.resolve()
    if not args.no_sclang:
        run_sclang(project)
    if translate_all(project):
        sys.exit(1)


if __name__ == "__main__":
    main()
