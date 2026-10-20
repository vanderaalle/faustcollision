# Gendy2 and Gendy3 exceed ±1: Gendyn_mirroring folds values below the lower bound out of range

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`Gendy2` and `Gendy3` mirror their random walks back into range with `Gendyn_mirroring`.
A value below the lower bound is folded to the wrong side: for the amplitude walk in
[-1, 1], -1 - d becomes 1 + d. The output then exceeds ±1 regularly, with default
arguments.

## Steps to reproduce

```supercollider
(
{
    [Gendy1.ar, Gendy2.ar, Gendy2.ar(ampscale: 1, durscale: 1)]
}.plot(0.5)
)
```

## Expected

Values within -1..1 (as `Gendy1`, which folds with its own code).

## Actual

(NRT, 10 s.) `Gendy2.ar`: max |x| 1.475, 2.9 % of the samples beyond ±1; with ampscale
and durscale 1: 1.96, 5.7 %. `Gendy1.ar`: within ±1.

## Cause

`server/plugins/GendynUGens.cpp`, `Gendyn_mirroring(lower, upper, in)`: for `in < lower`
it sets `in = (2.0f * upper - lower) - in`, then `in = fmod(in - upper, 2.0f * range)`
and folds. For `in = lower - d` this gives `d` (measured from 0) instead of `lower + d`;
it is right only when `lower` is 0, as for the [0, 1] duration walk.

## Suggestion

Reflect the offset from the lower bound, for values on either side:

```cpp
float t = fmod(fabs(in - lower), 2.0f * range);
in = lower + (t < range ? t : 2.0f * range - t);
```

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
