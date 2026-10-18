"""SynthDef → Faust code generator, driven by mapping.toml.

One named Faust signal per live UGen output inside a `with` block. SoundIn
becomes a `process` input, Out the outputs, spec'd controls `hslider`s.
Anything the table does not cover is a TranslationError naming the class.
"""
import math
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .scsyndef import Const, Ref, SynthDef

HERE = Path(__file__).parent
MAPPING = HERE / "mapping.toml"
FAUST_LIB_DIR = HERE / "faust"
COMPARE_ORDER = ["waveform", "envelope", "spectrum", "statistics"]


class TranslationError(Exception):
    pass


@dataclass
class Entry:
    """One mapping-table entry as used by a graph (an operator counts as its own entry)."""
    key: str  # "MoogFF", "BinaryOpUGen.pow"
    tier: str
    compare: str
    tol: float
    case: str


@dataclass
class Translation:
    name: str
    code: str
    inputs: int
    outputs: int
    controls: dict  # name -> spec dict
    entries: list  # of Entry, deduplicated, in first-use order

    @property
    def compare(self):
        return max((e.compare for e in self.entries), key=COMPARE_ORDER.index)

    @property
    def tol(self):
        return max(e.tol for e in self.entries if e.compare == self.compare)


def load_table(path=MAPPING):
    with open(path, "rb") as f:
        table = tomllib.load(f)
    for cls, e in table.items():
        kind = e.get("kind", "ugen")
        records = e["operators"].values() if kind == "operator" else [e]
        for rec in records:
            for k in ("compare", "tol", "case"):
                if k not in rec:
                    raise ValueError(f"mapping entry {cls}: missing '{k}'")
            if rec["compare"] not in COMPARE_ORDER:
                raise ValueError(f"mapping entry {cls}: unknown compare '{rec['compare']}'")
    return table


def _literal(v):
    if not math.isfinite(v):
        raise TranslationError(f"non-finite constant {v}")
    s = repr(float(v))
    return f"({s})" if v < 0 else s


def _ident(name):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
        raise TranslationError(f"control name '{name}' is not a valid Faust identifier")
    return name


