# Where the work stands, and what is next

Read with CLAUDE.md (rules) and docs/faust-notes.md (pitfalls).

## Done (all with regression cases, mostly bit-exact)
Operators; oscillators (incl. FSinOsc, SinOscFB, Blip, Formant, VarSaw, SyncSaw, Klang,
LFGauss, Phasor, Vibrato); filters, lags, decays, delays, combs/allpasses; EnvGen, Line,
XLine; dynamics; reverbs; Klank, PitchShift, LocalIn/LocalOut; Wrap, Fold, Clip, LinExp,
InRange, InRect, Schmidt, ModDif; triggers (Trig ... T2A); panners (Pan2, LinPan2,
Balance2, XFade2, LinXFade2, Rotate2, Pan4); LPZ1/2, HPZ1/2, BPZ2, BRZ2, Slope, FOS, SOS;
MidEQ; BEQSuite (BLowPass ... BHiShelf) with constant or per-block inputs.
Rejected with an explanation (tier "rejected"): T2K, Peak.kr of audio; BEQSuite with every
coefficient input at audio rate (next_aa, until step 1 below).

## Next, in order
1. BEQSuite next_aa (all coefficient inputs at audio rate; derive.beq_calc rejects it now).
   Each 3-sample group reads the inputs once and recomputes the coefficients when they
   differ from the stored ones (no ramp); the 64th sample keeps group 20's. What is read
   differs by class (FilterUGens.cpp, *_next_aa / *_next_aaa):
   - BLowPass, BAllPass, BPeakEQ, BLowShelf: group g reads sample g (the block's first
     21); the remainder stores sample 21 for the next block's comparison.
   - BHiPass: the same, but the remainder stores nothing (the stored value stays the last
     one read).
   - BBandPass, BBandStop, BHiShelf: on a change, `m_freq = ZXP(freq)` reads again, so the
     pointer advances by 2 (data-dependent: 0, 2, 4 ... 40 while the input keeps
     changing); the stored value is the sample after the one used. Remainder: BBandPass and
     BBandStop store the last value read (`nextfreq`), BHiShelf reads the next sample.
   One model: a per-block state machine (read pointer, pointer of the stored value,
   block-start stored values, effective inputs), updated at j = 3g, g <= 20, reading the
   input at delay j - p (p <= 2g, so causal). Measure against NRT (a Python simulation of
   each variant) before writing sc-findings 24; then sc.beq_a(cf, kind, x, f, q, d) on
   sos_g with the coefficient functions of beq_k (no ramp).
2. Median; then kr variants still unmapped (filters, delays, Lag*, Decay*, Integrator.kr...),
   Saw/Pulse/Blip .kr, VarLag, Linen, IEnvGen, DetectSilence, Select, Sanitize.
3. Random UGens (statistics only), chaos oscillators, DynKlank, grains, Pluck,
   Hilbert/FreqShift, ambisonic panners: lower priority.
4. Issue drafts: done for 4, 5, 11, 15, 17-23 (docs/issues/); file them upstream.

## Working method (keeps cost down)
- Read the scsynth source of the UGen (and nova-simd where a nova calc function runs).
- Write sc.lib port + mapping.toml entry + a case in tests/cases/case_direct.scd.
- `translator.build` then `pytest -k case_X`; compare per channel with the nrt/ and
  renders/ wavs; where it differs, simulate the C code in Python against the NRT render.
- Inputs scsynth reads in a constructor: feed them from Line/SinOsc/constants in cases.
- Full suite (~20 min) only before a commit; never rebuild while it runs.
- Measure before writing a finding; probes: sclang translator/batch.scd with a scratch
  build dir and a scratch source dir (relative paths).
