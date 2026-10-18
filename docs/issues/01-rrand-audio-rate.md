# rrand on audio-rate signals returns values outside [lo, hi)

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`rrand` used as a binary operator on audio-rate inputs returns values in
`[2*lo - hi, hi)` instead of `[lo, hi)`. At control rate it is correct.

## Steps to reproduce

```supercollider
(
{
    [
        BinaryOpUGen('rrand', DC.ar(0), DC.ar(1)),          // audio rate
        K2A.ar(BinaryOpUGen('rrand', DC.kr(0), DC.kr(1)))   // control rate
    ]
}.plot(1)
)
```

## Expected

Both channels between 0 and 1.

## Actual

Audio rate: min -1.0, max 1.0. Control rate: min 0.0, max 1.0 (measured over 2 s, NRT).

## Cause

`rrand_aa` (and the other audio-rate variants) draw from `frand2` (-1..1) instead of
`frand` (0..1):

```cpp
// server/plugins/BinaryOpUGens.cpp:3381 (rrand_aa)
ZXP(out) = xb > xa ? xa + frand2(s1, s2, s3) * (xb - xa) : (xb + frand2(s1, s2, s3) * (xa - xb));
```

while `rrand_1` (control rate, `BinaryOpUGens.cpp:1428`) uses `rgen.frand()`. Using
`frand` in the audio-rate variants would make both rates match the documented range.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
