"""Compile-time structure of UGens whose sizes scsynth derives in the constructor.

Called by the code generator for mapping entries with `derive = "<name>"`; the inputs
named in the entry's constant_inputs arrive as floats. Each function emulates the
constructor's float32/double arithmetic exactly and returns extra template fields.
The sample rate is fixed at translation time (SR below).

NumPy 2 computes float32 * Python float in float32. C's float * double is a double
product: write float(f32(x)) * d, then round with f32().
"""
import math

import numpy as np

SR = 48000.0
f32 = np.float32


def _isprime(n):
    lim = int(math.sqrt(f32(n)))
    if n == 2:
        return True
    if n & 1 == 0:
        return False
    return all(n % i for i in range(3, lim + 1, 2))


def _nearestprime(n, rerror):
    if _isprime(n):
        return n
    for k in range(1, int(n * f32(rerror)) + 1):
        if _isprime(n + k):
            return n + k
        if _isprime(n - k):
            return n - k
    return -1


def _f_round(x):
    return int(np.rint(f32(x)))  # the 3 << 22 magic: round half to even


def gverb(c):
    """ReverbUGens.cpp GVerb_Ctor and gverb_set_roomsize."""
    roomsize, spread, maxroom = f32(c["roomsize"]), f32(c["spread"]), f32(c["maxroomsize"])
    ld = f32(SR * float(roomsize) / float(f32(340.0)))           # double, stored float
    maxdelay = f32(SR * float(maxroom) / float(f32(340.0)))
    gbmul = [f32(1.0), f32(0.816490), f32(0.707100), f32(0.632450)]
    gb = [f32(m * ld) for m in gbmul]
    lens_ctor = [_nearestprime(int(gb[0]), 0.5)] + [_f_round(g) for g in gb[1:]]
    diffscale = f32(lens_ctor[3] / float(210 + 159 + 562 + 410))
    dif = {}
    for side, (r1, r2) in (("l", (0.125541, 0.854046)), ("r", (-0.568366, -0.126815))):
        b = 210
        a = int(f32(spread * f32(r1)))
        cc = 210 + 159 + a
        a2 = int(f32(f32(3.0) * spread * f32(r2)))
        d = 210 + 159 + 562 + a2
        sizes = [b, cc - b, d - cc, 1341 - d]
        dif[side] = [_f_round(f32(diffscale * s)) for s in sizes]
    # gverb_set_roomsize (runs at the first block when levels/bandwidth differ from the
    # constructor's zeros): double arithmetic, truncation
    rs = 1.0 if roomsize <= 1.0 else (float(maxroom) - 1.0 if roomsize >= maxroom else float(roomsize))
    lds = f32(SR * rs / 340.0)
    lens_set = [lens_ctor[0]] + [int(m * float(lds)) for m in (0.816490, 0.707100, 0.632450)]
    taps_ctor = [5 + int(m * float(ld)) for m in (0.410, 0.300, 0.155)] + [5]
    taps_set = [5 + int(m * float(lds)) for m in (0.410, 0.300, 0.155)] + [5]
    out = {"fdnsize": int(maxdelay) + 1000}
    for k in range(4):
        out[f"lc{k}"], out[f"ls{k}"] = lens_ctor[k], lens_set[k]
        out[f"tc{k}"], out[f"ts{k}"] = taps_ctor[k], taps_set[k]
        out[f"dl{k}"], out[f"dr{k}"] = dif["l"][k], dif["r"][k]
    return out



def klank(c):
    """OscUGens.cpp Klank_SetCoefs, run once in the constructor. scsynth mixes float and
    double: freqscale/freqoffset times mRadiansPerSample (double) stored as float; R =
    exp(log001 / (time * SR)) in double (log001 is a double), cost with the double cos of
    a float w, stored as float. The two-pole frequency of a low partial is sensitive to one
    ulp of b1, so the coefficients are computed here, exactly as there."""
    rps = 2.0 * math.pi / SR
    log001 = math.log(0.001)
    fs = f32(float(f32(c["freqscale"])) * rps)
    fo = f32(float(f32(c["freqoffset"])) * rps)
    ds = f32(c["decayscale"])
    b1s, b2s, a0s = [], [], []
    for k in range(c["n"]):
        w = f32(f32(f32(c[f"freq{k}"]) * fs) + fo)
        time = f32(f32(c[f"ring{k}"]) * ds)
        R = f32(0.0) if time == 0 else f32(math.exp(log001 / float(f32(time * f32(SR)))))
        twoR = f32(f32(2.0) * R)
        R2 = f32(R * R)
        cost = f32(float(twoR) * math.cos(float(w)) / float(f32(f32(1.0) + R2)))
        b1s.append(f32(twoR * cost))
        b2s.append(-R2)
        a0s.append(f32(float(f32(c[f"amp{k}"])) * 0.25))
    return {k: ", ".join(repr(float(v)) for v in vs) for k, vs in
            (("b1s", b1s), ("b2s", b2s), ("a0s", a0s))}


