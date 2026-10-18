"""Census of core SuperCollider UGens: what the translator covers, and how well.

    .venv/bin/python -m translator.census

1. sclang dumps every core UGen class (translator/census.scd).
2. Classes outside the dialect are excluded by the rules below (buffers, buses,
   demand rate, FFT, server machinery, platform UI).
3. Every remaining class gets a probe SynthDef per rate, every unary and binary
   operator one at audio rate: signal inputs fed by SoundIn, other arguments at
   their defaults, kr outputs through K2A.
4. One sclang batch builds all probes; each is translated. Probes that translate
   are rendered by scsynth (a second batch) and Faust, and scored like layer 2.

Output: report/census.md and report/census.json. Probe sources: build/census/probes/.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from . import scsyndef
from .codegen import TranslationError, load_table, translate

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "census"
REPORT = ROOT / "report"

# Exclusion rules, first match wins. Paths are relative to SCClassLibrary.
EXCLUDE_FILES = {
    r"Common/Audio/(FFT|FFT2|FFTUnpacking|PartConv|MachineListening)\.sc": "FFT / spectral",
    r"Common/Audio/Demand\.sc": "demand rate",
    r"Common/Audio/(BufIO|DiskIO)\.sc": "buffers",
    r"Common/Audio/(Bela/.*|MacUGens)\.sc": "platform / UI",
    r"Common/Audio/Poll\.sc": "server machinery",
    r"(deprecated|JITLib)/.*": "deprecated / JITLib",
}
EXCLUDE_NAMES = {
    "server machinery": {"Done", "FreeSelf", "PauseSelf", "FreeSelfWhenDone", "PauseSelfWhenDone", "Free", "Pause",
                         "SendTrig", "SendReply", "SendPeakRMS", "RandSeed", "RandID", "ScopeOut", "ScopeOut2",
                         "CheckBadValues", "Control", "AudioControl", "TrigControl", "LagControl", "OutputProxy"},
    # covered by the operator probes below
    "operator": {"UnaryOpUGen", "BinaryOpUGen", "MulAdd", "Sum3", "Sum4"},
}
BUS_FILE = r"Common/Audio/InOut\.sc"
BUS_KEEP = {"LocalIn", "LocalOut"}  # in-graph feedback: in the dialect (memorandum, approximate tier)
INFO_FILE = r"Common/Audio/InfoUGens\.sc"
INFO_KEEP = {"SampleRate", "SampleDur", "RadiansPerSample", "ControlRate", "ControlDur", "SubsampleOffset"}

SIGNAL_ARGS = {"in", "input", "in0", "in1", "in2", "in3", "a", "b", "left", "right", "trig", "inA", "inB", "x"}

# Probe bodies for classes whose required arguments cannot be defaulted.
# {rate} is ar or kr; {sig} the input signal at that rate.
OVERRIDES = {
    "DC": "DC.{rate}(0.3)",
    "Pitch": "Pitch.kr(SoundIn.ar(0))",
    "T2K": "T2K.kr(SoundIn.ar(0))",
    "K2A": "K2A.ar(A2K.kr(SoundIn.ar(0)))",
    "A2K": "A2K.kr(SoundIn.ar(0))",
    "AmpCompA": "AmpCompA.{rate}({sig}.abs * 1000 + 50)",
    "AmpComp": "AmpComp.{rate}({sig}.abs * 1000 + 50)",
    "PanAz": "PanAz.{rate}(4, {sig})",
    "DecodeB2": "DecodeB2.{rate}(4, {sig}, {sig} * 0.5, {sig} * 0.25)",
    "InRect": "InRect.{rate}({sig}, {sig} * 0.5, Rect(-0.5, -0.5, 1, 1))",
    "EnvGen": "EnvGen.{rate}(Env.perc(0.01, 0.3), SoundIn.ar(0))",
    "IEnvGen": "IEnvGen.{rate}(Env([0, 1, 0.3, 0], [0.3, 0.3, 0.4]), SoundIn.ar(0).abs)",
    "Klank": "Klank.ar(`[[200, 671, 1153], nil, [1, 1, 1]], SoundIn.ar(0))",
    "DynKlank": "DynKlank.ar(`[[200, 671, 1153], nil, [1, 1, 1]], SoundIn.ar(0))",
    "Klang": "Klang.ar(`[[200, 400], [0.3, 0.2], nil])",
    "DynKlang": "DynKlang.{rate}(`[[200, 400], [0.3, 0.2], nil])",
    "LocalIn": "{{ var fb = LocalIn.{rate}(1); LocalOut.{rate}(SoundIn.ar(0) + (fb * 0.5)); fb }}.value",
    "LocalOut": "{{ var fb = LocalIn.{rate}(1); LocalOut.{rate}(SoundIn.ar(0) + (fb * 0.5)); fb }}.value",
    "Select": "Select.{rate}(SoundIn.ar(0) > 0, [SoundIn.ar(0), SoundIn.ar(0) * 0.5])",
    "TWindex": "TWindex.{rate}(SoundIn.ar(0), [0.3, 0.7])",
    "Splay": "Splay.{rate}([SoundIn.ar(0), SoundIn.ar(0) * 0.5])",
    "SplayAz": "SplayAz.{rate}(2, [SoundIn.ar(0), SoundIn.ar(0) * 0.5])",
}

# Operators by special index, in scsynth order (lang/LangSource/Opcodes.h). None: not a UGen operator.
UNARY = ["neg", "not", None, None, "bitNot", "abs", "asFloat", "asInteger", "ceil", "floor", "frac", "sign",
         "squared", "cubed", "sqrt", "exp", "reciprocal", "midicps", "cpsmidi", "midiratio", "ratiomidi", "dbamp",
         "ampdb", "octcps", "cpsoct", "log", "log2", "log10", "sin", "cos", "tan", "asin", "acos", "atan", "sinh",
         "cosh", "tanh", "rand", "rand2", "linrand", "bilinrand", "sum3rand", "distort", "softclip", "coin", None,
         "silence", "thru", "rectWindow", "hanWindow", "welWindow", "triWindow", "ramp", "scurve"]
BINARY = ["+", "-", "*", "div", "/", "mod", "==", "!=", "<", ">", "<=", ">=", "min", "max", "bitAnd", "bitOr",
          "bitXor", "lcm", "gcd", "round", "roundUp", "trunc", "atan2", "hypot", "hypotApx", "pow", "leftShift",
          "rightShift", "unsignedRightShift", "fill", "ring1", "ring2", "ring3", "ring4", "difsqr", "sumsqr",
          "sqrsum", "sqrdif", "absdif", "thresh", "amclip", "scaleneg", "clip2", "excess", "fold2", "wrap2",
          "firstArg", "rrand", "exprand"]


def sclang(*args):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(["sclang", *map(str, args)], env=env, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        sys.exit(f"sclang failed (exit {proc.returncode}):\n{proc.stdout[-3000:]}")
    return proc.stdout


def classify(u):
    if not [r for r in u["rates"] if r in ("ar", "kr", "ir")]:
        return "abstract or demand-only"
    for pat, why in EXCLUDE_FILES.items():
        if re.fullmatch(pat, u["file"]):
            return why
    for why, names in EXCLUDE_NAMES.items():
        if u["name"] in names:
            return why
    if re.fullmatch(BUS_FILE, u["file"]) and u["name"] not in BUS_KEEP:
        return "buses"
    if re.fullmatch(INFO_FILE, u["file"]) and u["name"] not in INFO_KEEP:
        return "server info"
    if any("buf" in a.lower() and a != "envbufnum" for a, _ in u["args"]):
        return "buffers"
    return None


def probe_body(u, rate):
    sig = "A2K.kr(SoundIn.ar(0))" if rate == "kr" else "SoundIn.ar(0)"
    if u["name"] in OVERRIDES:
        return OVERRIDES[u["name"]].format(rate=rate, sig=sig)
    kwargs = [f"{a}: {sig}" for a, default in u["args"]
              if a in SIGNAL_ARGS or (default == "nil" and a not in ("mul", "add"))]
    return f"{u['name']}.{rate}({', '.join(kwargs)})"


RANDOM_OPS = {"rand", "rand2", "linrand", "bilinrand", "sum3rand", "coin", "rrand", "exprand"}


def probe_source(name, body, signals=("bass_di", "impulse", "noise", "sweep")):
    sigs = ", ".join(f"\\{s}" for s in signals)
    return (f"// Generated by translator/census.py. Do not edit.\n"
            f"SynthDef(\\{name}, {{\n"
            f"\tvar sig = {body};\n"
            f"\tsig = sig.asArray.collect {{ |s| if(s.rate == \\audio) {{ s }} {{ K2A.ar(s) }} }};\n"
            f"\tOut.ar(0, sig);\n"
            f"}}, metadata: (signals: [{sigs}]))\n")


def write_probes(ugens):
    """Returns {probe name: (target label, kind)} and writes the probe files."""
    d = OUT / "probes"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    probes = {}
    for u in ugens:
        if u["category"]:
            continue
        for rate in [r for r in ("ar", "kr") if r in u["rates"]] or ["ir"]:
            name = f"probe_{u['name']}_{rate}"
            (d / f"{name}.scd").write_text(probe_source(name, probe_body(u, rate)))
            probes[name] = {"target": u["name"], "rate": rate, "kind": "ugen"}
    for cls, ops, arity in (("UnaryOpUGen", UNARY, 1), ("BinaryOpUGen", BINARY, 2)):
        for idx, op in enumerate(ops):
            if op is None:
                continue
            name = f"probe_{cls}_{idx:02d}"
            args = "SoundIn.ar(0)" if arity == 1 else "SoundIn.ar(0), DC.ar(0.3)"
            body = f"{cls}.new('{op}', {args})"
            # a random operator scaled by an impulse is one random spike: no comparison
            signals = ("bass_di", "noise", "sweep") if op in RANDOM_OPS else ("bass_di", "impulse", "noise", "sweep")
            (d / f"{name}.scd").write_text(probe_source(name, body, signals))
            probes[name] = {"target": f"{cls} {op}", "rate": "ar", "kind": "operator", "cls": cls, "special": idx}
    return probes


def translate_probe(name, info, table):
    err = OUT / "meta" / f"{name}.sclang_error"
    if err.exists():
        return "sclang error", err.read_text().strip().splitlines()[0][:120], None
    meta = json.loads((OUT / "meta" / f"{name}.json").read_text())
    sdef = scsyndef.load(meta["scsyndef"])
    classes = {u.cls for u in sdef.ugens}
    if info["kind"] == "ugen" and info["target"] not in classes:
        expands = sorted(classes - {"Control", "In", "Out", "NumOutputBuses", "K2A"})
        info["expands_to"] = expands
    try:
        return "translated", None, translate(sdef, meta, table)
    except TranslationError as e:
        msg = str(e)
        m = re.match(r"unmapped UGen class (\w+)", msg)
        if m and (m.group(1) in (info["target"], info.get("cls")) or info.get("expands_to")):
            return "unmapped", None, None
        if "is not mapped (only" in msg:
            return "unmapped", msg, None
        if m:
            return "blocked", f"needs {m.group(1)}", None
        if info["kind"] == "operator" and "special index" in msg:
            return "unmapped", None, None
        return "translation error", msg, None


def score_translated(done):
    """Render translated probes with scsynth and Faust; score like layer 2."""
    sys.path.insert(0, str(ROOT))
    from tests import compare, faustrun
    import soundfile as sf

    d = OUT / "render_probes"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
    for name in done:
        shutil.copy(OUT / "probes" / f"{name}.scd", d)
    faust_dir = OUT / "faust"
    shutil.rmtree(faust_dir, ignore_errors=True)
    faust_dir.mkdir()
    shutil.copy(ROOT / "translator" / "faust" / "sc.lib", faust_dir)
    sclang(ROOT / "translator" / "batch.scd", ROOT, "build/census/rendered", "tolerant", "build/census/render_probes")
    faustrun.FAUST_DIR = faust_dir
    results = {}
    for name, t in done.items():
        meta_path = OUT / "rendered" / "meta" / f"{name}.json"
        if not meta_path.exists():
            results[name] = ("render error", "scsynth batch failed", None)
            continue
        dsp = faust_dir / f"{name}.dsp"
        dsp.write_text(t.code)
        worst = 0.0
        try:
            for job in json.loads(meta_path.read_text())["jobs"]:
                x, _ = sf.read(ROOT / "signals" / f"{job['signal']}.wav", dtype="float32")
                ref, _ = sf.read(job["nrt"], dtype="float32", always_2d=True)
                worst = max(worst, compare.score(t.compare, ref, faustrun.render(dsp, x)))
        except Exception as e:  # a compile failure is a finding, not a crash
            results[name] = ("faust error", str(e).splitlines()[0][:120], None)
            continue
        ok = worst <= t.tol
        results[name] = ("pass" if ok else "fail", f"{t.compare} {worst:.3g} (tol {t.tol:g})", worst)
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for d in ("meta", "synthdefs", "nrt", "rendered"):
        shutil.rmtree(OUT / d, ignore_errors=True)
    print(sclang(ROOT / "translator" / "census.scd", OUT / "ugens.json").strip().splitlines()[-1])
    ugens = json.loads((OUT / "ugens.json").read_text())
    for u in ugens:
        u["category"] = classify(u)
    probes = write_probes(ugens)
    print(f"census: {sum(1 for u in ugens if not u['category'])} candidate classes, {len(probes)} probes")
    sclang(ROOT / "translator" / "batch.scd", ROOT, "build/census", "no-render", "tolerant", "build/census/probes")

    table = load_table()
    done = {}
    for name, info in probes.items():
        status, detail, t = translate_probe(name, info, table)
        info.update(status=status, detail=detail)
        if t:
            done[name] = t
    for name, (status, detail, score) in score_translated(done).items():
        probes[name].update(status=status, detail=detail, score=score)

    REPORT.mkdir(exist_ok=True)
    (REPORT / "census.json").write_text(json.dumps({"ugens": ugens, "probes": probes}, indent=2))
    write_report(ugens, probes)
    print(Counter(p["status"] for p in probes.values()))


def write_report(ugens, probes):
    excluded = Counter(u["category"] for u in ugens if u["category"])
    status = Counter(p["status"] for p in probes.values())
    lines = ["# UGen census", "", "Generated by `python -m translator.census`. Do not edit.", "",
             f"{len(ugens)} core UGen classes; {sum(1 for u in ugens if not u['category'])} in the dialect; "
             f"{len(probes)} probes (per class and rate, plus one per operator).", "",
             "## Excluded classes", "", "| Reason | Classes |", "| --- | --- |"]
    lines += [f"| {why} | {n} |" for why, n in excluded.most_common()]
    lines += ["", "## Probe status", "", "| Status | Probes |", "| --- | --- |"]
    lines += [f"| {s} | {n} |" for s, n in status.most_common()]
    order = ["fail", "faust error", "render error", "translation error", "sclang error", "blocked", "pass", "unmapped"]
    lines += ["", "## Probes", "", "| Target | Rate | Status | Detail |", "| --- | --- | --- | --- |"]
    for name, p in sorted(probes.items(), key=lambda kv: (order.index(kv[1]["status"]), kv[1]["target"])):
        detail = p.get("detail") or ""
        if p.get("expands_to"):
            detail = f"pseudo-UGen → {', '.join(p['expands_to'])}" + (f"; {detail}" if detail else "")
        lines.append(f"| {p['target']} | {p['rate']} | {p['status']} | {detail} |")
    (REPORT / "census.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
