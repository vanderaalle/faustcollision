# LFDNoise0/1/3, LFClipNoise, LFDClipNoise, CoinGate, TRand, TIRand, TExpRand, TWindex

Prepared (source read), not yet written. Compare mode: statistics (tol 1.5), as the
mapped random UGens (WhiteNoise, Dust, LFNoise0...): the RNG streams differ, so only
distributions and timing are checked.

- LFClipNoise (NoiseUGens.cpp): LFNoise0 with level = fcoin (+-1): sc.lfnoise0_clk with a
  coin draw. Counter = max(1, (int)(rate / max(freq, .001))).
- LFDNoise0/1/3, LFDClipNoise (DynNoiseUGens.cpp:115-299): "dynamic" noise: a phase
  decremented by freq / SR per sample (freq read per sample at ar: next; per block:
  next_k), new value(s) when the phase wraps; 1: linear, 3: cubic interpolation between
  random points. Selected by INRATE(0) (freq), so no over-read.
- TRand, TIRand, TExpRand (NoiseUGens.cpp:453-690): a new value on each trigger rise
  (prev <= 0, cur > 0); the constructor draws the first value. .ar reads the trigger per
  sample whatever its rate (sc-findings 21, measured: a kr trigger gives ~22500-30000
  changes in 10 s instead of 100): require an audio-rate trigger at .ar (ar_inputs, as
  for Wrap/PulseDivider). TRand_next_aa: lo/hi per sample (audio lo).
- CoinGate (NoiseUGens.cpp:693): on a trigger rise, out = trigger value with probability
  prob, else 0; constructor output 0. .ar: same over-read (ar_inputs = trig).
- TWindex (OscUGens.cpp:561): weighted random index on a trigger (normalize flag, the
  weights read per trigger); selected by INRATE(0) (trig): next_a reads the trigger per
  sample only when it is audio rate.

Statistics to compare: for the triggered ones, the change instants are deterministic
(trigger rises) and can be checked exactly; the values by distribution. Consider a
"triggers exact, values statistics" compare, or two cases.
