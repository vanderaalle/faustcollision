# APF is not an allpass: its unrolled loop indexes the wrong past outputs

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`APF` should have a flat magnitude response. It boosts low frequencies by up to ~40 dB.

## Steps to reproduce

```supercollider
{ APF.ar(Impulse.ar(0), 1000, 0.95) }.plot(0.2);
// FFT the impulse response: the gain is far from 0 dB at every frequency.
```

## Expected

0 dB at all frequencies (the help describes an allpass).

## Actual

Impulse response starts 1.0, 0.902, 1.788, 2.554, 3.996, ... Magnitude response
(NRT render of the snippet, 8192-point FFT):

| Frequency | 100 Hz | 300 Hz | 1 kHz | 2 kHz | 5 kHz | 12 kHz |
| --- | --- | --- | --- | --- | --- | --- |
| Gain | +39.9 dB | +37.6 dB | +30.0 dB | +23.8 dB | +12.0 dB | +2.7 dB |

## Cause

Two problems in `APF_next` (`server/plugins/FilterUGens.cpp:1413`):

1. The loop computes 3 samples per iteration with rotating variables, but the second and
   third samples pick the wrong past outputs for the b2 term (lines 1435-1436, 1451-1452):

   ```cpp
   x0 = ZXP(in); ZXP(out) = y0 = x0 + b1 * (y1 - x1) + b2 * (y2 - x2);
   x2 = ZXP(in); ZXP(out) = y2 = x2 + b1 * (y0 - x0) + b2 * (y2 - x1);   // should be (y1 - x1)
   x1 = ZXP(in); ZXP(out) = y1 = x1 + b1 * (y2 - x2) + b2 * (y2 - x0);   // should be (y0 - x0)
   ```

   Only the first sample of each group (and the `mFilterRemain` sample) uses the
   per-sample formula.

2. That formula, `y = x + b1 (y1 - x1) + b2 (y2 - x2)`, has transfer function
   `(1 - b1 z^-1 - b2 z^-2) / (1 - b1 z^-1 - b2 z^-2)`: the identity, not an allpass.
   An allpass needs the mirrored numerator,
   `y = -b2 x + -b1 x1 + x2 + b1 y1 + b2 y2` (with b2 = -reson²).

So what `APF` currently outputs is decided by the indexing errors.

## Suggestion

Fix the formula to a real second-order allpass and the indexing of the unrolled loop (or
write the loop without rotation, as most other filters do).

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
