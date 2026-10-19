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


def median(c):
    """FilterUGens.cpp Median_Ctor: size = sc_clip((int)length, 0, kMAXMEDIANSIZE = 32).
    Size 0 indexes values[-1] in Median_InsertMedian: rejected."""
    n = min(max(int(c["length"]), 0), 32)
    if n == 0:
        raise ValueError("length < 1 makes Median_InsertMedian index values[-1]")
    return {"n": n}


def server_info(c):
    """DelayUGens.cpp:434-448: values the constructor writes once, doubles cast to float;
    the sample rate is fixed at translation time (SR)."""
    return {"sr": repr(float(f32(SR))), "cr": repr(float(f32(SR / 64))), "sdur": repr(float(f32(1.0 / SR))),
            "cdur": repr(float(f32(64.0 / SR))), "rps": repr(float(f32(2.0 * math.pi / SR)))}


def ampcomp_calc(rate, r):
    """LFUGens.cpp AmpComp_Ctor: AmpComp_next when root and exp are constants, else
    AmpComp_next_kk."""
    return f'{rate}_{"i" if r["root"] == "ir" and r["exp"] == "ir" else "k"}'


def ampcomp(c):
    """AmpComp_Ctor: rootmul = pow(root, exp) (float pow), exponent = -1.f * exp."""
    root, ex = f32(c["root"]), f32(c["exp"])
    return {"rootmul": repr(float(f32(np.power(root, ex)))), "xb": repr(float(f32(-1.0) * ex))}


def ampcompa(c):
    """AmpCompA_Ctor: rootLevel = AmpCompA_calcLevel(root) in double; scale = (rootAmp -
    minAmp) / (rootLevel - MINLEVEL), offset = minAmp - scale * MINLEVEL (doubles), used
    as doubles with a double level (here: their float values)."""
    K = 3.5041384 * 10e15
    C1, C2, C3, C4 = 20.598997 ** 2, 107.65265 ** 2, 737.86223 ** 2, 12194.217 ** 2
    MIN = -0.1575371167435

    def level(f):
        r = f * f
        lv = K * r * r * r * r
        n1, n2 = C1 + r, C4 + r
        return 1.0 - math.sqrt(lv / (n1 * n1 * (C2 + r) * (C3 + r) * n2 * n2))
    root = float(f32(c["root"])); minamp = float(f32(c["minAmp"])); rootamp = float(f32(c["rootAmp"]))
    scale = (float(f32(rootamp)) - minamp) / (level(root) - MIN)
    offset = minamp - scale * MIN
    return {"scale": repr(scale), "offset": repr(offset)}


def ienvgen(c):
    """LFUGens.cpp IEnvGen (3155-3260, GET_ENV_VAL 3172): the envelope is read once in the
    constructor; this builds the lookup as a Faust expression of the point p = max(index -
    offset, 0). Stage: the first j with p < cum_j (durations summed in float, as the C's
    newtime); pos = (p - d0 - ... - dj + dj) / dj in sequential float steps; shapes as
    GET_ENV_VAL, the curvature truncated to int (sc-findings 27). Hold depends on the
    previous lookup: rejected."""
    n = int(c["numStages"])
    if n < 1:
        raise ValueError("an envelope with no stages")
    lv = [float(f32(c["initLevel"]))] + [float(f32(c[f"level{k}"])) for k in range(n)]
    du = [float(f32(c[f"dur{k}"])) for k in range(n)]
    sh = [int(f32(c[f"shape{k}"])) for k in range(n)]
    cv = [int(f32(c[f"curve{k}"])) for k in range(n)]
    if 8 in sh:
        raise ValueError("the hold shape returns the previous lookup's level (stateful): not ported")
    cum, acc = [], f32(0.0)
    for d in du:
        acc = f32(acc + f32(d)); cum.append(float(acc))
    total = float(f32(c["totalDur"]))
    r = repr
    segs = []
    for j in range(n):
        s = "p"
        for k in range(j + 1):
            s = f"sc.fsub({s}, {r(du[k])})"
        s = f"sc.fadd({s}, {r(du[j])})"
        pos = f"({s} / {r(du[j])})"
        b, e, shape, cu = lv[j], lv[j + 1], sh[j], cv[j]
        if shape == 0:
            v = r(e)
        elif shape == 2:
            v = f"({r(b)} * pow({r(e)} / {r(b)}, {pos}))"
        elif shape == 3:
            v = f"({r(b)} + ({r(e)} - {r(b)}) * (0.0 - cos(ma.PI * {pos}) * 0.5 + 0.5))"
        elif shape == 4:
            v = (f"({r(b)} + ({r(e)} - {r(b)}) * sin(ma.PI * 0.5 * {pos}))" if b < e
                 else f"({r(e)} - ({r(e)} - {r(b)}) * sin(ma.PI * 0.5 - ma.PI * 0.5 * {pos}))")
        elif shape == 5 and abs(float(cu)) >= 0.0001:
            v = f"({r(b)} + ({r(e)} - {r(b)}) * ((1.0 - exp({pos} * {r(float(cu))})) / (1.0 - exp({r(float(cu))}))))"
        elif shape == 6:
            v = f"(({pos} * (sqrt({r(e)}) - sqrt({r(b)})) + sqrt({r(b)})) : \\(q).(q * q))"
        elif shape == 7:
            v = f"(({pos} * (pow({r(e)}, 0.3333333) - pow({r(b)}, 0.3333333)) + pow({r(b)}, 0.3333333)) : \\(q).(q * q * q))"
        else:  # linear (1), default, and a curve with |curve| < 1 (truncated to 0)
            v = f"({pos} * ({r(e)} - {r(b)}) + {r(b)})"
        segs.append(v)
    seg = segs[-1]
    for j in range(n - 2, -1, -1):
        seg = f"select2(p < {r(cum[j])}, {seg}, {segs[j]})"
    expr = f"select2(p >= {r(total)}, select2(p <= 0.0, {seg}, {r(lv[0])}), {r(lv[n])})"
    return {"expr": expr, "off": r(float(f32(c["offset"])))}


def pluck_calc(rate, r):
    """DelayUGens.cpp Pluck_Ctor: by the trigger and coef rates (aa, ak, ka, kk)."""
    return f'ar_{"a" if r["trig"] == "ar" else "k"}{"a" if r["coef"] == "ar" else "k"}'


_HILBERT_K = (0.3609, 2.7412, 11.1573, 44.7581, 179.6242, 798.4578, 1.2524, 5.5671, 22.3423, 89.6271, 364.7914, 2770.1114)


def hilbert(c):
    """FilterUGens.cpp Hilbert_Ctor: gamconst = (15.0f * pi_f) / SAMPLERATE (a float product,
    then double), gamma = gamconst * k (float literals), coef = (gamma - 1) / (gamma + 1) in
    double; the loop uses them as floats."""
    g0 = float(f32(f32(15.0) * f32(math.pi))) / SR
    cs = []
    for k in _HILBERT_K:
        g = g0 * float(f32(k))
        cs.append(repr(float(f32((g - 1.0) / (g + 1.0)))))
    return {"cs": ", ".join(cs)}


def freqshift(c):
    """FilterUGens.cpp FreqShift_Ctor: gamconst = (15.0 * pi) / SAMPLERATE in double; m_coefs
    are floats (used as doubles in the loop)."""
    g0 = (15.0 * math.pi) / SR
    cs = []
    for k in _HILBERT_K:
        g = g0 * float(f32(k))
        cs.append(repr(float(f32((g - 1.0) / (g + 1.0)))))
    return {"cs": ", ".join(cs)}
