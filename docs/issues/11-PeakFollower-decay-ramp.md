# PeakFollower: the decay ramp starts at the new value and overshoots, oscillating forever

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

When `decay` changes, `PeakFollower` should ramp from the old to the new value over a
block. It ramps from the *new* value away from it instead, and stores the overshoot. The
next block ramps back the other way, so with a steadily decaying input the stored decay
alternates around the target indefinitely instead of settling.

## Steps to reproduce

```supercollider
(
{
    var in = SinOsc.ar(110) * Decay.ar(Impulse.ar(2), 0.3);
    PeakFollower.ar(in, Line.kr(0.99, 0.9999, 6))
}.plot(6)
)
```

A float simulation of `PeakFollower_next` as written is bit-exact against scsynth (we
checked 10 s of `PeakFollower.ar(SoundIn.ar(0), Line.kr(0.99, 0.9999, 6))` on a bass
recording: 0 of 484800 samples differ); a simulation ramping from the old value is not.

## Expected

A decay coefficient ramped linearly from the previous to the new value over the block.

## Actual

The coefficient starts at the new value, moves past it by up to one block's slope (only
on samples where the level decays), and the overshoot is stored; afterwards it keeps
alternating between target + e and target - e.

## Cause

`server/plugins/TriggerUGens.cpp:1936`, `PeakFollower_next`:

```cpp
float decay = ZIN0(1);                                     // new value, not unit->mDecay
...
float decay_slope = CALCSLOPE(decay, unit->mDecay);
... else { level = ...; decay += decay_slope; } ...         // only on decaying samples
unit->mDecay = decay;                                      // stores the overshoot
```

The branch (which formula is used) is also chosen from the new and the stored, overshot
values.

## Suggestion

Start the ramp from `unit->mDecay` and store the target (`ZIN0(1)`) at the end of the
block; advance the ramp on every sample.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
