# Formant: the phase sync product overflows int32

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

When the fundamental's phase completes a cycle, `Formant` restarts the formant and
bandwidth phases in proportion to the fundamental's overshoot. The product used for that
overflows `int32` for ordinary frequencies, so the phases restart at a small arbitrary
value instead of the intended fraction. The output jitters by up to one sample of the
formant phase at every fundamental period.

## Steps to reproduce

```supercollider
{ Formant.ar(440, 1760, 880) }.plot(0.01);
```

Compare with a model of `Formant_next` computing the products in 64 bits: half the
samples of the first second differ (14.6 % relative RMS). A model wrapping the products
in int32 is bit-exact against scsynth.

## Expected

At the first restart (overshoot `phase1` = 4473848) `phase2 = phase1 * freq2 / freq1`
= 17895393 (3.3 % of a cycle).

## Actual

`phase2` = 118.

## Cause

`server/plugins/OscUGens.cpp:2199`, in `Formant_next`:

```cpp
phase1 -= onecyc13;
phase2 = phase1 * freq2 / freq1;
phase3 = phase1 * freq3 / freq1;
```

All operands are `int32`. `phase1` (up to `freq1`) times `freq2` is of the order of
`freq1 * freq2`, e.g. 4.5e6 × 2e7 for 440/1760 Hz, far beyond 2^31. Signed overflow is
undefined behaviour in C++; x86-64 builds wrap.

## Suggestion

Compute in 64 bits: `phase2 = (int32)((int64)phase1 * freq2 / freq1);` (same for
`phase3`).

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
