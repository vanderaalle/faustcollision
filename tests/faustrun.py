"""Compile and render generated Faust: DawDreamer for audio, `faust -json` for layer 1."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import dawdreamer as dd
import numpy as np

SR = 48000
BLOCK = 64
ROOT = Path(__file__).resolve().parent.parent
FAUST_DIR = ROOT / "build" / "faust"
# The Daisy target's flags: single precision, denormals flushed to zero (bitmask).
# Layer 3 checks outputs under exactly these flags. -inpl: DawDreamer passes the same
# buffer for input and output; without it, an output written first is read back as
# the input by later outputs.
FAUST_FLAGS = ["-single", "-ftz", "2", "-inpl"]


def faust_cli():
    return shutil.which("faust")


def describe_cli(dsp: Path):
    """Inputs, outputs and control labels from `faust -json` (the reference for layer 1)."""
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run([faust_cli(), "-json", "-I", str(FAUST_DIR), "-O", tmp, "-o", "out.cpp", str(dsp)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"faust failed:\n{proc.stderr}")
        info = json.loads((Path(tmp) / (dsp.name + ".json")).read_text())

    def walk(items):
        for it in items:
            if "items" in it:
                yield from walk(it["items"])
            else:
                yield it
    ui = {it["label"]: it for it in walk(info["ui"]) if it["type"] in ("hslider", "vslider", "nentry")}
    return {"inputs": info["inputs"], "outputs": info["outputs"],
            "controls": {k: {"min": v["min"], "max": v["max"], "default": v["init"]} for k, v in ui.items()}}


def processor(engine, dsp: Path):
    p = engine.make_faust_processor("dsp")
    p.faust_libraries_paths = [str(FAUST_DIR)]
    p.compile_flags = FAUST_FLAGS
    p.set_dsp(str(dsp))
    if not p.compile():
        raise RuntimeError(f"DawDreamer failed to compile {dsp}")
    return p


def describe_libfaust(dsp: Path):
    """Same information through DawDreamer's embedded libfaust, when the faust CLI is absent."""
    engine = dd.RenderEngine(SR, BLOCK)  # must outlive the processor
    p = processor(engine, dsp)
    ctl = {d["label"]: {"min": d["min"], "max": d["max"], "default": d["value"]} for d in p.get_parameters_description()}
    return {"inputs": p.get_num_input_channels(), "outputs": p.get_num_output_channels(), "controls": ctl}


def render(dsp: Path, x: np.ndarray, settings: dict | None = None, automation: dict | None = None):
    """Render mono input `x` through `dsp`. `settings`: constant control values;
    `automation`: control -> per-sample array (same length as x).
    Constant settings render through the C++ a target compiles (render_cpp); automation
    through DawDreamer's JIT (FC_RENDER=dawdreamer forces it). The JIT is not the target
    compiler: its sqrt is not correctly rounded (docs/faust-notes.md)."""
    if automation is None and os.environ.get("FC_RENDER", "cpp") == "cpp":
        return render_cpp(dsp, x, settings)
    return render_dawdreamer(dsp, x, settings, automation)


ARCH = Path(__file__).with_name("arch_render.cpp")
CXX_CACHE = ROOT / "build" / "cxx"


def compile_cpp(dsp: Path) -> Path:
    """faust -> C++ (tests/arch_render.cpp) -> g++ -O2, cached by the content of the program,
    sc.lib, sctables.lib, the architecture and the flags."""
    libdir = Path(dsp).parent if (Path(dsp).parent / "sc.lib").exists() else FAUST_DIR
    h = hashlib.sha256()
    for f in (dsp, libdir / "sc.lib", libdir / "sctables.lib", ARCH):
        h.update(Path(f).read_bytes())
    h.update(" ".join(FAUST_FLAGS).encode())
    exe = CXX_CACHE / f"{Path(dsp).stem}-{h.hexdigest()[:16]}"
    if exe.exists():
        return exe
    CXX_CACHE.mkdir(parents=True, exist_ok=True)
    src = exe.with_suffix(".cpp")
    proc = subprocess.run([faust_cli(), *FAUST_FLAGS, "-I", str(libdir), "-a", str(ARCH), str(dsp), "-o", str(src)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"faust failed:\n{proc.stderr}")
    proc = subprocess.run(["g++", "-O2", "-std=c++17", f"-I{subprocess.run([faust_cli(), '--includedir'], capture_output=True, text=True).stdout.strip()}",
                           str(src), "-o", str(exe)], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"g++ failed:\n{proc.stderr[-3000:]}")
    src.unlink()
    return exe


def render_cpp(dsp: Path, x: np.ndarray, settings: dict | None = None):
    """As render(), through the C++ build: input 0 gets x, other inputs zeros."""
    exe = compile_cpp(dsp)
    n = len(x)
    with tempfile.TemporaryDirectory() as tmp:
        fin, fout = Path(tmp) / "in.f32", Path(tmp) / "out.f32"
        np.asarray(x, dtype=np.float32).tofile(fin)
        args = [str(exe), str(fin), str(fout), str(n)] + [f"{k}={float(v)!r}" for k, v in (settings or {}).items()]
        proc = subprocess.run(args, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"{exe.name} failed ({proc.returncode}): {proc.stderr}")
        y = np.fromfile(fout, dtype=np.float32)
    return y.reshape(-1, n).T  # (samples, channels)


def render_dawdreamer(dsp: Path, x: np.ndarray, settings: dict | None = None, automation: dict | None = None):
    engine = dd.RenderEngine(SR, BLOCK)
    p = processor(engine, dsp)
    params = {d["label"]: d["name"] for d in p.get_parameters_description()}
    for k, v in (settings or {}).items():
        p.set_parameter(params[k], float(v))
    for k, v in (automation or {}).items():
        p.set_automation(params[k], np.asarray(v, dtype=np.float32))
    graph = [(p, [])]
    if p.get_num_input_channels() > 0:
        pb = engine.make_playback_processor("in", np.asarray(x, dtype=np.float32)[None, :])
        graph = [(pb, []), (p, ["in"])]
    engine.load_graph(graph)
    engine.render(len(x) / SR)
    return engine.get_audio()[:, :len(x)].T  # (samples, channels)
