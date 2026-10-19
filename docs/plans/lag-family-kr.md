# Lag family .kr

Prepared, not yet applied or tested. The three open checks are resolved (below); the code reflects them.

- mapping: add `kr = "sc.lag_kr({in}, {lagTime})"` etc. to Lag, Lag2, Lag3, LagUD, Decay,
  Decay2, Integrator, Slew (self_hold = true: the port holds per block itself).
- Lag* .kr with an audio-rate time: kr fed by audio -> codegen's krhold convention applies
  to the inputs? No: self_hold UGens get their raw inputs; check how other self_hold kr
  ports treat audio inputs (a2k vs krhold) before writing.
- Check before porting: Decay_next at inNumSamples 1 (the ramp form: b1 += slope before or
  after the sample) and Slew_next's SAMPLEDUR for kr (mRate->mSampleDur = 64 / SR).
- Cases: each with K2A.ar(X.kr(Latch.kr(in, Impulse.kr(...)), knob)), a knob-swept time
  (coefficient change = jump), a constant time (next_1_i for Lag2/Lag3).
- Tolerances: the ar floors (coefficient in float near 1); fewer steps per second, so
  expect lower.
- Not covered here: OnePole/OneZero/LeakDC/LPF/HPF/RLPF... .kr (each has its own _next_1
  or uses next_a with 1 sample: read each), DelayN/L/C, Comb*, Allpass* .kr (buffer in
  blocks), Saw/Pulse/Blip .kr.


## Resolved checks (FilterUGens.cpp)
- Audio-rate time inputs: a kr unit reads in[0] of the current block (a2k), the
  translator default after the kr-fed-by-audio fix.
- Coefficient change at kr: Lag (Lag_next_1), Lag2 (Lag2_next_k), Lag3, LagUD add the
  slope before the sample: immediate. Decay, Decay2, Integrator add it after the sample
  (CALCSLOPE, slope factor 1): the change applies one block late (as sc-findings 28):
  their kr ports use kprev of the coefficient.
- Slew: upf = up * (float)mSampleDur, dnf = -dn * (float)mSampleDur, read per block;
  level in double (sc_clip of a double slope).

## sc.lib.part

```

//------------------------------------------------------------------------------
// .kr of the lags, decays, integrator, slew (FilterUGens.cpp). A kr unit runs its calc
// function with inNumSamples = 1 (Lag: Lag_next_1; Lag2/Lag3: *_next_1_i for a constant
// time, else the ar function): one step per block on the block's values, SAMPLERATE =
// SR / 64, and the coefficient ramp collapses to a jump (the kr slope factor is 1). The
// state is zapped after every step. Initial states as in the ar ports' constructors.
//------------------------------------------------------------------------------
srk = ma.SR / blocksize;
dec60k(t) = select2(t == 0, 1.0 + expm1f(log(0.001) / (t * srk)), 0.0);
// one recursion stepped at block starts: y = f(x, y1, b), y1 from y0init at time 0
rec1_kr(f, y0init, x, b) = (\(fy).(nv, nv with {
        y1 = select2(ba.time == 0, fy, y0init);
        nv = select2(krclk, y1, zap(f(x, y1, b)));
    })) ~ _ : !, _;
lag_kr(x, t) = rec1_kr(lagstep, x, x, dec60k(t));
lag2_kr(x, t) = rec1_kr(lagstep, x, rec1_kr(lagstep, x, x, b), b) with { b = dec60k(t); };
lag3_kr(x, t) = rec1_kr(lagstep, x, rec1_kr(lagstep, x, rec1_kr(lagstep, x, x, b), b), b) with { b = dec60k(t); };
lagud_kr(x, tu, td) = (\(fy).(nv, nv with {
        y1 = select2(ba.time == 0, fy, x);
        nv = select2(krclk, y1, zap(x + select2(x > y1, dec60k(td), dec60k(tu)) * (y1 - x)));
    })) ~ _ : !, _;
// Decay: y = x + b y1; the constructor step from y1 = 0 leaves in[0]
decay_kr(x, t) = rec1_kr(\(xx, y1, b).(xx + b * y1), x, x, kprev(dec60k(t)));   // one block late
// Decay2: no constructor step (output 0), both states at in[0]; no zap (as the ar port)
decay2_kr(x, at, dt) = d(kprev(dec60k(dt))) - d(kprev(dec60k(at)))   // one block late
with { d(b) = (\(fy).(nv, nv with { y1 = select2(ba.time == 0, fy, x); nv = select2(krclk, y1, x + b * y1); })) ~ _ : !, _; };
// Integrator: y = x + b y1 from 0
integrator_kr(x, coef) = rec1_kr(\(xx, y1, b).(xx + b * y1), 0.0, x, kprev(coef));   // one block late
// Slew: level += clip(in - level, -dn / SRk, up / SRk), level at in[0]
// float sampleDur (64 / SR rounded to float), products in float; level in double: use pairs if the floor demands
slew_kr(x, up, dn) = rec1_kr(\(xx, l, b).(l + max(0.0 - fmul(dn, sd), min(fmul(up, sd), xx - l))), x, x, 0)
with { sd = float(blocksize) / ma.SR; };
```

