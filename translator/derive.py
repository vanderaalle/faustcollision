"""Compile-time structure of UGens whose sizes scsynth derives in the constructor.

Called by the code generator for mapping entries with `derive = "<name>"`; the inputs
named in the entry's constant_inputs arrive as floats. Each function emulates the
constructor's float32/double arithmetic exactly and returns extra template fields.
The sample rate is fixed at translation time (SR below).
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
    fs = f32(f32(c["freqscale"]) * rps)
    fo = f32(f32(c["freqoffset"]) * rps)
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
