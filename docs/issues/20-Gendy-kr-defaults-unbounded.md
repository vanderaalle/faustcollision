# Gendy1/2/3.kr with default arguments output values up to ~1e5

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

With their default arguments, `Gendy1.kr`, `Gendy2.kr` and `Gendy3.kr` produce values far
outside the documented -1..1 range, growing over time. The kr defaults (minfreq 20,
maxfreq 1000, 12 breakpoints; Gendy3 freq 440) make the phase advance by more than one
breakpoint per control period, and the code only steps one breakpoint per sample.

## Steps to reproduce

```supercollider
(
{
    K2A.ar([Gendy1.kr, Gendy2.kr, Gendy3.kr])
}.plot(2)
)
```

## Expected

Values within -1..1 (amplitudes are mirrored into that range), as with
`Gendy1.kr(minfreq: 1, maxfreq: 10)`.

## Actual

(NRT, 10 s.) Max |x|: 1.0e5 (Gendy1), 1.6e5 (Gendy2), 475 (Gendy3).

## Cause

`server/plugins/GendynUGens.cpp`: `Gendy1_next_k` and `Gendy2_next_k` do `if (phase >= 1.0)
{ phase -= 1.0; ... }` once per sample, while `speed = (minfreq + (maxfreq - minfreq) * rate)
* mFreqMul * num` exceeds 1 at control rate (mFreqMul = 1/750); the phase climbs and the
linear interpolation `(1 - phase) * amp + phase * nextamp` extrapolates. `Gendy3_next_k`
steps one region per sample (`if (phase >= nextphase)`), so with regions narrower than the
step, `interp = (phase - lastphase) * interpmult` exceeds 1. At audio rate the same happens
when maxfreq * num exceeds the sample rate.

## Suggestion

Step breakpoints in a `while` loop (`while (phase >= 1.0)`, Gendy3: `while (phase >=
nextphase)`), or clamp the speed; or lower the kr defaults and document the limit.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
