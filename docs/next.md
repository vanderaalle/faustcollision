# Where the work stands, and what is next

Read with CLAUDE.md (rules) and docs/faust-notes.md (pitfalls).

## Done (all with regression cases, mostly bit-exact)
Operators; oscillators (incl. FSinOsc, SinOscFB, Blip, Formant, VarSaw, SyncSaw, Klang,
LFGauss, Phasor, Vibrato); filters, lags, decays, delays, combs/allpasses; EnvGen, Line,
XLine; dynamics; reverbs; Klank, PitchShift, LocalIn/LocalOut; Wrap, Fold, Clip, LinExp,
InRange, InRect, Schmidt, ModDif; triggers (Trig ... T2A); panners (Pan2, LinPan2,
Balance2, XFade2, LinXFade2, Rotate2, Pan4); LPZ1/2, HPZ1/2, BPZ2, BRZ2, Slope, FOS, SOS.
Rejected with an explanation (tier "rejected"): T2K, Peak.kr of audio.

## Next, in order
1. MidEQ (FilterUGens.cpp:2539): like BPF (sc.bpf: fcoef + iir2), out = in + a0 (y0 - y2),
   amp = dbamp(db) - 1; same float-coefficient floor as BPF.
2. BLowPass, BHiPass, BBandPass, BBandStop, BAllPass, BPeakEQ, BLowShelf, BHiShelf
   (FilterUGens.cpp:4193...): constant freq/rq -> exact double coefficients from
   derive.py into sc.sos_g (pair biquad); kr -> ramp in 21 steps of 3 from the previous
   exact target; ar freq (next_aa) reads ZXP(freq) once per 3-sample group, i.e. the first
   21 values of the block: probable sc-findings 24, measure before writing it.
3. Median; then kr variants still unmapped (filters, delays, Lag*, Decay*, Integrator.kr...),
   Saw/Pulse/Blip .kr, VarLag, Linen, IEnvGen, DetectSilence, Select, Sanitize.
4. Random UGens (statistics only), chaos oscillators, DynKlank, grains, Pluck,
   Hilbert/FreqShift, ambisonic panners: lower priority.
5. Issue drafts: done for 4, 5, 11, 15, 17-23 (docs/issues/); file them upstream.
6. vairi: bump its faustcollision submodule pointer.

## Working method (keeps cost down)
- Read the scsynth source of the UGen (and nova-simd where a nova calc function runs).
- Write sc.lib port + mapping.toml entry + a case in tests/cases/case_direct.scd.
- `translator.build` then `pytest -k case_X`; compare per channel with the nrt/ and
  renders/ wavs; where it differs, simulate the C code in Python against the NRT render.
- Inputs scsynth reads in a constructor: feed them from Line/SinOsc/constants in cases.
- Full suite (~20 min) only before a commit; never rebuild while it runs.
- Measure before writing a finding; probes: sclang translator/batch.scd with a scratch
  build dir and a scratch source dir (relative paths).
