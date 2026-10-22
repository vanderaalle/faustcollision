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
Integrator, Slew at kr; Lag2UD, Lag3UD (sc-findings 30); AmpComp, AmpCompA; VarLag (sc-findings 26); IEnvGen (sc-findings 27; hold shape rejected); Ramp
(sc-findings 16: the boundary over-read is not reproduced); MantissaMask, Hasher; LFClipNoise,
LFDNoise0/1/3, LFDClipNoise, TRand, TIRand, TExpRand, CoinGate (statistics); Saw, Pulse, Blip
at kr (sc-findings 25 reproduced); TWindex (sc-findings 31); Pluck; Sum3, Sum4
(sclang's merged additions; unblock DynKlank).
Filters at kr (LPF ... LeakDC, sc-findings 28 timing); delays, combs, allpasses, Delay1/2 at kr.
SampleRate, SampleDur, ControlRate, ControlDur, RadiansPerSample, SubsampleOffset (sc-findings 29).
Census failures fixed: kr UGens fed by audio read the block's first sample (a2k; krhold
only for kr_block entries: Amplitude, Pitch, T2K); EnvGen's audio-rate envelope inputs at
the block start; LocalIn.kr held per block; Pan4.kr compile error (opaque inputs).
Rejected with an explanation (tier "rejected"): T2K, Peak.kr of audio.
Batch 8: Rand, IRand, LinRand, NRand, ExpRand (distribution metric); doneAction 2 on Line,
XLine, EnvGen; TrigControl, LagControl; scalar-rate operators; excluded classes refused with
their reason (translator/excluded.toml); Out bus 0 only, Out.kr refused; layer 2 rendered
through the C++ a target compiles (three Faust C++ issues worked around); sc-findings 35, 36.
Batch 7 (branch ports-batch7, before its full suite): DynKlank; Hilbert, FreqShift; PanB,
PanB2, BiPanB2, DecodeB2, PanAz (ar and kr); Spring, Ball, TBall; the chaos family: Cusp,
Quad, LinCong, Standard, FBSine, Latoocarfian, Gbman (N/L/C), Henon (N/L/C, the freeze and
reseed), LorenzL, Crackle, Logistic (float pairs: in float32 it cycles); Gendy1/2/3
(sc-findings 33, 34). Chaotic maps run in double in scsynth: statistics,
exact up to the first few hundred iterations; Standard at tol 4 (its mixed phase space:
scsynth against itself from a perturbed start scores up to 3.4).

## Goal
Completeness: every core UGen that can be translated into Faust, for the SuperCollider
community (vairi is one consumer). Order by value per effort, but niche or costly UGens are
in scope; only buffers, buses, demand rate and FFT stay excluded by design.

## Open
- Gendy3 with knum < initCPs (and amp/dur distributions 3, 5): the port's spectrum differs
  from scsynth's (case_Gendy3 channel 2: port vs 10 scsynth seeds median 5.4 dB, scsynth vs
  itself 1.3). Hidden by the wide tolerance the kr channel forces. Set aside (Oct 2026).
  Known: a float transcription of Gendy3_next_k matches scsynth (median 0.9-1.6), so the
  port is wrong for all tested settings (dist 1/1 and 3/5, knum 7 and 12), its default
  configuration excepted. gendist, gmirror, hrand and the initial state match the C; fed the
  port's own draws, the model diverges at the first period: the amplitude step is right for
  breakpoint 1 and identical for every breakpoint from 2 on, although the generated hash code
  is correct per breakpoint. Suspect next: the list compaction (act/pos/slot in gendy3_g).

## Next, in order
1. Batch 9 (branch ports-batch9): array arguments, FSinOsc with a varying freq, Linen
   doneAction 2, more excluded classes (done there); the Gendy3 item above; then the
   help-file corpus (721 SynthDefs in HelpSource, 332 translated) rendered against scsynth.
2. doneAction 2 for DetectSilence and LFGauss; Pitch median, Pluck maxdelaytime, Klank
   freqscale as non-constant inputs (help-file corpus).
3. MoogFF.kr: set aside (plans/moogff-kr.md: a Faust miscompilation to understand first).
4. Measure findings 6, 7, 8 (source only so far).
5. Issue drafts: docs/issues/ covers SuperCollider findings 4, 5, 11, 15, 17-28, 30-35 and
   two Faust bugs (faust-01, faust-02); filing them is the maintainer's decision.

## Working method (keeps cost down)
- Read the scsynth source of the UGen (and nova-simd where a nova calc function runs).
- Write sc.lib port + mapping.toml entry + a case in tests/cases/case_direct.scd.
- `translator.build` then `pytest -k case_X`; compare per channel with the nrt/ and
  renders/ wavs; where it differs, simulate the C code in Python against the NRT render.
- Inputs scsynth reads in a constructor: feed them from Line/SinOsc/constants in cases.
- Full suite (~20 min) only before a commit; never rebuild while it runs.
- Measure before writing a finding; probes: sclang translator/batch.scd with a scratch
  build dir and a scratch source dir (relative paths).