def pitchshift(c):
    """DelayUGens.cpp PitchShift_Ctor: window size clamped to 3 samples; framesize =
    ((long)(winsize * SR) + 2) & ~3 (double); slope = 2.f / framesize; buffer = next power
    of two of ceil(winsize * SR * 3 + 3) + 64."""
    win = f32(c["windowSize"])
    if float(win) < 3.0 / SR:
        win = f32(3.0 / SR)
    fs = (int(float(win) * SR) + 2) & ~3
    size = int(math.ceil(float(win) * SR * 3.0 + 3.0)) + 64
    return {"fs": fs, "N": 1 << (size - 1).bit_length(), "slope": repr(float(f32(f32(2.0) / f32(fs))))}


def _pair(v):
    hi = f32(v)
    return repr(float(hi)), repr(float(f32(v - float(hi))))


def fsinosc(c):
    """OscUGens.cpp FSinOsc_Ctor: float w = freq * radiansPerSample (a double product);
    b1 = 2 cos(w), y1 = sin(iphase - w), y2 = sin(iphase - 2w), with cos and sin of a float
    argument resolving to cosf and sinf (measured: the double versions do not match).
    Fields for both rates (kr: radians per control period), as float pairs."""
    out = {}
    for rate, sr in (("ar", SR), ("kr", SR / 64)):
        w = f32(float(f32(c["freq"])) * (2.0 * math.pi / sr))
        iphase = f32(c["iphase"])
        vals = {"b": 2.0 * float(f32(math.cos(float(w)))),
                "y1": float(f32(math.sin(float(f32(iphase - w))))),
                "y2": float(f32(math.sin(float(f32(iphase - f32(f32(2.0) * w))))))}
        for k, v in vals.items():
            out[f"{k}h_{rate}"], out[f"{k}l_{rate}"] = _pair(v)
    return out


def line(c):
    """LFUGens.cpp Line_Ctor: counter = (int)(dur * rate + .5f), at least 1; slope =
    (end - start) / counter and level = start + slope, in double (counter 0: level = end,
    slope 0). Fields per rate (ar: 64 * slope too, the nova block step), as float pairs."""
    start, end, dur = (float(f32(c[k])) for k in ("start", "end", "dur"))
    out = {}
    for rate, sr in (("ar", SR), ("kr", SR / 64)):
        n = int(dur * sr + 0.5)
        if n == 0:
            level, slope = end, 0.0
        else:
            slope = (end - start) / n
            level = start + slope
        n = max(1, n)
        out[f"n_{rate}"] = n
        out[f"lh_{rate}"], out[f"ll_{rate}"] = _pair(level)
        out[f"sh_{rate}"], out[f"sl_{rate}"] = _pair(slope)
        out[f"bh_{rate}"], out[f"bl_{rate}"] = _pair(64.0 * slope)
    out["endf"] = repr(float(f32(end)))
    return out


def klang(c):
    """OscUGens.cpp Klang_SetCoefs: w = freq * freqscale + freqoffset (float; freqscale and
    freqoffset are double products stored as float); y1 = level sin(phase - w), y2 =
    level sin(phase - 2w) (phase 0: level -sin(w), level -sin(w + w)), sinf of floats;
    b1 = 2 cos(w), cosf then a double product stored as float."""
    rps = 2.0 * math.pi / SR
    fs = f32(float(f32(c["freqscale"])) * rps)
    fo = f32(float(f32(c["freqoffset"])) * rps)
    sinf = lambda x: f32(math.sin(float(x)))
    y1s, y2s, b1s = [], [], []
    for k in range(c["n"]):
        w = f32(f32(f32(c[f"freq{k}"]) * fs) + fo)
        level, phase = f32(c[f"amp{k}"]), f32(c[f"phase{k}"])
        if phase != 0:
            y1 = f32(level * sinf(f32(phase - w)))
            y2 = f32(level * sinf(f32(f32(phase - w) - w)))
        else:
            y1 = f32(level * -sinf(w))
            y2 = f32(level * -sinf(f32(w + w)))
        y1s.append(y1)
        y2s.append(y2)
        b1s.append(f32(2.0 * float(f32(math.cos(float(w))))))
    return {k: ", ".join(repr(float(v)) for v in vs) for k, vs in
            (("y1s", y1s), ("y2s", y2s), ("b1s", b1s))}


