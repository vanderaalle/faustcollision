# NRand returns NaN with its default arguments

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`NRand.new` with its default arguments outputs NaN. The class's default is `n = 0`, and the
constructor divides the sum of the n draws by n: 0 / 0. The NaN then propagates through
everything the value feeds. The help file's example also starts with `n = 0`.

## Steps to reproduce

```supercollider
{ [NRand.new, NRand(0, 1, 0), NRand(0, 1, 3)] * DC.ar(1) }.plot(0.01)
```

## Expected

A value between lo and hi, e.g. one uniform draw (the class comment: "n = 1 : uniform
distribution - same as Rand").

## Actual

(NRT.) `NRand.new` and `NRand(0, 1, 0)`: NaN. `NRand(0, 1, 3)`: a value in 0..1.

## Cause

`server/plugins/NoiseUGens.cpp`, `NRand_Ctor`: `for (int i = 0; i < n; ++i) sum +=
rgen.frand(); ZOUT0(0) = (sum / n) * range + lo;` with n = 0. `Noise.sc`: `*new { arg lo =
0.0, hi = 1.0, n = 0; ... }`.

## Suggestion

Change the default to `n = 1`, and clamp n to at least 1 in the constructor.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
