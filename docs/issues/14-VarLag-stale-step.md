# VarLag.ar: changing time after the ramp has ended adds one stale slope step

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

With `warp: \lin` (the only warp that creates the VarLag UGen), changing `time` while
the input is unchanged rescales the ramp, even when the ramp has already ended. The
output then overshoots the target by one sample.

## Steps to reproduce

```supercollider
(
{
    var x = Line.ar(0, 1, 0.05) >= 1;                  // step 0 -> 1 at 0.05 s
    var t = (Line.kr(0, 1, 0.1) >= 1) * 0.01 + 0.02;   // time 0.02 -> 0.03 at 0.1 s
    VarLag.ar(x, t, warp: \lin)
}.plot(0.2)
)
```

## Expected

1.0 after the ramp, whatever happens to `time` afterwards.

## Actual

(NRT.) One sample reads 1.0006951 = (1/960) / 1.5, the old per-sample slope divided by
the time ratio; the next sample is 1.0 again.

## Cause

`server/plugins/FilterUGens.cpp`, `VarLag_next`: in the `else` branch (input
unchanged, `lagTime != m_lagTime`), `counter = sc_max(1, (int)(m_counter * scaleFactor))`
turns a finished ramp (counter 0) into one more step with the stale slope.
`VarLag_next_1` (control rate) checks `counter != 0` first.

## Suggestion

Rescale only while `counter > 0`, as `VarLag_next_1` does.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
