# VarLag

Prepared, not yet applied or tested. Apply, build, test, measure tolerances.


sclang (Filter.sc:130, VarLag.new1): only warp \lin (curve 1) makes the VarLag UGen
(inputs in, time, start). Any other warp, including the default warp = 5, builds
EnvGen(Env([start, in], [time], warp), Changed(in) + Impulse(0) [+ Changed.kr(time)]):
already translatable if EnvGen, Changed and Impulse at that rate are mapped. Check with a
regression case of the default VarLag too (it exercises EnvGen retriggering mid-segment).

VarLag UGen (FilterUGens.cpp:860):
- Reads the input once per block, even at ar (`*in` = IN(0)[0]): a step to a new input
  value starts a linear ramp in double: counter = max(1, (int)(lagTime * SAMPLERATE))
  (double product: sc.iprod), slope = (in - level) / counter. Per sample: out = level; if
  counter > 0 { level += slope; --counter } else level = m_in (the exact target).
- lagTime changes while the input is unchanged: counter = (int)(counter * lagTime /
  oldLagTime) (ar: float scale factor; kr: double), slope /= scaleFactor.
- Probable sc-findings 26 (measure first): next (ar) rescales even when the ramp has
  ended (counter == 0): max(1, 0) = 1, so the next sample adds the stale slope once more
  (an overshoot of one slope step), then snaps back to m_in. next_1 (kr) checks
  counter != 0. Also at ar, the change test runs only if the input is unchanged; at kr
  both run (after an input change m_lagTime already equals lagTime, so it is moot).
- Constructor: level = start, counter and slope toward in, output start; no step.

Port: a per-sample state machine (level and slope as double pairs: dadd2 per sample,
slope from ddivf; counter int; m_in, m_lagTime), clocked per sample at ar and per block at
kr; input and lagTime through a2k at ar. Expected bit-exact with pairs (the ramp is a
long double accumulation: a float level would drift by ~counter ulps).

Cases: VarLag.ar(Latch.ar(in, Impulse.ar(4)), knob, warp: \lin) (steps, knob-swept
time), a time change mid-ramp and after the ramp (the probe for finding 26), .kr likewise;
plus VarLag.ar(..) with the default warp (EnvGen path).