def linexp_calc(rate, r):
    """LFUGens.cpp LinExp_SetCalc: the calc function from the input rates. A pair whose
    calc function reads both bounds per sample with only one at audio rate reads past the
    other's single value (sc-findings 22): rejected."""
    ar = {k: r[k] == "ar" for k in ("srclo", "srchi", "dstlo", "dsthi")}
    if rate == "kr":
        return "kr_i" if all(r[k] == "ir" for k in ar) else "kr_k"
    src, dst = ar["srclo"] or ar["srchi"], ar["dstlo"] or ar["dsthi"]
    if (src and not (ar["srclo"] and ar["srchi"])) or (dst and not (ar["dstlo"] and ar["dsthi"])):
        raise ValueError("an audio-rate range needs both of its bounds at audio rate "
                         "(scsynth reads the other past its value, sc-findings 22)")
    if src or dst:
        return "ar_a"   # next_aa / _ak / _ka: per-sample bounds where audio, libm pow
    return "ar_i" if all(r[k] == "ir" for k in ar) else "ar_k"


def sweep_calc(rate, r):
    """TriggerUGens.cpp Sweep_Ctor: by the trig and rate input rates."""
    if rate == "kr":
        return "kr"
    return ("a" if r["trig"] == "ar" else "k") + ("a" if r["rate"] == "ar" else "k")


def runlevel_calc(rate, r):
    """Peak, RunningMin, RunningMax: next_aa (audio trig), _ak (kr: reset at block end),
    _ai (constant trig: never resets). Peak.kr of an audio input scans the whole current
    block (Peak_next_*_k): not causal, not ported."""
    if rate == "kr":
        if r["in"] == "ar" and r.get("_cls") == "Peak":
            raise ValueError("Peak.kr of an audio input takes the current block's maximum "
                             "(one block ahead of a causal port): not ported")
        return "kr_i" if r["trig"] == "ir" else "kr"
    return {"ar": "a", "kr": "k", "ir": "i"}[r["trig"]]


def change_calc(rate, r):
    """MostChange/LeastChange: at ar with neither input at audio rate scsynth runs next_aa
    and reads both past their single values (sc-findings 21): rejected."""
    if rate == "ar" and r["a"] != "ar" and r["b"] != "ar":
        raise ValueError("at audio rate one input must be audio rate (sc-findings 21)")
    return rate


def t2a(c):
    """T2A writes out[(int)offset] unchecked: only 0 <= offset < 64 is meaningful."""
    off = int(c["offset"])
    if not 0 <= off < 64:
        raise ValueError(f"offset {off} is outside the block (scsynth writes out of bounds)")
    return {"off": off}


def not_causal(rate, r):
    """UGens whose kr value is a function of the current audio block (T2K)."""
    raise ValueError("its control-rate value depends on the whole current audio block; a causal "
                     "port is one block late (measured: up to 35 dB envelope error): not ported")


def section_calc(rate, r):
    """FOS_Ctor / SOS_Ctor: by the coefficient rates (all audio, all constant, else per
    block); kr units run next_1."""
    if rate == "kr":
        return "kr"
    co = [v for k, v in r.items() if k not in ("in", "_cls")]
    if all(v == "ar" for v in co):
        return "a"
    if r["_cls"] == "SOS" and all(v == "ir" for v in co):
        return "i"
    return "k"


# BEQSuite (FilterUGens.cpp:4193-5100): the constructors' double coefficients, from float
# inputs, in the C operation order; w0 = twopi * (double)freq * SAMPLEDUR.
_TWOPI = math.pi * 2.0
_SDUR = 1.0 / SR


def _w0(c):
    return _TWOPI * float(f32(c["freq"])) * _SDUR


