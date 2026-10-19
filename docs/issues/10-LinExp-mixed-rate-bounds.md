# LinExp.ar with one audio-rate bound reads the other bound past its value

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

When one bound of a range pair (`srclo`/`srchi` or `dstlo`/`dsthi`) is audio rate and
the other is a constant or control rate, `LinExp.ar` reads both bounds as audio buffers:
the non-audio one is read past its single value, and the output contains NaN and inf.

## Steps to reproduce

```supercollider
(
{
    var in = DC.ar(0.5);
    [
        LinExp.ar(in, 0, SinOsc.ar(1).range(0.9, 1.1), 1, 10),
        LinExp.ar(in, 0, 1, 1, SinOsc.ar(1).range(9, 11)),
        LinExp.ar(in, DC.ar(0), SinOsc.ar(1).range(0.9, 1.1), 1, 10)  // correct
    ]
}.plot(1)
)
```

## Expected

Finite output on all channels.

## Actual

(NRT, 10 s.) Channel 1: NaN on 15150 samples. Channel 2: NaN on 371175 samples and inf
on 15150. Channel 3 (both bounds of the pair at audio rate) is correct.

## Cause

`LinExp_SetCalc` (`server/plugins/LFUGens.cpp:2369`) selects the per-sample calc
functions when *either* bound is audio rate:

```cpp
if (INRATE(1) == calc_FullRate || INRATE(2) == calc_FullRate) {
```

and `LinExp_next_aa`, `_ak`, `_ka` (lines 2325-2354) then read *both* bounds with
`ZXP`.

## Suggestion

Read a bound per sample only when it is audio rate (e.g. add mixed calc functions, or
use a stride of 0 for non-audio inputs).

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
