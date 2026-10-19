# MoogFF .kr

Prepared (source read), not yet written.

C (FilterUGens.cpp, MoogFF_next): the same calc function runs at kr with one sample per
block and the control rate's SAMPLEDUR / SAMPLERATE (64 / SR, SR / 64):
- freq: wcD = 2 tan(T pi freq) * SAMPLERATE recomputed when freq changes, used at once
  (no ramp). At kr the tan pole sits at 375 Hz: freq near or above it gives huge or
  negative wcD; the code clamps wcD < 0 to 0, so b0 = 0 and the filter closes. Measured
  (NRT, freq Line.kr(300, 450), gain 2): finite throughout; above 380 Hz the output decays
  to silence (max 0.006). A sensible guard: no finding; port the clamp.
- gain k: CALCSLOPE ramp with k += slope_k after the sample (slope factor 1 at kr): a gain
  change applies one block late (as sc-findings 28).
- reset (IN0(3) > 0) clears the state: required 0, as for .ar.
- Constructor: one sample (MoogFF_next(unit, 1)) from zero state with m_freq
  uninitialised: the first block continues from that state.

Port: the ar sc.moogff stepped at krclk with SR / 64, k via kprev; tier "approximate"
like .ar (float floor near self-oscillation). Case: K2A.ar(MoogFF.kr(LFNoise0.kr(200),
knob freq 1..300, gain 0..3.5)).
