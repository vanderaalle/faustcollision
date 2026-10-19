# Vibrato, Wrap, Fold, Clip, InRange, ToggleFF, PulseDivider (.ar) read a constant or kr input past its end

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

These UGens, at audio rate, read their first input with `ZXP(in)` for every sample of
the block whatever its rate. A constant or control-rate input holds one value: the other
63 reads go past it into adjacent memory. Unlike most UGens of this kind (`Trig`,
`Latch`, `TDelay`, `LinExp`...), their classes have no `checkInputs` requiring an
audio-rate first input, so sclang accepts these SynthDefs. `Vibrato`'s own defaults
(`Vibrato.ar(freq: 440.0)`) take this path.

## Steps to reproduce

```supercollider
(
{
    [
        Vibrato.ar(0.5, 6, 0, 0, 0, 0, 0),   // depth 0: should output 0.5
        Wrap.ar(0.3, 0, 1),                  // should output 0.3
        PulseDivider.ar(Impulse.kr(5), 2)    // should pulse 2.5 times per second
    ]
}.plot(0.1)
)
```

## Expected

0.5 and 0.3 throughout; 25 pulses in 10 s.

## Actual

(NRT, 10 s.) The correct value on the first sample of each block, then zeros, denormals
and NaN (30300 NaN samples for `Wrap` and for `Fold`); `InRange.ar` flips between 0
and 1; `PulseDivider.ar(Impulse.kr(5), 2)` outputs 22750 ones instead of 25. The garbage
depends on the memory layout, so it differs between servers and runs. With `DC.ar(...)`
or `T2A.ar(...)` as input, all are correct.

## Cause

The calc functions read the input as a buffer:

- `Vibrato_next` (`server/plugins/LFUGens.cpp:295`), `Wrap_next_*` (1569-1607),
  `Fold_next_*` (1677-1721), `Clip_next_*` (1767-1812), `InRange_next` (2215):
  `float* in = ZIN(0)` and `ZXP(in)` per sample.
- `ToggleFF_next` (`server/plugins/TriggerUGens.cpp:900`), `PulseDivider_next`
  (1110): likewise for the trigger.

and the classes do not check the input rate: `Vibrato` (`Osc.sc:303`), `InRange` and
its subclasses `Fold`, `Clip`, `Wrap` (`Trig.sc:208-244`), `ToggleFF`,
`PulseDivider`.

## Suggestion

Add `checkInputs { ^this.checkSameRateAsFirstInput }` to these classes (as `Trig`,
`TDelay` etc. have), or select calc functions that read `ZIN0(0)` when the input is
not audio rate.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
