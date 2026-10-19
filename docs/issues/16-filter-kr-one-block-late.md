# Resonz.kr, Ringz.kr, TwoPole.kr, TwoZero.kr, MidEQ.kr, OneZero.kr apply coefficient changes one block late; APF.kr passes its input through

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

At control rate, several filters keep using their old coefficients for the block in which
`freq` (or another coefficient input) changes; the new coefficients take effect from the
next block. `LPF.kr`, `HPF.kr`, `RLPF.kr`, `RHPF.kr`, `BPF.kr`, `BRF.kr`, `Formlet.kr`
and `LeakDC.kr` use the new values at once. `APF.kr` outputs its input unchanged.

## Steps to reproduce

```supercollider
(
{
    var x = LFNoise0.kr(200);
    var f = (Line.kr(0, 1, 0.5) >= 1) * 40 + 30;   // 30 -> 70 Hz at 0.5 s
    K2A.ar([Resonz.kr(x, f, 0.5), APF.kr(x, 50, 0.9), x])
}.plot(1)
)
```

## Expected

Coefficients follow `freq` in the block where it changes (as `LPF.kr` does); `APF.kr`
filters its input.

## Actual

(NRT.) A double-precision simulation applying new coefficients one block late is
bit-exact for `Resonz.kr`, `Ringz.kr`, `TwoPole.kr`, `TwoZero.kr`, `MidEQ.kr` and
`OneZero.kr`; applying them at once differs by up to 0.94 (Resonz), 5.6 (TwoPole).
`APF.kr(x, 50, 0.9)` equals `x` on every block.

## Cause

At control rate the buffer length is 1, so `mFilterLoops` = 0, `mFilterRemain` = 1 and
`mFilterSlope` = 0 (`server/scsynth/SC_Rate.cpp:34-40`). These filters run their unrolled
audio-rate function at control rate (they have no `_next_1`): on a change the slopes are
`(next - current) * mFilterSlope` = 0, the single remainder sample uses the old
coefficients, and the new ones are only stored. `OneZero_next` adds its `CALCSLOPE` step
after the sample, to the same effect. `APF.kr` runs only the remainder loop, whose
per-sample formula has equal numerator and denominator (see the APF issue): the identity.

## Suggestion

Give these filters a `_next_1` that computes the coefficients and uses them at once (as
`LPF_next_1` does), or set `mFilterSlope` so that the remainder sample reaches the new
value at control rate.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
