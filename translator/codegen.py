"""SynthDef → Faust code generator, driven by mapping.toml.

One named Faust signal per live UGen output inside a `with` block. SoundIn
becomes a `process` input, Out the outputs, spec'd controls `hslider`s.
Anything the table does not cover is a TranslationError naming the class.
"""
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .scsyndef import Const, Ref, SynthDef

HERE = Path(__file__).parent
MAPPING = HERE / "mapping.toml"
FAUST_LIB_DIR = HERE / "faust"
IR_FROM_KR = {"UnaryOpUGen", "BinaryOpUGen", "MulAdd", "Sum3", "Sum4"}
COMPARE_ORDER = ["waveform", "envelope", "spectrum", "statistics", "distribution"]


def _lag_b1(lag):
    """IOUGens.cpp LagControl_Ctor: b1 = lag == 0 ? 0 : (float)exp(log001 / (lag * controlRate)),
    lag a float, the rate a double (48000 / 64)."""
    import numpy as np
    lag = float(np.float32(lag))
    return 0.0 if lag == 0 else float(np.float32(math.exp(math.log(0.001) / (lag * (48000.0 / 64)))))


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
    notes: list = field(default_factory=list)  # behaviour worth telling the user

    @property
    def compare(self):
        return max((e.compare for e in self.entries), key=COMPARE_ORDER.index)

    @property
    def tol(self):
        return max(e.tol for e in self.entries if e.compare == self.compare)


EXCLUDED = Path(__file__).with_name("excluded.toml")


