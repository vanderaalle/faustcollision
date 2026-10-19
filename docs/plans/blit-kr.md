# Saw, Pulse, Blip .kr

Prepared, not yet applied or tested. Apply, build, test, measure tolerances.


C (OscUGens.cpp): the same calc functions with inNumSamples = 1 at SAMPLERATE = SR / 64
(750 Hz): cpstoinc = sineSize * SAMPLEDUR * 65536 * 0.5 with SAMPLEDUR = 64 / SR; N =
(int32)(375 / freq); one output sample per block.

Differences from .ar that the port must model:
- Crossfade on an N change: xfade starts at 0 and the slope is mSlopeFactor (1 at kr), so
  the change block's single sample uses the previous kernel only (n1); the new kernel from
  the next block. (.ar ramps xfade over the block: sc.bl_xf.)
- Saw/Pulse do not clamp N: freq > 375 Hz gives N = 0, scale = 0.5 / 0 = inf, and the
  kernel is evaluated with N2 = 1. Expect inf/NaN output: probable sc-findings 25 (Saw.kr,
  Pulse.kr above SR / 128). Measure first (NRT: Saw.kr(Line.kr(100, 600, 2)) through K2A),
  then port faithfully (the float division gives inf in Faust too) and document.
  Blip clamps N to >= 1 (Blip_Ctor / Blip_next): no issue.
- Constructors: Saw/Blip run next(1) and then reset phase/y1/N: no state change except
  m_freqin; Pulse outputs 0 and runs nothing. Same as .ar.

Refactor in sc.lib (keeps .ar bit-exact; rerun case_Saw, case_Pulse, case_Blip after):
- bl_N(fin) -> bl_N_g(fin, sr): cc = sr * 0.5.
- dinc(f, shift) uses ma.SR via ldiv(.., sr): add a dinc_g(f, shift, sr) or check whether
  ldiv already takes sr (it is called with `sr`: find its binding).
- iphase(inc) -> iphase_g(inc, clk): (+(inc * clk) ~ _) : mem, sampled at clk; kr reads
  the phase before the block's step.
- core recursions: y updated only at clk (select2(clk, y1, y)), output held per block
  (ba.sAndH(krclk)); xfade term: 0 at kr (n1 only on xf).
- per-block quantities: kr inputs are already per block; bl_prev(x) = x@blocksize stays
  right for kr (previous block).
- Pulse duty offset ramp: at kr, inNumSamples = 1, so the int ramp's per-sample slope is
  d / 1 applied after the sample: the change block uses the previous offset; check
  Pulse_next's phaseoff update order before writing.

Cases: K2A.ar(Saw.kr(knob)) with the knob spec 0.1..300 (N changes across the range),
Saw.kr(Latch.kr(in.abs * 300 + 1, Impulse.kr(...))) (per-block changes), and the above-375
Hz case only as a probe (not a regression case, unless the port reproduces inf exactly and
the comparison handles non-finite values).