def translate(sdef: SynthDef, meta: dict, table=None) -> Translation:
    table = table or load_table()
    ugens = sdef.ugens
    specs = meta.get("specs", {})

    def n_out_of(e):
        return e.get("outputs", 1)

    def entry_of(u):
        e = table.get(u.cls)
        if e is None:
            raise TranslationError(f"unmapped UGen class {u.cls}")
        return e

    def input_names(u, e):
        names = e.get("inputs", [])
        if e.get("variadic"):  # trailing inputs in groups (EnvGen: level, time, shape, curve)
            group = e["variadic"]["group"]
            extra = len(u.inputs) - len(names)
            if extra < 0 or extra % len(group):
                raise TranslationError(f"{u.cls}: {extra} trailing inputs do not form groups of {len(group)}")
            return names + [f"{g}{k}" for k in range(extra // len(group)) for g in group]
        if len(names) != len(u.inputs):
            raise TranslationError(f"{u.cls}: binary has {len(u.inputs)} inputs, table lists {len(names)}")
        return names

    def soundin_channel(u):
        # In's bus must be NumOutputBuses (+ constant), i.e. SoundIn.
        bus = u.inputs[0]
        if isinstance(bus, Ref):
            src = ugens[bus.ugen]
            if src.cls == "NumOutputBuses":
                return 0
            if src.cls == "BinaryOpUGen" and src.special == 0:
                a, b = src.inputs
                if isinstance(a, Ref) and ugens[a.ugen].cls == "NumOutputBuses" and isinstance(b, Const):
                    return int(b.value)
        raise TranslationError("In: only SoundIn (bus = NumOutputBuses + constant) is supported")

    outs = [u for u in ugens if entry_of(u).get("kind") == "output"]
    if len(outs) != 1:
        raise TranslationError(f"expected exactly one Out, found {len(outs)}")
    out = outs[0]
    if out.cls != "Out":
        raise TranslationError(f"unsupported output UGen {out.cls}")

    # Live UGens: reachable from Out's signal inputs. In's bus (and Out's) are not followed.
    live, stack = set(), [r.ugen for r in out.inputs[1:] if isinstance(r, Ref)]
    while stack:
        i = stack.pop()
        if i in live:
            continue
        live.add(i)
        u = ugens[i]
        if entry_of(u).get("kind") != "input":
            stack += [r.ugen for r in u.inputs if isinstance(r, Ref)]

    names, lines, controls, entries, channels = {}, [], {}, {}, {}
    control_outputs = set()

    def use(key, rec, tier):
        entries.setdefault(key, Entry(key, tier, rec["compare"], rec["tol"], rec["case"]))

    def expr(inp):
        if isinstance(inp, Const):
            return _literal(inp.value)
        key = (inp.ugen, inp.output)
        if key in control_outputs:  # only controls that are actually read become hsliders
            cname = names[key]
            if cname not in specs:
                raise TranslationError(f"control '{cname}' is used but has no spec in the SynthDef metadata")
            controls[cname] = specs[cname]
            return _ident(cname)
        return names[key]

    for u in ugens:
        e = entry_of(u)
        kind = e.get("kind", "ugen")
        if u.index not in live and kind != "output":
            continue
        if kind == "output":
            use(u.cls, e, e["tier"])
            continue
        if kind == "control":
            use(u.cls, e, e["tier"])
            if u.cls != "Control":
                raise TranslationError(f"unsupported control UGen {u.cls}")
            for k in range(len(u.output_rates)):
                cname = sdef.param_names.get(u.special + k)
                if cname is None:
                    raise TranslationError(f"control output {u.special + k} has no name")
                names[(u.index, k)] = cname
                control_outputs.add((u.index, k))
            continue
        if kind == "input":
            if u.cls != "In":
                raise TranslationError(f"{u.cls} is only legal as the bus of SoundIn")
            use(u.cls, e, e["tier"])
            use("NumOutputBuses", table["NumOutputBuses"], "direct")
            base = soundin_channel(u)
            for k in range(len(u.output_rates)):
                channels[base + k] = f"in{base + k}"
                names[(u.index, k)] = f"in{base + k}"
            continue

        args = dict(zip(input_names(u, e), u.inputs))
        if kind == "operator":
            rec = e["operators"].get(str(u.special))
            if rec is None:
                raise TranslationError(f"unmapped {u.cls} special index {u.special}")
            key = f"{u.cls}.{rec['name']}"
        else:
            rec, key = e, u.cls
        for iname, want in e.get("require", {}).items():
            got = args[iname]
            if not (isinstance(got, Const) and math.isclose(got.value, want, rel_tol=1e-6, abs_tol=1e-9)):
                raise TranslationError(f"{u.cls}: input '{iname}' must be the constant {want}, got {got}")
        for iname in e.get("constant_inputs", []):
            if not isinstance(args[iname], Const):
                raise TranslationError(f"{u.cls}: input '{iname}' must be a constant (scsynth reads it once)")
        for iname in e.get("kr_inputs", []):
            v = args[iname]
            if isinstance(v, Ref) and ugens[v.ugen].rate == "ar":
                raise TranslationError(f"{u.cls}: input '{iname}' must not be audio rate")
        template = rec["faust"]
        if isinstance(template, dict):
            def rate_of(v):
                return ugens[v.ugen].rate if isinstance(v, Ref) else "ir"
            first = u.inputs[0] if u.inputs else None
            # "kr<kr": by the first input's rate; "ar<coef:ar": by a named input's rate
            named = [k for k in template if k.startswith(f"{u.rate}<") and ":" in k
                     and rate_of(args[k.split("<")[1].split(":")[0]]) == k.split(":")[1]]
            if named:
                template = {u.rate: template[named[0]]}
            elif first is not None and f"{u.rate}<{rate_of(first)}" in template:
                template = {u.rate: template[f"{u.rate}<{rate_of(first)}"]}
            if u.rate not in template:
                raise TranslationError(f"{u.cls}.{u.rate} is not mapped (only {', '.join(template)})")
            template = template[u.rate]
        use(key, rec, e["tier"])

        def arg(name, v):
            x = expr(v)
            interp = e.get("kr_interpolate")
            if u.rate == "ar" and (interp is True or (isinstance(interp, list) and name in interp)) \
                    and isinstance(v, Ref) and ugens[v.ugen].rate == "kr":
                return f"sc.kr2ar({x})"
            return x
        # {seed}: a per-node constant, so random operators get independent streams.
        # Signal arguments enter as wires of a lambda: Faust re-expands a named expression at
        # every use inside the library function, which can make compilation explode.
        fixed = set(e.get("inputs", []))
        wires = {k: arg(k, v) for k, v in args.items() if isinstance(v, Ref) and k in fixed}
        fmt = {k: (f"w_{k}" if k in wires else arg(k, v)) for k, v in args.items()}
        if e.get("variadic"):
            group = e["variadic"]["group"]
            n = (len(u.inputs) - len(fixed)) // len(group)
            fmt["n"] = n
            for g in group:  # {levels}, {times}, ...: a Faust parallel list of the group's inputs
                fmt[g + "s"] = ", ".join(arg(f"{g}{k}", args[f"{g}{k}"]) for k in range(n))
        body = template.format(seed=u.index, **fmt)
        if wires:
            body = f"({', '.join(wires.values())}) : \\({', '.join('w_' + k for k in wires)}).({body})"
        if u.rate == "kr" and not e.get("self_hold"):
            # A kr output changes once per block. Fed by audio, the value must come from the
            # previous block (causality): krhold. Fed only by kr inputs (already per block),
            # sample at the block start: a2k. For pure operators that is the identity; for
            # random and stateful ones it gives one value per block, as in scsynth.
            fed_by_audio = any(isinstance(v, Ref) and ugens[v.ugen].rate == "ar" for v in u.inputs)
            hold = "sc.krhold" if fed_by_audio else "sc.a2k"
            body = f"{hold}({body})" if n_out_of(e) == 1 else f"({body}) : par(i, {n_out_of(e)}, {hold})"
        node = f"u{u.index}"
        n_out = n_out_of(e)
        if n_out != len(u.output_rates):
            raise TranslationError(f"{u.cls}: binary has {len(u.output_rates)} outputs, table lists {n_out}")
        lines.append(f"    {node} = {body};")
        if n_out == 1:
            names[(u.index, 0)] = node
        else:
            for k in range(n_out):
                sel = ", ".join("_" if j == k else "!" for j in range(n_out))
                lines.append(f"    {node}_{k} = {node} : {sel};")
                names[(u.index, k)] = f"{node}_{k}"

    if channels and sorted(channels) != list(range(len(channels))):
        raise TranslationError(f"SoundIn channels must be contiguous from 0, got {sorted(channels)}")
    ins = [channels[c] for c in sorted(channels)]
    results = [expr(i) for i in out.inputs[1:]]

    head = [
        f"// Generated by translator/codegen.py from {sdef.name}.scsyndef. Do not edit.",
        f'declare name "{sdef.name}";',
        'import("stdfaust.lib");',
        'sc = library("sc.lib");',
        "",
    ]
    for cname, s in controls.items():
        lo, hi, default = s["min"], s["max"], s["default"]
        scale = {"lin": "", "linear": "", "exp": "[scale:log]", "exponential": "[scale:log]"}.get(s.get("warp", "lin"))
        if scale is None:
            raise TranslationError(f"control '{cname}': unsupported warp {s.get('warp')}")
        head.append(f'{cname} = hslider("{cname}{scale}", {default!r}, {lo!r}, {hi!r}, {(hi - lo) / 10000!r});')
    proc = f"process({', '.join(ins)})" if ins else "process"
    body = [f"{proc} = {', '.join(results)}", "with {", *lines, "};"] if lines else [f"{proc} = {', '.join(results)};"]
    code = "\n".join(head + [""] + body + [""])
    return Translation(sdef.name, code, len(ins), len(results), controls, list(entries.values()))
