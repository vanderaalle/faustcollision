# AllpassC outputs 0 instead of -coef * in while its delay line fills

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

For the first delay length after the synth starts, `AllpassC` outputs silence. An
allpass with an empty delay line should output `-feedback * in` there (the direct
path), which is what `AllpassN` and `AllpassL` do. `AllpassC` differs from them for
the first `delaytime` seconds.

## Steps to reproduce

```supercollider
(
{
    var in = WhiteNoise.ar(0.5);
    [
        AllpassL.ar(in, 0.2, 0.2, 1),
        AllpassC.ar(in, 0.2, 0.2, 1)
    ]
}.plot(0.3)
)
```

## Expected

Both channels equal `-feedback * in` for the first 0.2 s, then (nearly) equal.

## Actual

The `AllpassC` channel is 0 for the first 0.2 s.

## Cause

`AllpassC_helper<true>` (the "checked" variant used while the buffer fills,
`server/plugins/DelayUGens.cpp:2655`) writes the input to the buffer and outputs 0
when the newest read index is negative (line 2667):

```cpp
if (irdphase0 < 0) {
    bufData[iwrphase & mask] = ZXP(in);
    ZXP(out) = 0.f;
}
```

`AllpassL_helper<true>` (line 2615) outputs `-feedbk * zin` in the same branch, which is
the allpass output with a zero delayed value (`value - feedbk * dwr` with `value = 0`).

## Suggestion

`ZXP(out) = -feedbk * zin;` in `AllpassC_helper<true>`, as in `AllpassL_helper<true>`.
`BufAllpassC` shares the helper.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
