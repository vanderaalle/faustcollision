# TWindex returns an index outside the array when the weights sum to less than 1

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

With `normalize = 0` and weights that sum to less than 1, `TWindex` returns n + 2 (for n
weights) with the missing probability: an index outside the array. The help only says the
weights "should sum to 1.0". `Select` then clips it to the last element, silently changing
the distribution.

## Steps to reproduce

```supercollider
(
{
    TWindex.ar(Impulse.ar(200), [0.2, 0.3, 0.3], 0)
}.plot(0.1)
)
```

## Expected

Either an index in 0..2 (e.g. the last one, or the weights treated as relative), or a
documented out-of-range value.

## Actual

(NRT, 10 s.) Indices 0, 1, 2 with 0.18 / 0.30 / 0.30 of the triggers, and index 5 with
0.22.

## Cause

`server/plugins/OscUGens.cpp`, `TWindex_chooseNewIndex`: `int32 index = maxindex;` with
`maxindex = unit->mNumInputs` (the weights plus the trigger and normalize inputs); when no
running sum reaches the draw, that initial value is returned.

## Suggestion

Return the last index (`maxindex - 3`) when no sum reaches the draw, or document the
behaviour (and that `normalize = 1` avoids it).

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
