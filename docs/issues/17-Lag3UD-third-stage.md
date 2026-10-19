# Lag3UD: the third stage chooses its lag time by comparing the first two stages

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`Lag3UD` is three `LagUD` stages in series; each stage should use `lagTimeU` when its input
rises above its state and `lagTimeD` otherwise. The third stage instead decides by comparing
the first stage with the second, so it can rise with the down time and fall with the up
time.

## Steps to reproduce

```supercollider
(
{
    var x = LFPulse.ar(7, 0, 0.3) + (LFNoise0.ar(40) * 0.3);
    Lag3UD.ar(x, 0.005, 0.08)
}.plot(0.5)
)
```

## Expected

Each stage follows its own input with the up or down time (as `Lag2UD` does for both of
its stages).

## Actual

(NRT, 2 s.) A double-precision simulation of `Lag3UD_next` as written is bit-exact against
scsynth; with the third stage testing its own input and state it differs on 45813 of
96000 samples, by up to 0.2.

## Cause

`server/plugins/FilterUGens.cpp`, `Lag3UD_next` (both loops):

```cpp
if (y1a > y1b) {            // should be (y1b > y1c)
    y1c = y1b + b1u * (y1c - y1b);
} else {
    y1c = y1b + b1d * (y1c - y1b);
}
```

## Suggestion

`if (y1b > y1c)`.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