def excluded_reason(cls, path=EXCLUDED):
    """The reason a class is excluded by design (translator/excluded.toml), or None."""
    with open(path, "rb") as f:
        ex = tomllib.load(f)
    key = "fft" if cls.startswith("PV_") else ex["classes"].get(cls)
    return ex["reasons"][key] if key else None


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

    def n_out_of(e, u=None):
        # "n": as many as the SynthDef's UGen has (PanAz, DecodeB2: numChans)
        n = e.get("outputs", 1)
        return len(u.output_rates) if n == "n" else n

    def entry_of(u):
        e = table.get(u.cls)
        if e is None:
            why = excluded_reason(u.cls)
            if why:
                raise TranslationError(f"{u.cls}: excluded by design ({why})")
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
        raise TranslationError("In: excluded by design (reads or writes a server bus other than the audio input and output); "
                           "only SoundIn (bus = NumOutputBuses + constant) is translated")

    outs = [u for u in ugens if entry_of(u).get("kind") == "output"]
    if len(outs) != 1:
        raise TranslationError(f"expected exactly one Out, found {len(outs)}")
    out = outs[0]
    if out.cls != "Out":
        raise TranslationError(f"unsupported output UGen {out.cls}")
    if out.rate != "ar":
        raise TranslationError("Out.kr: excluded by design (writes a control bus; the program's outputs are "
                               "audio): use Out.ar")

    # LocalIn/LocalOut: one feedback bus per rate. LocalIn outputs what the LocalOuts of its
    # rate wrote in the previous block (summed in graph order); a LocalOut placed before its
    # LocalIn would feed back within the block, which is not supported.
    local_in, local_outs = {}, {"ar": [], "kr": []}
    for u in ugens:
        kind = entry_of(u).get("kind")
        if kind == "localin":
            if u.rate in local_in:
                raise TranslationError(f"a second LocalIn.{u.rate} (scsynth outputs zeros for it)")
            local_in[u.rate] = u
        elif kind == "localout":
            src = local_in.get(u.rate)
            if src is None:
                raise TranslationError(f"LocalOut.{u.rate} before (or without) a LocalIn.{u.rate}")
            if len(u.inputs) != len(src.output_rates):
                raise TranslationError(f"LocalOut.{u.rate} has {len(u.inputs)} channels, LocalIn "
                                       f"{len(src.output_rates)} (scsynth ignores it)")
            local_outs[u.rate].append(u)

    # Live UGens: reachable from Out's signal inputs (and from the LocalOuts of a live
    # LocalIn). In's bus (and Out's) are not followed.
    live, stack = set(), [r.ugen for r in out.inputs[1:] if isinstance(r, Ref)]
    while stack:
        i = stack.pop()
        if i in live:
            continue
        live.add(i)
        u = ugens[i]
        if entry_of(u).get("kind") == "localin":
            stack += [r.ugen for lo in local_outs[u.rate] for r in lo.inputs if isinstance(r, Ref)]
        if entry_of(u).get("kind") != "input":
            stack += [r.ugen for r in u.inputs if isinstance(r, Ref)]
    feedback = [u for u in local_in.values() if u.index in live and local_outs[u.rate]]

    names, lines, controls, entries, channels = {}, [], {}, {}, {}
    gates = []  # node_alive, doneAction 2: UGens that end the node (every output stops)
    notes = []
    # Out's bus: the Faust outputs are the program's outputs, i.e. bus 0. A control bus (the
    # usual `arg out = 0`) is accepted at a default of 0 and fixed there.
    bus = out.inputs[0]
    if isinstance(bus, Const):
        if bus.value != 0:
            raise TranslationError(f"Out: bus {_literal(bus.value)}; only bus 0 is translated (the program's outputs)")
    elif ugens[bus.ugen].cls in ("Control", "TrigControl", "LagControl"):
        idx = ugens[bus.ugen].special + bus.output
        bname, default = sdef.param_names.get(idx, f"#{idx}"), sdef.params[idx]
        if default != 0:
            raise TranslationError(f"Out: bus control '{bname}' defaults to {_literal(default)}; only bus 0 is translated")
        notes.append(f"Out bus '{bname}' is a control: the program writes bus 0 (its default), whatever it is set to")
    else:
        raise TranslationError("Out: the bus is computed by the graph; only bus 0 is translated")
    control_outputs = set()
    ctl_wrap = {}  # (ugen, output) -> Faust wrapper of the slider (TrigControl, LagControl)

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
            # prefixed: a bare name can clash with stdfaust's environments (db, ba, ma...)
            return ctl_wrap.get(key, "{}").format(f"ctl_{_ident(cname)}")
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
            if u.cls not in ("Control", "TrigControl", "LagControl"):
                raise TranslationError(f"unsupported control UGen {u.cls}")
            for k in range(len(u.output_rates)):
                cname = sdef.param_names.get(u.special + k)
                if cname is None:
                    raise TranslationError(f"control output {u.special + k} has no name")
                names[(u.index, k)] = cname
                control_outputs.add((u.index, k))
                if u.cls == "TrigControl":
                    ctl_wrap[(u.index, k)] = "sc.trigctl({})"
                elif u.cls == "LagControl":
                    lag = u.inputs[k]
                    if not isinstance(lag, Const):
                        raise TranslationError(f"LagControl '{cname}': the lag time must be a constant")
                    ctl_wrap[(u.index, k)] = "sc.lagctl({}, " + _literal(_lag_b1(lag.value)) + ")"
            continue
        if kind == "localout":
            if any(v.rate == u.rate for v in feedback):
                use(u.cls, e, e["tier"])
            continue
        if kind == "localin":
            use(u.cls, e, e["tier"])
            for k, d in enumerate(u.inputs):
                names[(u.index, k)] = f"u{u.index}_{k}"
                # without a LocalOut the bus is never written: the default, every block
                src = f"fb{u.index}_{k}" if local_outs[u.rate] else "0.0"
                fn = "sc.localin" if local_outs[u.rate] else "sc.localin_unwritten"
                # kr: the bus value at the block start (LocalOut.kr wrote its input's first
                # sample of the previous block), held over the block
                hold = "sc.a2k" if u.rate == "kr" else ""
                lines.append(f"    u{u.index}_{k} = {hold}({fn}({expr(d)}, {src}));")
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
        constant = list(e.get("constant_inputs", []))
        if e.get("variadic", {}).get("constant"):  # the whole group is read once
            constant += [k for k in args if k not in e.get("inputs", [])]
        for iname in constant:
            if not isinstance(args[iname], Const):
                raise TranslationError(f"{u.cls}: input '{iname}' must be a constant (scsynth reads it once)")
        for iname in e.get("ar_inputs", []):  # read per sample at ar, whatever its rate
            v = args[iname]
            if u.rate == "ar" and not (isinstance(v, Ref) and ugens[v.ugen].rate == "ar"):
                raise TranslationError(f"{u.cls}.ar: input '{iname}' must be audio rate (scsynth reads "
                                       f"a constant or control input past its one value)")
        for iname in e.get("kr_inputs", []):
            v = args[iname]
            if isinstance(v, Ref) and ugens[v.ugen].rate == "ar":
                raise TranslationError(f"{u.cls}: input '{iname}' must not be audio rate")
        template = rec["faust"]
        # derive_when_constant: the exact template (with derive) when these inputs are
        # constants, otherwise faust_var (an approximation documented in the entry)
        exact = all(isinstance(args[k], Const) for k in e.get("derive_when_constant", []))
        if not exact:
            template = rec["faust_var"]
        if e.get("template_by"):  # the calc function from all input rates (translator/derive.py)
            from . import derive
            rates = {k: (ugens[v.ugen].rate if isinstance(v, Ref) else "ir") for k, v in args.items()}
            rates["_cls"] = u.cls
            try:
                template = {u.rate: template[getattr(derive, e["template_by"])(u.rate, rates)]}
            except ValueError as err:
                raise TranslationError(f"{u.cls}: {err}")
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
            if u.rate == "ir" and "ir" not in template and "kr" in template and u.cls in IR_FROM_KR:
                # a scalar-rate operator: its constructor computes one value with the scalar
                # (kr) function; held from the first sample (initv), so random operators draw once
                template = {"ir": "sc.initv(" + template["kr"] + ")"}
            if u.rate not in template:
                raise TranslationError(f"{u.cls}.{u.rate} is not mapped (only {', '.join(template)})")
            template = template[u.rate]
        use(key, rec, e["tier"])

        def arg(name, v):
            x = expr(v)
            interp = e.get("kr_interpolate")
            krin = u.rate == "ar" and isinstance(v, Ref) and ugens[v.ugen].rate == "kr"
            if krin and (interp is True or (isinstance(interp, list) and name in interp)):
                return f"sc.kr2ar({x})"
            # kr_wrap: {input: function} applied to a kr input of an ar UGen (the UGen's own
            # per-block ramp of that input)
            if krin and name in e.get("kr_wrap", {}):
                return f"{e['kr_wrap'][name]}({x})"
            return x
        # {seed}: a per-node constant, so random operators get independent streams.
        # Signal arguments enter as wires of a lambda: Faust re-expands a named expression at
        # every use inside the library function, which can make compilation explode.
        fixed = set(e.get("inputs", []))
        wires = {k: arg(k, v) for k, v in args.items() if isinstance(v, Ref) and k in fixed}
        fmt = {k: (f"w_{k}" if k in wires else arg(k, v)) for k, v in args.items()}
        if e.get("derive") and exact:  # constructor-time structure (translator/derive.py)
            from . import derive
            consts = {k: args[k].value for k in constant + e.get("derive_when_constant", [])}
            consts["_nout"] = len(u.output_rates)
            if e.get("variadic"):
                consts["n"] = (len(u.inputs) - len(fixed)) // len(e["variadic"]["group"])
            try:
                fmt.update(getattr(derive, e["derive"])(consts))
            except ValueError as err:
                raise TranslationError(f"{u.cls}: {err}")
        if e.get("variadic"):
            group = e["variadic"]["group"]
            n = (len(u.inputs) - len(fixed)) // len(group)
            fmt["n"] = n
            for g in group:  # {levels}, {times}, ...: a Faust parallel list of the group's inputs
                fmt[g + "s"] = ", ".join(arg(f"{g}{k}", args[f"{g}{k}"]) for k in range(n))
        fmt.setdefault("nout", len(u.output_rates))
        body = template.format(seed=u.index, **fmt)
        if e.get("node_alive"):
            gates.append(e["node_alive"].format(seed=u.index, **fmt))
        wrap = (lambda b: f"({', '.join(wires.values())}) : \\({', '.join('w_' + k for k in wires)}).({b})") if wires else (lambda b: b)
        if e.get("done_input"):
            # doneAction: 0 nothing; 2 frees the synth when the UGen is done (the port's
            # <function>_end companion, same arguments): every output stops after that block
            da = args[e["done_input"]]
            if not isinstance(da, Const) or da.value not in (0.0, 2.0):
                raise TranslationError(f"{u.cls}: doneAction must be the constant 0 or 2 (other done actions act "
                                       f"on other nodes), got {da}")
            if da.value == 2.0:
                end = re.sub(r"sc\.(\w+)\(", r"sc.\1_end(", body, count=1)
                gates.append(f"sc.alive({wrap(end)})")
                notes.append(f"{u.cls} doneAction 2: the whole program falls silent for good once it is done")
        body = wrap(body)
        if u.rate == "kr" and not e.get("self_hold"):
            # A kr output changes once per block. A kr unit runs one sample per block and
            # reads in[0] of an audio input: the current block's first sample, known at the
            # block start, so a2k (measured: Splay.kr -> Pan2.kr of an audio input). Entries
            # whose kr calc function consumes the whole audio block (kr_block: Amplitude's
            # atok, Pitch_next_a) cannot be known before the block ends: the previous
            # block's value (causality), krhold. For pure operators a2k is the identity;
            # for random and stateful ones it gives one value per block, as in scsynth.
            fed_by_audio = any(isinstance(v, Ref) and ugens[v.ugen].rate == "ar" for v in u.inputs)
            hold = "sc.krhold" if fed_by_audio and e.get("kr_block") else "sc.a2k"
            body = f"{hold}({body})" if n_out_of(e, u) == 1 else f"({body}) : par(i, {n_out_of(e, u)}, {hold})"
        node = f"u{u.index}"
        n_out = n_out_of(e, u)
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
    if gates:  # a freed node writes nothing: every output gated
        results = [f"({r}) * ({' * '.join(gates)})" for r in results]

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
        head.append(f'ctl_{cname} = hslider("{cname}{scale}", {default!r}, {lo!r}, {hi!r}, {(hi - lo) / 10000!r});')
    proc = f"process({', '.join(ins)})" if ins else "process"
    body = [f"{proc} = {', '.join(results)}", "with {", *lines, "};"] if lines else [f"{proc} = {', '.join(results)};"]
    if feedback:
        # The graph inside a recursion: its first outputs, the LocalOut sums, come back
        # (one sample later) as the fb wires; sc.localin delays them to one block.
        fbs, sums = [], []
        for u in feedback:
            for k in range(len(u.output_rates)):
                fbs.append(f"fb{u.index}_{k}")
                terms = [expr(lo.inputs[k]) for lo in local_outs[u.rate]]
                s = terms[0]
                for t in terms[1:]:
                    s = f"sc.fadd({s}, {t})"
                sums.append(s)
        body = [f"process = (\\({', '.join(fbs + ins)}).(({', '.join(sums + results)})",
                "with {", *lines, f"}})) ~ si.bus({len(fbs)}) : si.block({len(fbs)}), si.bus({len(results)});"]
    code = "\n".join(head + [""] + body + [""])
    return Translation(sdef.name, code, len(ins), len(results), controls, list(entries.values()), notes)