def _beq(a0, a1, a2, b1, b2):
    out = {}
    for k, v in (("a0", a0), ("a1", a1), ("a2", a2), ("b1", b1), ("b2", b2)):
        out[f"{k}h"], out[f"{k}l"] = _pair(v)
    return out


def blowpass(c):
    w0 = _w0(c); cosw0 = math.cos(w0); i = 1. - cosw0
    alpha = math.sin(w0) * 0.5 * float(f32(c["rq"])); b0rz = 1. / (1. + alpha)
    a0 = i * 0.5 * b0rz
    return _beq(a0, i * b0rz, a0, cosw0 * 2. * b0rz, (1. - alpha) * -b0rz)


def bhipass(c):
    w0 = _w0(c); cosw0 = math.cos(w0); i = 1. + cosw0
    alpha = math.sin(w0) * 0.5 * float(f32(c["rq"])); b0rz = 1. / (1. + alpha)
    a0 = i * 0.5 * b0rz
    return _beq(a0, -i * b0rz, a0, cosw0 * 2. * b0rz, (1. - alpha) * -b0rz)


def _bwalpha(w0, bw):
    sinw0 = math.sin(w0)
    return sinw0 * (math.sinh((0.34657359027997 * float(f32(bw)) * w0) / sinw0))


def bbandpass(c):
    w0 = _w0(c); alpha = _bwalpha(w0, c["bw"]); b0rz = 1. / (1. + alpha)
    a0 = alpha * b0rz
    return _beq(a0, 0.0, -a0, math.cos(w0) * 2. * b0rz, (1. - alpha) * -b0rz)


def bbandstop(c):
    w0 = _w0(c); alpha = _bwalpha(w0, c["bw"]); b0rz = 1. / (1. + alpha)
    b1 = 2. * b0rz * math.cos(w0)
    return _beq(b0rz, -b1, b0rz, b1, (1. - alpha) * -b0rz)


def ballpass(c):
    w0 = _w0(c); alpha = math.sin(w0) * 0.5 * float(f32(c["rq"])); b0rz = 1. / (1. + alpha)
    a0 = (1. - alpha) * b0rz; b1 = 2. * b0rz * math.cos(w0)
    return _beq(a0, -b1, 1., b1, -a0)


def bpeakeq(c):
    a = math.pow(10., float(f32(c["db"])) * 0.025)
    w0 = _w0(c); alpha = math.sin(w0) * 0.5 * float(f32(c["rq"]))
    b0rz = 1. / (1. + (alpha / a)); b1 = 2. * b0rz * math.cos(w0)
    return _beq((1. + (alpha * a)) * b0rz, -b1, (1. - (alpha * a)) * b0rz, b1, (1. - (alpha / a)) * -b0rz)


def _shelf(c):
    a = math.pow(10., float(f32(c["db"])) * 0.025)
    w0 = _w0(c); cosw0 = math.cos(w0); sinw0 = math.sin(w0)
    alpha = sinw0 * 0.5 * math.sqrt((a + (1. / a)) * (float(f32(c["rs"])) - 1.) + 2.)
    return a, (a + 1.) * cosw0, (a - 1.) * cosw0, 2. * math.sqrt(a) * alpha


def blowshelf(c):
    a, i, j, k = _shelf(c)
    b0rz = 1. / ((a + 1.) + j + k)
    return _beq(a * ((a + 1.) - j + k) * b0rz, 2. * a * ((a - 1.) - i) * b0rz, a * ((a + 1.) - j - k) * b0rz,
                2. * ((a - 1.) + i) * b0rz, ((a + 1.) + j - k) * -b0rz)


def bhishelf(c):
    a, i, j, k = _shelf(c)
    b0rz = 1. / ((a + 1.) - j + k)
    return _beq(a * ((a + 1.) + j + k) * b0rz, -2. * a * ((a - 1.) + i) * b0rz, a * ((a + 1.) + j - k) * b0rz,
                -2. * ((a - 1.) - i) * b0rz, ((a + 1.) - j - k) * -b0rz)


def beq_calc(rate, r):
    """BEQSuite constructors: next_aa(a) when every coefficient input is audio rate
    (sc-findings 24), else next_kk (constants: next_ii, or next_kk without a change: the
    same)."""
    if rate != "ar":
        raise ValueError("only .ar exists")
    co = [v for k, v in r.items() if k not in ("in", "_cls")]
    if all(v == "ar" for v in co):
        return "ar_a"
    return "ar_i" if all(v == "ir" for v in co) else "ar_k"
