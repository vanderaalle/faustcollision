# Where the work stands, and what is next

Read with CLAUDE.md (rules) and docs/faust-notes.md (pitfalls).

## Done (all with regression cases, mostly bit-exact)
Operators; oscillators (incl. FSinOsc, SinOscFB, Blip, Formant, VarSaw, SyncSaw, Klang,
LFGauss, Phasor, Vibrato); filters, lags, decays, delays, combs/allpasses; EnvGen, Line,
XLine; dynamics; reverbs; Klank, PitchShift, LocalIn/LocalOut; Wrap, Fold, Clip, LinExp,
InRange, InRect, Schmidt, ModDif; triggers (Trig ... T2A); panners (Pan2, LinPan2,
Balance2, XFade2, LinXFade2, Rotate2, Pan4); LPZ1/2, HPZ1/2, BPZ2, BRZ2, Slope, FOS, SOS;
MidEQ; BEQSuite (BLowPass ... BHiShelf) at every input rate (next_aa: sc-findings 24).
Median, Select, Sanitize, Linen, DetectSilence; Lag, Lag2, Lag3, LagUD, Decay, Decay2,
Integrator, Slew at kr; Lag2UD, Lag3UD (sc-findings 30); AmpComp, AmpCompA; VarLag (sc-findings 26).
Filters at kr (LPF ... LeakDC, sc-findings 28 timing); delays, combs, allpasses, Delay1/2 at kr.
SampleRate, SampleDur, ControlRate, ControlDur, RadiansPerSample, SubsampleOffset (sc-findings 29).
Census failures fixed: kr UGens fed by audio read the block's first sample (a2k; krhold
only for kr_block entries: Amplitude, Pitch, T2K); EnvGen's audio-rate envelope inputs at
the block start; LocalIn.kr held per block; Pan4.kr compile error (opaque inputs).
Rejected with an explanation (tier "rejected"): T2K, Peak.kr of audio.

## Next, in order
Each step has a prepared plan (and, where noted, code) in docs/plans/: apply, build, test,
set tolerances from the measured floors, full suite, commit, bump vairi.
1. Saw, Pulse, Blip .kr (core refactor; sc-findings 25): plans/blit-kr.md.
2. IEnvGen (sc-findings 27): plans/ienvgen.md.
3. Small remaining classes (census, unmapped): MoogFF.kr (plans/moogff-kr.md: a Faust miscompilation to understand first); Ramp (sc-findings 16, measured); MantissaMask, Hasher:
   plans/small-classes.md.
4. Random UGens (statistics only; plans/random.md), chaos oscillators, DynKlank, grains, Pluck,
   Hilbert/FreqShift, ambisonic panners: lower priority.
5. Issue drafts: docs/issues/ covers 4, 5, 11, 15, 17-28, 30; file them upstream.

## Working method (keeps cost down)
- Read the scsynth source of the UGen (and nova-simd where a nova calc function runs).
- Write sc.lib port + mapping.toml entry + a case in tests/cases/case_direct.scd.
- `translator.build` then `pytest -k case_X`; compare per channel with the nrt/ and
  renders/ wavs; where it differs, simulate the C code in Python against the NRT render.
- Inputs scsynth reads in a constructor: feed them from Line/SinOsc/constants in cases.
- Full suite (~20 min) only before a commit; never rebuild while it runs.
- Measure before writing a finding; probes: sclang translator/batch.scd with a scratch
  build dir and a scratch source dir (relative paths).
