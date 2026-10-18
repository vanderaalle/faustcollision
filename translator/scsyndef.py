"""Parser for the SuperCollider SynthDef binary format (SCgf, versions 1 and 2).

Reference: "SynthDef File Format" in the SuperCollider help. UGens come out in
the file's order, which sclang writes topologically sorted.
"""
import struct
from dataclasses import dataclass, field
from pathlib import Path

RATES = {0: "ir", 1: "kr", 2: "ar", 3: "dr"}


@dataclass(frozen=True)
class Const:
    value: float


@dataclass(frozen=True)
class Ref:
    """Output `output` of UGen number `ugen`."""
    ugen: int
    output: int


@dataclass
class UGen:
    index: int
    cls: str
    rate: str
    special: int
    inputs: list  # of Const | Ref
    output_rates: list


@dataclass
class SynthDef:
    name: str
    constants: list
    params: list  # initial values, by param index
    param_names: dict  # param index -> name
    ugens: list
    variants: dict = field(default_factory=dict)


class _Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0

    def take(self, fmt):
        vals = struct.unpack_from(">" + fmt, self.data, self.pos)
        self.pos += struct.calcsize(">" + fmt)
        return vals if len(vals) > 1 else vals[0]

    def pstring(self):
        n = self.take("B")
        s = self.data[self.pos:self.pos + n].decode("ascii")
        self.pos += n
        return s


def parse(data: bytes) -> list[SynthDef]:
    r = _Reader(data)
    if r.data[:4] != b"SCgf":
        raise ValueError("not a SynthDef file (missing SCgf header)")
    r.pos = 4
    version = r.take("i")
    if version not in (1, 2):
        raise ValueError(f"unsupported SynthDef file version {version}")
    i = "i" if version == 2 else "h"
    defs = []
    for _ in range(r.take("h")):
        name = r.pstring()
        constants = [r.take("f") for _ in range(r.take(i))]
        params = [r.take("f") for _ in range(r.take(i))]
        param_names = {}
        for _ in range(r.take(i)):
            pname = r.pstring()
            param_names[r.take(i)] = pname
        ugens = []
        for u in range(r.take(i)):
            cls = r.pstring()
            rate = RATES[r.take("b")]
            n_in, n_out = r.take(i), r.take(i)
            special = r.take("h")
            inputs = []
            for _ in range(n_in):
                src, idx = r.take(i), r.take(i)
                inputs.append(Const(constants[idx]) if src == -1 else Ref(src, idx))
            out_rates = [RATES[r.take("b")] for _ in range(n_out)]
            ugens.append(UGen(u, cls, rate, special, inputs, out_rates))
        variants = {}
        for _ in range(r.take("h")):
            vname = r.pstring()
            variants[vname] = [r.take("f") for _ in params]
        defs.append(SynthDef(name, constants, params, param_names, ugens, variants))
    return defs


def load(path) -> SynthDef:
    defs = parse(Path(path).read_bytes())
    if len(defs) != 1:
        raise ValueError(f"{path}: expected one SynthDef, found {len(defs)}")
    return defs[0]
