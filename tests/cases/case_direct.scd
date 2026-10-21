// Regression cases for the direct tier: one or more per mapping entry, covering the
// calc functions scsynth picks by input rate (named <UGen>, <UGen>_<variant>).
(
var in = { SoundIn.ar(0) };
var spec = { |lo, hi, def, warp = \exp| ControlSpec(lo, hi, warp, 0, def) };
[
	// kr frequency (Osc_ikk: double increment), swept by the knob settings
	SynthDef(\case_SinOsc, { |freq = 440| Out.ar(0, SinOsc.ar(freq) * 0.5) },
		metadata: (specs: (freq: spec.(20, 5000, 440)), signals: [\impulse])),
	// audio-rate frequency (Osc_iaa: float increment) and audio-rate phase (Osc_ika)
	SynthDef(\case_SinOsc_ar, { Out.ar(0, [SinOsc.ar(in.value * 500 + 600), SinOsc.ar(300, in.value * 4)] * 0.5) }),
	// control rate
	SynthDef(\case_SinOsc_kr, { |freq = 3| Out.ar(0, K2A.ar(SinOsc.kr(freq, 0.5))) },
		metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	// LF oscillators: kr freq (next_k), audio freq (next_a), control rate; iphase nonzero
	SynthDef(\case_LFSaw, { |freq = 440| Out.ar(0, [LFSaw.ar(freq, 0.3), LFSaw.ar(in.value * 300 + 200), LFSaw.ar(freq.neg)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)))),
	SynthDef(\case_LFSaw_kr, { |freq = 3| Out.ar(0, K2A.ar(LFSaw.kr(freq, -0.5))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	SynthDef(\case_LFTri, { |freq = 440| Out.ar(0, [LFTri.ar(freq, 1), LFTri.ar(in.value * 300 + 200)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)))),
	SynthDef(\case_LFTri_kr, { |freq = 3| Out.ar(0, K2A.ar(LFTri.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	SynthDef(\case_LFPar, { |freq = 440| Out.ar(0, [LFPar.ar(freq, 1), LFPar.ar(in.value * 300 + 200)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)))),
	SynthDef(\case_LFPar_kr, { |freq = 3| Out.ar(0, K2A.ar(LFPar.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 500, 3)), signals: [\impulse])),
	SynthDef(\case_LFCub, { |freq = 440| Out.ar(0, [LFCub.ar(freq, 0.2), LFCub.ar(in.value * 300 + 200)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)))),
	SynthDef(\case_LFCub_kr, { |freq = 3| Out.ar(0, K2A.ar(LFCub.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 500, 3)), signals: [\impulse])),
	SynthDef(\case_LFPulse, { |freq = 440, width = 0.3| Out.ar(0, [LFPulse.ar(freq, 0.1, width), LFPulse.ar(in.value * 300 + 200, 0, width)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440), width: spec.(0, 1, 0.3, \lin)))),
	SynthDef(\case_LFPulse_kr, { |freq = 3| Out.ar(0, K2A.ar(LFPulse.kr(freq, 0, 0.5))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	// Impulse: kr freq (ramped increment), offset phase, audio freq, negative freq, control rate
	SynthDef(\case_Impulse, { |freq = 440| Out.ar(0, [Impulse.ar(freq), Impulse.ar(freq, 0.25), Impulse.ar(freq.neg)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)), signals: [\impulse])),
	SynthDef(\case_Impulse_ar, { Out.ar(0, Impulse.ar(in.value * 300 + 400) * 0.5) }),
	SynthDef(\case_Impulse_kr, { |freq = 3| Out.ar(0, K2A.ar(Impulse.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	// Filters: knob-swept coefficient (constant per render) and an audio-rate one
	// (read per block, so the coefficient interpolation runs every block)
	SynthDef(\case_LPF, { |freq = 1000| Out.ar(0, [LPF.ar(in.value, freq), LPF.ar(in.value, in.value.abs * 4000 + 100)]) },
		metadata: (specs: (freq: spec.(30, 15000, 1000)))),
	SynthDef(\case_HPF, { |freq = 1000| Out.ar(0, [HPF.ar(in.value, freq), HPF.ar(in.value, in.value.abs * 4000 + 100)]) },
		metadata: (specs: (freq: spec.(30, 15000, 1000)))),
	SynthDef(\case_OnePole, { |coef = 0.5| Out.ar(0, [OnePole.ar(in.value, coef), OnePole.ar(in.value, in.value.abs.min(0.99))]) },
		metadata: (specs: (coef: spec.(-0.99, 0.99, 0.5, \lin)))),
	SynthDef(\case_OneZero, { |coef = 0.5| Out.ar(0, OneZero.ar(in.value, coef)) },
		metadata: (specs: (coef: spec.(-1, 1, 0.5, \lin)))),
	SynthDef(\case_LeakDC, { |coef = 0.995| Out.ar(0, LeakDC.ar(in.value + 0.3, coef)) },
		metadata: (specs: (coef: spec.(0.9, 0.9999, 0.995, \lin)))),
	// Delays: constant, knob (kr) and audio-rate delay time; Delay1/2
	SynthDef(\case_DelayN, { |dt = 0.01| Out.ar(0, [DelayN.ar(in.value, 0.2, 0.0123), DelayN.ar(in.value, 0.2, dt), DelayN.ar(in.value, 0.05, in.value.abs * 0.04)]) },
		metadata: (specs: (dt: spec.(0.0001, 0.2, 0.01)))),
	SynthDef(\case_DelayL, { |dt = 0.01| Out.ar(0, [DelayL.ar(in.value, 0.2, 0.0123), DelayL.ar(in.value, 0.2, dt), DelayL.ar(in.value, 0.05, in.value.abs * 0.04)]) },
		metadata: (specs: (dt: spec.(0.0001, 0.2, 0.01)))),
	SynthDef(\case_Delay1, { Out.ar(0, Delay1.ar(in.value)) }),
	SynthDef(\case_Delay2, { Out.ar(0, Delay2.ar(in.value)) }),
	// Pulse (Saw: tests/cases/case_Saw.scd); audio-rate freq is read once per block
	SynthDef(\case_Pulse, { |freq = 220, width = 0.3| Out.ar(0, [Pulse.ar(freq, width), Pulse.ar(in.value.abs * 500 + 100, 0.5)] * 0.5) },
		metadata: (specs: (freq: spec.(30, 5000, 220), width: spec.(0.05, 0.95, 0.3, \lin)))),
	SynthDef(\case_Saw_ar, { Out.ar(0, Saw.ar(in.value.abs * 500 + 100) * 0.5) }),
	// Latch: audio-rate trigger, kr trigger (Impulse.kr), control rate
	SynthDef(\case_Latch, { Out.ar(0, [Latch.ar(in.value, in.value), Latch.ar(in.value, Impulse.kr(30)), K2A.ar(Latch.kr(in.value, Impulse.kr(10)))]) }),
	// Pan2.kr of an audio input (reads the block's first sample: a2k, not krhold), and Splay.kr
	// (a pseudo-UGen: Pan2.kr per channel plus operators)
	SynthDef(\case_Pan2_kr_audio, { Out.ar(0, K2A.ar(Pan2.kr(in.value, 0.3, 0.8)) ++ K2A.ar(Splay.kr([in.value, in.value * 0.5]))) }),
	// Pan2: kr pos (knob), audio-rate pos, kr level
	SynthDef(\case_Pan2, { |pos = 0| Out.ar(0, Pan2.ar(in.value, pos, 0.7) ++ Pan2.ar(in.value, in.value, 0.5)) },
		metadata: (specs: (pos: spec.(-1, 1, 0, \lin)))),
	// Resonant filters: knob-swept frequency at a fixed Q/decay, and an audio-rate (per-block) frequency
] ++ [[\RLPF, 0.3], [\RHPF, 0.3], [\BPF, 0.5], [\BRF, 0.5], [\Resonz, 0.1], [\Ringz, 0.2], [\TwoPole, 0.95], [\TwoZero, 0.95], [\APF, 0.95]].collect { |p|
	SynthDef(("case_" ++ p[0]).asSymbol, { |freq = 1000|
		Out.ar(0, [p[0].asClass.ar(in.value, freq, p[1]), p[0].asClass.ar(in.value, in.value.abs * 3000 + 200, p[1])] * 0.5) },
		metadata: (specs: (freq: spec.(50, 12000, 1000))))
} ++ [
	// BEQSuite: knobs (next_kk), constants (next_ii), audio-rate freq read at the block start
	// (next_kk), all coefficient inputs audio rate (next_aa: stepped freq with constant
	// rq/db, so unchanged groups occur; continuous); [class, rq/bw/rs, has db]
] ++ [[\BLowPass, 0.5, false], [\BHiPass, 0.5, false], [\BAllPass, 0.5, false], [\BBandPass, 1, false],
	[\BBandStop, 1, false], [\BPeakEQ, 0.5, true], [\BLowShelf, 1, true], [\BHiShelf, 1, true]].collect { |p|
	SynthDef(("case_" ++ p[0]).asSymbol, { |freq = 1000, db = 6|
		var c = p[0].asClass, ext = if(p[2]) { [db] } { [] }, cext = if(p[2]) { [-9] } { [] };
		Out.ar(0, [c.ar(in.value, freq, p[1], *ext), c.ar(in.value, 800, p[1], *cext),
			c.ar(in.value, in.value.abs * 3000 + 200, p[1], *ext),
			c.ar(in.value, Latch.ar(in.value.abs * 3000 + 200, Impulse.ar(900)), DC.ar(p[1]), *(if(p[2]) { [DC.ar(-9)] } { [] })),
			c.ar(in.value, in.value.abs * 3000 + 200, in.value.abs * 0.5 * p[1] + (0.5 * p[1]), *(if(p[2]) { [in.value * 12] } { [] }))] * 0.5) },
		metadata: (specs: if(p[2]) { (freq: spec.(50, 12000, 1000), db: spec.(-24, 24, 6, \lin)) } { (freq: spec.(50, 12000, 1000)) }))
} ++ [
	// MidEQ: knob-swept frequency and gain (boost and cut), audio-rate (per-block) frequency
	SynthDef(\case_MidEQ, { |freq = 1000, db = 6|
		Out.ar(0, [MidEQ.ar(in.value, freq, 0.5, db), MidEQ.ar(in.value, in.value.abs * 3000 + 200, 0.3, -12)] * 0.5) },
		metadata: (specs: (freq: spec.(50, 12000, 1000), db: spec.(-24, 24, 6, \lin)))),
	// Median: odd and even lengths (even: the upper middle), the 32 clip; kr over block values
	SynthDef(\case_Median, { Out.ar(0, [Median.ar(3, in.value), Median.ar(8, in.value), Median.ar(40, in.value),
		K2A.ar(Median.kr(5, Latch.kr(in.value, Impulse.kr(200))))]) }),
	// Select: kr which (next_k), audio which (next_a), out-of-range and negative which (clip), kr
	SynthDef(\case_Select, { |which = 1| Out.ar(0, [Select.ar(which, [in.value, in.value.abs, in.value.neg]),
		Select.ar(in.value * 3, [in.value, DC.ar(0.25), in.value.squared]), Select.ar(in.value * 8 - 2, [in.value, DC.ar(-0.5)]),
		K2A.ar(Select.kr(Latch.kr(in.value, Impulse.kr(3)) * 4, [DC.kr(0.1), DC.kr(0.2), DC.kr(0.3)]))]) },
		metadata: (specs: (which: spec.(-1, 4, 1, \lin)))),
	// Sanitize: inf/NaN from a division by a 0/1 gate, a subnormal from a tiny product; kr replace; .kr
	SynthDef(\case_Sanitize, { Out.ar(0, [Sanitize.ar(in.value / (in.value.abs > 0.1), 0.5),
		Sanitize.ar(in.value * 1e-39, -0.5), Sanitize.ar(in.value / (in.value.abs > 0.1), Latch.kr(in.value, Impulse.kr(5))),
		K2A.ar(Sanitize.kr(Latch.kr(in.value, Impulse.kr(50)) / (Latch.kr(in.value, Impulse.kr(50)).abs > 0.1), -0.25))]) }),
	// Linen: gate from the test signal (rises, falls, forced release via gate <= -1), attack
	// longer than some gates (the attack completes before release)
	SynthDef(\case_Linen, { |att = 0.05| var g = Latch.kr(in.value, Impulse.kr(20)) * 4;
		Out.ar(0, [K2A.ar(Linen.kr(g, att, 0.8, 0.1)), K2A.ar(Linen.kr(g.clip(-1.05, 1), 0.7, 0.5, 0.3))]) },
		metadata: (specs: (att: spec.(0.001, 1, 0.05)))),
	// DetectSilence: constant amp/time (next), kr amp (next_k), .kr; time with a product near an integer
	SynthDef(\case_DetectSilence, { |amp = 0.01| Out.ar(0, [DetectSilence.ar(in.value, 0.01, 0.05),
		DetectSilence.ar(in.value, amp, 0.0007), K2A.ar(DetectSilence.kr(Latch.kr(in.value, Impulse.kr(100)), 0.02, 0.7))]) },
		metadata: (specs: (amp: spec.(0.0001, 0.5, 0.01)))),
	// Filters at kr: a kr input changing every block or so; knob-swept frequency, stepping up at
	// 1 s (immediate group: new coefficients at once; late group: one block later)
	SynthDef(\case_filters_kr, { |freq = 40|
		var k = Latch.kr(in.value, Impulse.kr(400)), st = Line.kr(0, 1, 2) > 0.5, f = freq * (1 + st);
		Out.ar(0, K2A.ar([LPF.kr(k, f), HPF.kr(k, f), RLPF.kr(k, f, 0.3), RHPF.kr(k, f, 0.3), BPF.kr(k, f, 0.5),
			BRF.kr(k, f, 0.5), Resonz.kr(k, f, 0.1), Ringz.kr(k, f, 0.2) * 0.1, Formlet.kr(k, f, 0.005, 0.1) * 0.1,
			TwoPole.kr(k, f, 0.9) * 0.1, TwoZero.kr(k, f, 0.9), APF.kr(k, f, 0.9), MidEQ.kr(k, f, 0.5, 6),
			OnePole.kr(k, 0.9 - (0.4 * st)), OneZero.kr(k, 0.5 * st - 0.2), LeakDC.kr(k, 0.9 + (0.05 * st))])) },
		metadata: (specs: (freq: spec.(5, 150, 40)))),
	// Delays, combs, allpasses at kr: delays in blocks (fractional for L/C), a delay-time step at
	// 1 s (applied at once), feedback; Delay1/Delay2; a constant zero delay (pass-through)
	SynthDef(\case_delays_kr, { |dt = 0.05|
		var k = Latch.kr(in.value, Impulse.kr(400)), t = dt * (1 + (0.5 * (Line.kr(0, 1, 2) > 0.5)));
		Out.ar(0, K2A.ar([DelayN.kr(k, 0.2, t), DelayL.kr(k, 0.2, t), DelayC.kr(k, 0.2, t),
			CombN.kr(k, 0.2, t, 1), CombL.kr(k, 0.2, t, 1), CombC.kr(k, 0.2, t, 1),
			AllpassN.kr(k, 0.2, t, 1), AllpassL.kr(k, 0.2, t, 1), AllpassC.kr(k, 0.2, t, 1),
			Delay1.kr(k), Delay2.kr(k), DelayN.kr(k, 0.2, 0)] * 0.5)) },
		metadata: (specs: (dt: spec.(0.003, 0.13, 0.05)))),
	// Server info constants (scaled to ~1 so the waveform score is meaningful)
	SynthDef(\case_ServerInfo, { Out.ar(0, DC.ar(1) * [SampleRate.ir / 48000, SampleDur.ir * 48000, ControlRate.ir / 750,
		ControlDur.ir * 750, RadiansPerSample.ir * 7639.437, SubsampleOffset.ir]) }),
	// Lag2UD, Lag3UD (ar and kr): asymmetric times, steps and noise in the input
	SynthDef(\case_LagUDn, { |scale = 1| var k = Latch.kr(in.value, Impulse.kr(50));
		Out.ar(0, [Lag2UD.ar(in.value, 0.005 * scale, 0.08 * scale), Lag3UD.ar(in.value, 0.005 * scale, 0.08 * scale),
			K2A.ar(Lag2UD.kr(k, 0.01 * scale, 0.1 * scale)), K2A.ar(Lag3UD.kr(k, 0.01 * scale, 0.1 * scale))]) },
		metadata: (specs: (scale: spec.(0.1, 10, 1)))),
	// AmpComp (constant root/exp: next; kr root: next_kk), AmpCompA, ar and kr, over the audio range
	SynthDef(\case_AmpComp, { |root = 261.6| var f = in.value.abs * 15000 + 30, k = Latch.kr(f, Impulse.kr(50));
		Out.ar(0, [AmpComp.ar(f, 261.6, 0.3333), AmpComp.ar(f, root, 0.5), AmpCompA.ar(f, 1000, 0.32, 1),
			K2A.ar(AmpComp.kr(k, 440, 0.3333)), K2A.ar(AmpCompA.kr(k, 0, 0.32, 1))] * 0.2) },
		metadata: (specs: (root: spec.(50, 2000, 261.6)))),
	// VarLag (warp \\lin): steps of the input (new ramps, some mid-ramp), a time change at 0.7 s
	// (mid-ramp or after it: sc-findings 26); ar and kr
	SynthDef(\case_VarLag, { |time = 0.05| var x = Latch.ar(in.value, Impulse.ar(3)), t = time * (1 + (0.5 * (Line.kr(0, 1, 1.4) > 0.5)));
		Out.ar(0, [VarLag.ar(x, t, warp: \lin, start: 0), K2A.ar(VarLag.kr(A2K.kr(x), t, warp: \lin, start: 0.2))]) },
		metadata: (specs: (time: spec.(0.002, 0.3, 0.05)))),
	// IEnvGen: all shapes but hold, an integer and two fractional curvatures (truncated:
	// sc-findings 27), a nonzero offset, the index running past both ends; ar and kr
	SynthDef(\case_IEnvGen, { var idx = in.value.abs * 1.6 - 0.1;
		var e1 = Env([0.1, 1, 0.3, 0.8, 0.05, 0.6, 0.2, 0.7, 0.4], [0.1, 0.15, 0.1, 0.2, 0.1, 0.15, 0.1, 0.1], [\step, \lin, \exp, \sin, \wel, \sqr, \cub, -4.5]);
		var e2 = Env([0, 1, 0.2, 0.9], [0.3, 0.4, 0.3], [3, 0.7, -2], offset: 0.05);
		Out.ar(0, [IEnvGen.ar(e1, idx), IEnvGen.ar(e2, idx), K2A.ar(IEnvGen.kr(e1, Latch.kr(idx, Impulse.kr(100))))]) }),
	// Ramp: even segment lengths (480, 240 samples: never ending with a block, sc-findings 16; 0.01 gives
	// (int)(0.01f * 48000) = 479), ar
	// and kr
	SynthDef(\case_Ramp, { Out.ar(0, [Ramp.ar(in.value, 0.01001), Ramp.ar(in.value, 0.00501),
		K2A.ar(Ramp.kr(Latch.kr(in.value, Impulse.kr(40)), 0.02))]) }),
	// MantissaMask (bits 0, 3, 10, 23; kr) and Hasher (ar, kr) on the test signal
	SynthDef(\case_MantissaMask, { var k = Latch.kr(in.value, Impulse.kr(100));
		Out.ar(0, [MantissaMask.ar(in.value, 3), MantissaMask.ar(in.value, 0), MantissaMask.ar(in.value, 10),
			MantissaMask.ar(in.value, 23), K2A.ar(MantissaMask.kr(k, 5)), Hasher.ar(in.value), K2A.ar(Hasher.kr(k))]) }),
	// Random UGens (statistics only): rates and trigger densities >= 100/s on the silence signal
	// (~1000 random events per render, as the noise cases below)
	SynthDef(\case_random2, { |freq = 500| var t = Impulse.ar(200), k = Impulse.kr(200);
		Out.ar(0, [LFClipNoise.ar(freq), LFDNoise0.ar(freq), LFDNoise1.ar(freq), LFDNoise3.ar(freq), LFDClipNoise.ar(freq),
			K2A.ar(LFDNoise1.kr(100)), TRand.ar(-1, 1, t), TIRand.ar(-5, 5, t) * 0.2, TExpRand.ar(0.1, 1, t),
			CoinGate.ar(0.5, t), K2A.ar(TRand.kr(-1, 1, k)), K2A.ar(CoinGate.kr(0.5, k)),
			TRand.ar(SinOsc.ar(0.5) * 0.5 - 1, SinOsc.ar(0.3) * 0.5 + 1, t), CoinGate.ar(SinOsc.ar(0.2) * 0.4 + 0.5, t)] * 0.5) },
		metadata: (specs: (freq: spec.(100, 5000, 500)), signals: [\silence])),
	// Saw, Pulse, Blip at kr (below the 375 Hz limit of sc-findings 25): knob-swept frequency
	// (N changes), a duty step at 1 s (one block late), a harmonic-count change. One SynthDef
	// each: several band-limited kr oscillators in one Faust program compile for minutes.
	SynthDef(\case_Saw_kr, { |freq = 20| Out.ar(0, K2A.ar(Saw.kr(freq)) * 0.3) }, metadata: (specs: (freq: spec.(0.5, 250, 20)))),
	SynthDef(\case_Pulse_kr, { |freq = 20| Out.ar(0, K2A.ar(Pulse.kr(freq, 0.3 + (0.4 * (Line.kr(0, 1, 2) > 0.5)))) * 0.3) },
		metadata: (specs: (freq: spec.(0.5, 250, 20)))),
	SynthDef(\case_Blip_kr, { |freq = 20| Out.ar(0, K2A.ar(Blip.kr(freq, 3 + (5 * (Line.kr(0, 1, 2) > 0.5)))) * 0.3) },
		metadata: (specs: (freq: spec.(0.5, 250, 20)))),
	// TWindex (statistics): normalized weights, unnormalized ones summing to 0.8 (n + 2 when no
	// weight is reached), audio and kr triggers at 200/s
	SynthDef(\case_TWindex, { var t = Impulse.ar(200), k = Impulse.kr(200);
		Out.ar(0, [TWindex.ar(t, [1, 3, 2, 4], 1), TWindex.ar(t, [0.2, 0.3, 0.3], 0), K2A.ar(TWindex.kr(k, [0.5, 0.25, 0.25]))] * 0.2) },
		metadata: (signals: [\silence])),
	// Pluck: kr trigger (next_kk), audio trigger (ak), audio coef (ka, aa); knob-swept delay time
	SynthDef(\case_Pluck, { |dt = 0.005| var n = in.value, ta = Impulse.ar(3), tk = Impulse.kr(3), c = SinOsc.ar(0.5) * 0.4;
		Out.ar(0, [Pluck.ar(n, tk, 0.05, dt, 2, 0.4), Pluck.ar(n, ta, 0.05, dt * 1.5, 1, -0.3),
			Pluck.ar(n, tk, 0.05, dt, 2, c), Pluck.ar(n, ta, 0.05, dt * 0.7, 3, c)] * 0.4) },
		metadata: (specs: (dt: spec.(0.001, 0.04, 0.005)))),
	// Sum3, Sum4 (sclang merges a + b + c into them): ar, ar with kr and constant terms, kr; and
	// DynKlank (Ringz bank summed through Sum3/Sum4)
	SynthDef(\case_Sum34, { |g = 0.5| var x = in.value, k = Latch.kr(x, Impulse.kr(20));
		Out.ar(0, [Sum3(x, x.squared, x.abs), Sum4(x, x * 0.5, k, g), Sum3(x, k, 0.25), K2A.ar(Sum3(k, k * 2, g)),
			DynKlank.ar(`[[400, 800, 1200], [0.3, 0.2, 0.1], [0.3, 0.2, 0.4]], x * 0.1),
			DynKlank.ar(`[[300, 500, 700, 900, 1100], nil, [0.2]], x * 0.1, g + 0.5)]) },
		metadata: (specs: (g: spec.(0, 1, 0.5, \lin)))),
	// Hilbert: the two quadrature outputs of the test signal
	SynthDef(\case_Hilbert, { Out.ar(0, Hilbert.ar(in.value)) }),
	// FreqShift, one SynthDef per calc function (each compiles slowly): kk (knob freq, constant
	// phase: ignored, sc-findings 32), ka (audio phase), aa, ak (audio freq, kr phase ramp)
	SynthDef(\case_FreqShift, { |freq = 100| Out.ar(0, FreqShift.ar(in.value, freq, 0.5) * 0.5) },
		metadata: (specs: (freq: spec.(-500, 2000, 100, \lin)))),
	SynthDef(\case_FreqShift_ka, { Out.ar(0, FreqShift.ar(in.value, 150, SinOsc.ar(3)) * 0.5) }),
	SynthDef(\case_FreqShift_aa, { Out.ar(0, FreqShift.ar(in.value, SinOsc.ar(0.5) * 200 + 100, SinOsc.ar(2)) * 0.5) }),
	SynthDef(\case_FreqShift_ak, { Out.ar(0, FreqShift.ar(in.value, SinOsc.ar(0.5) * 200 + 100, Line.kr(0, 2, 2)) * 0.5) }),
	// Ambisonic and azimuth panners: knob azimuth (kr ramp), audio-rate PanAz position, 4/5/6
	// outputs, width 2 and 3, orientation 0.5; SplayAz (sclang sugar over PanAz)
	SynthDef(\case_panners_b, { |az = 0.3| var x = in.value, a = SinOsc.ar(0.25);
		Out.ar(0, PanB.ar(x, az, az * 0.5, 0.8) ++ PanB2.ar(x, az * -1, 0.7) ++ BiPanB2.ar(x, x * 0.5, az, 0.9)
			++ DecodeB2.ar(4, x, x * 0.5, x * -0.3, 0.5) ++ DecodeB2.ar(6, x, x * 0.3, x * 0.2, 0)
			++ PanAz.ar(5, x, az, 0.8, 2, 0.5) ++ PanAz.ar(4, x, a, 1, 3, 0) ++ SplayAz.ar(4, [x, x * 0.5, x * -0.5])) },
		metadata: (specs: (az: spec.(-1, 1, 0.3, \lin)))),
	// the same panners at kr (one sample per block; gains one block late), on a kr input
	SynthDef(\case_panners_b_kr, { |az = 0.3| var k = Latch.kr(in.value, Impulse.kr(100)), st = Line.kr(0, 1, 2) > 0.5;
		Out.ar(0, K2A.ar(PanB.kr(k, az + st, 0.2, 0.8) ++ PanB2.kr(k, az, 0.7 + (0.2 * st)) ++ BiPanB2.kr(k, k * 0.5, az + st, 0.9)
			++ DecodeB2.kr(4, k, k * 0.5, k * -0.3, 0.5) ++ PanAz.kr(5, k, az + st, 0.8, 2, 0.5) ++ SplayAz.kr(4, [k, k * 0.5]))) },
		metadata: (specs: (az: spec.(-1, 1, 0.3, \lin)))),
	// Spring (force in), Ball and TBall (a floor moving with the signal; dither on bounces), ar, kr
	SynthDef(\case_physical, { var x = in.value, k = Latch.kr(x, Impulse.kr(100));
		Out.ar(0, [Ball.ar(x * 0.2, 2, 0.1, 0.01), TBall.ar(x * 0.2, 5, 0.1, 0.01) * 0.1, K2A.ar(Ball.kr(k * 0.2, 1, 0.1, 0.01))]) }),
	SynthDef(\case_Spring, { var x = in.value, k = Latch.kr(x, Impulse.kr(100));
		Out.ar(0, [Spring.ar(x, 30, 0.001), K2A.ar(Spring.kr(k, 5, 0.01))] * 0.01) }),
	// Chaos oscillators (statistics): iteration rates >= 2 kHz so a render has many iterations
	SynthDef(\case_chaos, { Out.ar(0, [CuspN.ar(8000, 1, 1.9), CuspL.ar(3000, 1, 1.9), QuadN.ar(8000), QuadL.ar(3000), QuadC.ar(3000),
		LinCongN.ar(8000), LinCongL.ar(3000), LinCongC.ar(3000),
		FBSineN.ar(8000), FBSineL.ar(3000), FBSineC.ar(3000), LatoocarfianN.ar(8000), LatoocarfianL.ar(3000), LatoocarfianC.ar(3000),
		GbmanN.ar(8000), GbmanL.ar(3000), LorenzL.ar(3000)] * 0.3) }, metadata: (signals: [\silence])),
	// Henon: defaults; a to 2 at 0.5 s (diverges, freezes), back to 1.4 at 1 s (reseeds)
	SynthDef(\case_Henon, { var t = Line.kr(0, 2, 2), a = 1.4 + (0.6 * ((t > 0.5) * (t < 1)));
		Out.ar(0, [HenonN.ar(8000), HenonL.ar(3000), HenonC.ar(3000), HenonN.ar(8000, a), HenonL.ar(3000, a), HenonC.ar(3000, a)] * 0.3) },
		metadata: (signals: [\silence])),
	// Crackle away from the bistable default; a swept parameter; .kr
	SynthDef(\case_Crackle, { Out.ar(0, [Crackle.ar(1.9), Crackle.ar(Line.kr(1.8, 2.0, 4)), K2A.ar(Crackle.kr(1.95))] * 0.3) },
		metadata: (signals: [\silence])),
	// Logistic: every sample (scalar freq >= SR), held periods (also a kr parameter), .kr
	SynthDef(\case_Logistic, { Out.ar(0, [Logistic.ar(3.9, 48000), Logistic.ar(3.7, 3000, 0.3), Logistic.ar(Line.kr(3.6, 3.99, 4), 1000),
		K2A.ar(Logistic.kr(3.95, 100, 0.2))] * 0.5) },
		metadata: (signals: [\silence])),
	// Gendy: defaults; other distributions, fewer breakpoints, knum < initCPs; .kr in range
	// (speed below one breakpoint per block); distribution 6 is meant for a moving adparam
	SynthDef(\case_Gendy1, { Out.ar(0, [Gendy1.ar, Gendy1.ar(0, 0, 1, 1, 100, 200, 0.3, 0.3, 8, 5), Gendy1.ar(2, 3, 0.5, 0.5, 200, 400),
		K2A.ar(Gendy1.kr(1, 1, 1, 1, 20, 40, 0.5, 0.5, 12))] * 0.3) }, metadata: (signals: [\silence])),
	SynthDef(\case_Gendy_dist, { Out.ar(0, ((0..5).collect { |d| Gendy1.ar(d, 6 - d, 0.6, 0.6, 300, 500) }
		++ [Gendy1.ar(6, 0, SinOsc.kr(0.3).range(0, 1), 0.6, 300, 500)]) * 0.3) },
		metadata: (signals: [\silence])),
	SynthDef(\case_Gendy2, { Out.ar(0, [Gendy2.ar, Gendy2.ar(0, 0, 1, 1, 100, 200, 0.3, 0.3, 8, 5, 1.5, 0.2),
		K2A.ar(Gendy2.kr(minfreq: 1, maxfreq: 10))] * 0.3) }, metadata: (signals: [\silence])),
	SynthDef(\case_Gendy3, { Out.ar(0, [Gendy3.ar, Gendy3.ar(0, 0, 1, 1, 220, 0.3, 0.3, 4), Gendy3.ar(3, 5, 0.6, 0.6, 330, 0.5, 0.5, 12, 7),
		K2A.ar(Gendy3.kr(1, 1, 1, 1, 20, 0.5, 0.5, 4))] * 0.3) }, metadata: (signals: [\silence])),
	// Grains: overlapping mono grains; stereo with swept dur/freq/pan; 4 channels; a kr
	// trigger with maxGrains 2 (one slot: refusals, and reuse in the block a grain ends in)
	SynthDef(\case_GrainSin, { var t = Impulse.ar(30, 0.5);
		Out.ar(0, [GrainSin.ar(1, t, 0.05, 440, maxGrains: 16), GrainSin.ar(2, Impulse.ar(17, 0.3), Line.kr(0.01, 0.2, 5), Line.kr(200, 2000, 6), SinOsc.kr(0.3), maxGrains: 16),
			GrainSin.ar(4, t, 0.1, 330, Line.kr(-1, 1, 8), maxGrains: 16), GrainSin.ar(1, Impulse.kr(13), 0.1, 660, maxGrains: 2)].flat * 0.3) },
		metadata: (signals: [\silence])),
	SynthDef(\case_GrainFM, { Out.ar(0, [GrainFM.ar(1, Impulse.ar(25, 0.5), 0.06, 440, 220, 2, maxGrains: 16),
		GrainFM.ar(2, Impulse.ar(11, 0.2), 0.12, Line.kr(300, 900, 6), Line.kr(50, 400, 7), Line.kr(0.5, 5, 8), SinOsc.kr(0.4), maxGrains: 16),
		GrainFM.ar(1, Impulse.kr(9), 0.08, 550, 110, 3, maxGrains: 8)].flat * 0.3) },
		metadata: (signals: [\silence])),
	SynthDef(\case_GrainIn, { Out.ar(0, [GrainIn.ar(1, Impulse.ar(20, 0.5), 0.03, in.value, maxGrains: 16),
		GrainIn.ar(2, Impulse.ar(13, 0.1), Line.kr(0.02, 0.15, 6), in.value, SinOsc.kr(0.25), maxGrains: 16),
		GrainIn.ar(1, Impulse.kr(7), 0.05, in.value, maxGrains: 4)].flat * 0.5) }),
	// PSinGrain: one grain; the node ends with it, silencing the other output too
	SynthDef(\case_PSinGrain, { Out.ar(0, [PSinGrain.ar(660, 0.3, 0.5), SinOsc.ar(220) * 0.2]) }, metadata: (signals: [\silence])),
	SynthDef(\case_PSinGrain_long, { Out.ar(0, PSinGrain.ar(1234.5, 2.3456, 0.8)) }, metadata: (signals: [\silence])),
	// Scalar randoms: 128 instances cycled through one channel (one draw per sample); one
	// SynthDef per UGen (all in one overflows sclang's synth message)
] ++ [[\Rand, { Rand(-1, 1) }], [\IRand, { IRand(0, 9) * 0.1 }], [\LinRand, { LinRand(0, 1, 0) }], [\LinRand_max, { LinRand(-1, 0, 1) }],
	[\NRand, { NRand(0, 1, 3) }], [\ExpRand, { ExpRand(0.01, 1) }]].collect { |k|
	SynthDef(("case_" ++ k[0]).asSymbol, { var n = 128, ix = Phasor.ar(0, 1, 0, n);
		Out.ar(0, Select.ar(ix, { k[1].value * DC.ar(1) } ! n)) }, metadata: (signals: [\impulse]))
} ++ [
	// doneAction 2: the synth ends where the UGen is done; the sine must stop with it
	SynthDef(\case_done_line, { Out.ar(0, [Line.ar(0, 1, 0.0123, doneAction: 2), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_line_kr, { Out.ar(0, [K2A.ar(Line.kr(0, 1, 0.05, doneAction: 2)), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_line_var, { |dur = 0.02| Out.ar(0, [Line.ar(0, 1, dur, doneAction: 2), SinOsc.ar(300) * 0.1]) },
		metadata: (signals: [\impulse], specs: (dur: ControlSpec(0.001, 0.3, \exp, 0, 0.02)))),
	SynthDef(\case_done_xline, { Out.ar(0, [XLine.ar(1, 0.01, 0.0234, doneAction: 2), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_xline_kr, { Out.ar(0, [K2A.ar(XLine.kr(1, 0.01, 0.07, doneAction: 2)), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_env, { Out.ar(0, [EnvGen.ar(Env.perc(0.01, 0.1), doneAction: 2), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_env_kr, { Out.ar(0, [K2A.ar(EnvGen.kr(Env.perc(0.01, 0.1), doneAction: 2)), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	SynthDef(\case_done_env_gate, { var g = SoundIn.ar(0).abs > 0.5; Out.ar(0, [EnvGen.ar(Env.asr(0.01, 1, 0.05), Trig.ar(g, 0.2), doneAction: 2), SinOsc.ar(300) * 0.1]) }),
	SynthDef(\case_done_env_rel, { Out.ar(0, [EnvGen.ar(Env.asr(0.01, 1, 0.03), Line.kr(1, -1, 0.3) > 0, doneAction: 2), SinOsc.ar(300) * 0.1]) }, metadata: (signals: [\impulse])),
	// Control variants: a t_ argument (its value for the first block, then 0) and lagged
	// arguments (a lag per block); the settings change the controls at creation only. No
	// filter after the trigger: TrigControl's constructor output is 0, and constructor-time
	// input values are not modelled (a filter would carry the first block's difference on)
	SynthDef(\case_TrigControl, { |t_trig = 1| Out.ar(0, [K2A.ar(t_trig), K2A.ar(t_trig) * SinOsc.ar(440)]) },
		metadata: (signals: [\impulse], specs: (t_trig: ControlSpec(0, 2, \lin, 0, 1)))),
	SynthDef(\case_LagControl, { |freq = 440, amp = 0.3| Out.ar(0, [K2A.ar(freq) * 0.001, SinOsc.ar(freq) * amp]) }, [0.2, 0.05],
		metadata: (specs: (freq: ControlSpec(100, 1000, \exp, 0, 440), amp: ControlSpec(0, 1, \lin, 0, 0.3)))),
	SynthDef(\case_Standard, { Out.ar(0, [StandardN.ar(8000), StandardL.ar(3000)] * 0.3) }, metadata: (signals: [\silence])),
	SynthDef(\case_Formlet, { |freq = 1000| Out.ar(0, Formlet.ar(in.value, freq, 0.005, 0.1) * 0.5) },
		metadata: (specs: (freq: spec.(50, 12000, 1000)))),
	// Lags and decays: knob-swept time, input signal (impulse/steps from the test signals)
] ++ [[\Lag, [0.05]], [\Lag2, [0.05]], [\Lag3, [0.05]], [\LagUD, [0.005, 0.1]], [\Decay, [0.2]], [\Decay2, [0.005, 0.2]]].collect { |p|
	SynthDef(("case_" ++ p[0]).asSymbol, { |scale = 1|
		Out.ar(0, p[0].asClass.ar(in.value, *(p[1] * scale)) * 0.5) },
		metadata: (specs: (scale: spec.(0.1, 10, 1))))
} ++ [
	// Lags, decays, integrator, slew at kr: one step per block; a time doubling at 1 s
	// (Lag* apply a change at once, Decay/Decay2/Integrator one block late)
	SynthDef(\case_Lag_kr, { |scale = 1|
		var k = Latch.kr(in.value, Impulse.kr(50)), m = scale * (1 + (Line.kr(0, 1, 2) > 0.5));
		Out.ar(0, K2A.ar([Lag.kr(k, 0.05 * m), Lag2.kr(k, 0.05 * m), Lag3.kr(k, 0.05 * m), LagUD.kr(k, 0.005 * m, 0.1 * m),
			Decay.kr(k, 0.2 * m), Decay2.kr(k, 0.005 * m, 0.2 * m), Integrator.kr(k * 0.1, 0.99 - (0.04 * (m > scale))),
			Slew.kr(k, 200 / m, 100 / m)])) },
		metadata: (specs: (scale: spec.(0.1, 10, 1)))),
	SynthDef(\case_Integrator, { |coef = 0.99| Out.ar(0, Integrator.ar(in.value * 0.1, coef)) },
		metadata: (specs: (coef: spec.(0.5, 0.999, 0.99, \lin)))),
	SynthDef(\case_Slew, { |up = 200| Out.ar(0, Slew.ar(in.value, up, up * 0.5)) },
		metadata: (specs: (up: spec.(10, 5000, 200)))),
	SynthDef(\case_DelayC, { |dt = 0.01| Out.ar(0, [DelayC.ar(in.value, 0.2, 0.0123), DelayC.ar(in.value, 0.2, dt), DelayC.ar(in.value, 0.05, in.value.abs * 0.04)]) },
		metadata: (specs: (dt: spec.(0.0001, 0.2, 0.01)))),
	// Combs and allpasses: knob delay (kr), negative decay (negative feedback), audio-rate delay
] ++ [\CombN, \CombL, \CombC, \AllpassN, \AllpassL, \AllpassC].collect { |u|
	SynthDef(("case_" ++ u).asSymbol, { |dt = 0.01|
		var c = u.asClass;
		Out.ar(0, [c.ar(in.value, 0.2, dt, 0.5), c.ar(in.value, 0.2, 0.0123, -0.3), c.ar(in.value, 0.05, in.value.abs * 0.04, 0.2)] * 0.5) },
		metadata: (specs: (dt: spec.(0.0005, 0.2, 0.01))))
} ++ [
	// Lines: ar and kr, rising and falling, a duration shorter than the render
	SynthDef(\case_Line, { Out.ar(0, [Line.ar(-0.5, 0.8, 0.7), Line.ar(1, 0, 0.0123), K2A.ar(Line.kr(0, 1, 0.5)),
		Line.ar(2000, 60, 8), Line.ar(0.3, 0.9, 0), K2A.ar(Line.kr(900, 50, 9))]) }),
	// Line with a control start: read once, the closed-form fallback
	SynthDef(\case_Line_var, { |knob = 0.2| Out.ar(0, [Line.ar(knob, 2, 3), K2A.ar(Line.kr(knob, -1, 1.5))]) },
		metadata: (specs: (knob: ControlSpec(-1, 1, \lin, 0, 0.2)))),
	SynthDef(\case_XLine, { Out.ar(0, [XLine.ar(0.01, 1, 0.7), XLine.ar(1, 0.001, 0.3), K2A.ar(XLine.kr(1, 0.1, 0.5))]) }),
	// EnvGen: all shapes, audio-rate and kr gates, release node with loop, .kr
	// EnvGen with audio-rate levels and a gate rising mid-block (levels read at the block's first
	// sample), and VarLag's default warp, which sclang builds from EnvGen + Changed + Impulse
	SynthDef(\case_EnvGen_arlevels, { Out.ar(0, [EnvGen.ar(Env([in.value, in.value.neg, 0], [0.01, 0.02], 3), in.value.abs > 0.2),
		VarLag.ar(in.value, 0.1)]) }),
	// Pan4.kr with constant positions (compile-time zero denominators in discarded branches)
	SynthDef(\case_Pan4_kr_const, { Out.ar(0, K2A.ar(Pan4.kr(Latch.kr(in.value, Impulse.kr(50)), 0, 0))) }),
	// LocalIn.kr / LocalOut.kr fed by audio: LocalOut.kr writes its input's first sample of the
	// block, LocalIn.kr holds it over the next block (census probe: 1.24 -> exact)
	SynthDef(\case_LocalIn_kr_audio, { var fb = LocalIn.kr(1, 0); LocalOut.kr(in.value + K2A.ar(fb * 0.5)); Out.ar(0, K2A.ar(fb)) }),
	SynthDef(\case_EnvGen, {
		var trig = Impulse.kr(1.5);
		Out.ar(0, [
			EnvGen.ar(Env([0.01, 1, 0.3, 0.8, 0.01], [0.05, 0.1, 0.15, 0.2], [\exp, \sin, \wel, \sqr]), trig),
			EnvGen.ar(Env([0, 1, 0.5, 0.7, 0.2, 0], [0.03, 0.1, 0.1, 0.05, 0.2], [\cub, \step, \hold, 3, -4]), trig),
			EnvGen.ar(Env.perc(0.005, 0.2), in.value > 0.1),
			EnvGen.ar(Env([0, 1, 0.2, 0], [0.05, 0.1, 0.2], \lin, 2, 0), LFPulse.kr(0.7, 0, 0.6), 0.8, 0.1, 1.5),
			K2A.ar(EnvGen.kr(Env.perc(0.01, 0.3, 1, -2), trig)),
			EnvGen.ar(Env.perc(0.01, 0.3), in.value * 1.5)   // audio gate dipping below -1: forced release
		] * 0.5)
	}),
	// Dynamics
	SynthDef(\case_Limiter, { |level = 0.3| Out.ar(0, [Limiter.ar(in.value, level, 0.01), Limiter.ar(in.value * 2, 0.5, 0.003)]) },
		metadata: (specs: (level: spec.(0.05, 1, 0.3)))),
	SynthDef(\case_Normalizer, { |level = 0.5| Out.ar(0, Normalizer.ar(in.value, level, 0.01)) },
		metadata: (specs: (level: spec.(0.05, 1, 0.5)))),
	SynthDef(\case_Compander, { |thresh = 0.2| Out.ar(0, [
		Compander.ar(in.value, in.value, thresh, 1, 0.3, 0.01, 0.1),          // compressor
		Compander.ar(in.value, in.value, thresh, 3, 1, 0.005, 0.05)]) },      // gate/expander
		metadata: (specs: (thresh: spec.(0.02, 0.8, 0.2)))),
	// Reverb
	SynthDef(\case_FreeVerb, { |room = 0.5| Out.ar(0, [FreeVerb.ar(in.value, 0.5, room, 0.5), FreeVerb.ar(in.value, 1, 0.9, 0.1)]) },
		metadata: (specs: (room: spec.(0, 1, 0.5, \lin)))),
	SynthDef(\case_FreeVerb2, { |room = 0.5| Out.ar(0, FreeVerb2.ar(in.value, in.value * -0.5, 0.5, room, 0.5)) },
		metadata: (specs: (room: spec.(0, 1, 0.5, \lin)))),
	SynthDef(\case_GVerb, { |revtime = 3| Out.ar(0, GVerb.ar(in.value, 10, revtime, 0.5, 0.5, 15, 1, 0.7, 0.5, 300) * 0.5) },
		metadata: (specs: (revtime: spec.(0.5, 10, 3)))),
	// Klank: 3 partials (remainder only), 6 partials (remainder + one group), scaled/offset
	SynthDef(\case_Klank, { Out.ar(0, [
		Klank.ar(`[[200, 671, 1153], [1, 0.5, 0.3], [1, 0.5, 0.25]], in.value),
		Klank.ar(`[[110, 220, 330, 440, 557, 1201], nil, [0.3, 0.6, 0.2, 1, 0.4, 0.05]], in.value, 1.5, 7, 0.5)
	] * 0.1) }),
	// PitchShift: up, down, a short window, a ratio moving at kr and at ar
	SynthDef(\case_PitchShift, { Out.ar(0, [
		PitchShift.ar(in.value, 0.2, 1.5),
		PitchShift.ar(in.value, 0.05, 0.7),
		PitchShift.ar(in.value, 0.0011, 2.3),
		PitchShift.ar(in.value, 0.1, LFTri.kr(0.7).range(0.5, 2)),
		PitchShift.ar(in.value, 0.1, SinOsc.ar(3).range(0.25, 4.5))
	]) }),
	// LocalIn/LocalOut (one per rate per SynthDef: a second LocalIn outputs zeros): audio
	// feedback through a filter, two LocalOuts summed, defaults in the first block, and a
	// control-rate loop. Started in block 1: in the server's first block, LocalIn reads
	// its uninitialised bus instead of the default (sc-findings 19).
	SynthDef(\case_LocalIn, {
		var fb = LocalIn.ar(3, [0.5, 0.1, -0.2]);
		var x = LPF.ar(in.value + (fb[0] * 0.7), 2000);
		var c = LocalIn.kr(1, 0.1);
		LocalOut.ar([x, fb[2] * 0.6, in.value]);
		LocalOut.ar([0, 0.25 * fb[1], fb[1] * 0.3]);
		LocalOut.kr((c * 1.07 + 0.01) % 1);
		Out.ar(0, [fb[0], x, fb[1], fb[2], K2A.ar(c)])
	}, metadata: (startBlock: 1)),
	// FSinOsc: audio and control rate, phases, low and high frequencies
	SynthDef(\case_FSinOsc, { Out.ar(0, [
		FSinOsc.ar(440), FSinOsc.ar(31.7, 1.2), FSinOsc.ar(9876.5, -0.5), FSinOsc.ar(0.3, pi/2),
		K2A.ar(FSinOsc.kr(3.3, 0.4))
	] * 0.5) }),
	// SinOscFB: constant, kr and audio-rate feedback and frequency; control rate
	SynthDef(\case_SinOscFB, { Out.ar(0, [
		SinOscFB.ar(220, 0.8), SinOscFB.ar(LFTri.kr(0.3).range(50, 900), Line.kr(0, 2.5, 4)),
		SinOscFB.ar(SinOsc.ar(2).range(100, 300), in.value * 4), SinOscFB.ar(3000, 1.4),
		K2A.ar(SinOscFB.kr(4.2, LFTri.kr(0.2).range(0, 1.5)))
	] * 0.5) }),
	// VarSaw: constant, kr and audio-rate frequency, moving width, initial phase, kr.
	// Inputs scsynth reads in the constructor come from Line (see README, constructor values)
	SynthDef(\case_VarSaw, { Out.ar(0, [
		VarSaw.ar(220), VarSaw.ar(LFTri.kr(0.3).range(50, 900), 0.3, Line.kr(0, 1, 6)),
		VarSaw.ar(SinOsc.ar(3).range(100, 300), 1.4, 0.1), VarSaw.ar(4321.7, 0, 0.93),
		K2A.ar(VarSaw.kr(5.5, 0.2, Line.kr(0.2, 0.8, 8)))
	] * 0.5) }),
	// SyncSaw: the four rate combinations and control rate
	SynthDef(\case_SyncSaw, { Out.ar(0, [
		SyncSaw.ar(110, 377), SyncSaw.ar(Line.kr(50, 300, 8), SinOsc.ar(0.5).range(400, 1200)),
		SyncSaw.ar(SinOsc.ar(2).range(100, 200), Line.kr(300, 900, 9)), SyncSaw.ar(1234.5, 2999),
		K2A.ar(SyncSaw.kr(3, Line.kr(5, 13, 7)))
	] * 0.5) }),
	// Blip: fixed, clipped harmonics, moving freq and numharm (crossfades), audio-rate freq
	SynthDef(\case_Blip, { Out.ar(0, [
		Blip.ar(220, 20), Blip.ar(3000, 200), Blip.ar(Line.kr(900, 50, 9), LFSaw.kr(0.5).range(1, 40)),
		Blip.ar(Line.kr(2000, 60, 8), 300), Blip.ar(SinOsc.ar(3).range(100, 300), 7)
	] * 0.5) }),
	// Formant: defaults, a low fundamental with a high formant, moving inputs (kr, ar)
	SynthDef(\case_Formant, { Out.ar(0, [
		Formant.ar, Formant.ar(87, 2345, 600), Formant.ar(Line.kr(100, 400, 9), LFTri.kr(0.3).range(500, 3000), 300),
		Formant.ar(SinOsc.ar(2).range(150, 250), 1500, SinOsc.ar(0.5).range(200, 900))
	] * 0.5) }),
	// Klang: 3 partials with phases, 8 partials (two groups) scaled and offset
	SynthDef(\case_Klang, { Out.ar(0, [
		Klang.ar(`[[200, 671, 1153], [0.3, 0.2, 0.1], [0, 1, pi]]),
		Klang.ar(`[[100, 200, 300, 400, 510, 620, 777, 1999], nil, [0, 0.5, 0, 1, 0, 2, 0, 3]], 1.25, 13)
	] * 0.1) }),
	// LFGauss: defaults, iphase, one-shot (loop 0), audio-rate duration and width, kr
	SynthDef(\case_LFGauss, { Out.ar(0, [
		LFGauss.ar, LFGauss.ar(0.013, 0.3, 0.4), LFGauss.ar(2, 0.2, 0, 0),
		LFGauss.ar(SinOsc.ar(0.3).range(0.005, 0.02), SinOsc.ar(0.7).range(0.05, 0.3)),
		K2A.ar(LFGauss.kr(0.37, Line.kr(0.1, 0.4, 5)))
	] * 0.5) }),
	// Phasor: free-running (kk), kr trigger, audio trigger with sub-sample reset, audio rate,
	// rate above the range (floor branch), negative rate, control rate
	SynthDef(\case_Phasor, { Out.ar(0, [
		Phasor.ar(0, 0.01), Phasor.ar(Impulse.kr(3), 0.003, -1, 1, 0.5),
		Phasor.ar(in.value, 0.0045833, 0, 1, 0.2),
		Phasor.ar(Impulse.ar(7.3), SinOsc.ar(0.4).range(0.001, 0.02), 0, 2),
		Phasor.ar(0, 2.7, 0, 1), Phasor.ar(0, -0.013, -0.5, 0.5),
		K2A.ar(Phasor.kr(Impulse.kr(1.1), 0.05, 0, 3))
	] * 0.5) }),
	// Vibrato (variations 0): plain, delay and onset, phase and depth, audio input, retrigger
	SynthDef(\case_Vibrato, { Out.ar(0, [
		Vibrato.ar(DC.ar(1), 6, 0.02, 0, 0, 0, 0), Vibrato.ar(DC.ar(1), 5, 0.1, 0.1, 0.3, 0, 0),
		Vibrato.ar(DC.ar(1), 3.3, 0.2, 0, 0, 0, 0, 0.3), Vibrato.ar(in.value, 7, 0.05, 0, 0.05, 0, 0),
		Vibrato.ar(DC.ar(1), 4, 0.1, 0.05, 0.1, 0, 0, 0.6, Impulse.kr(0.7)),
		K2A.ar(Vibrato.kr(1, 2.5, 0.3, 0, 0.5, 0, 0))
	] * 0.5) }),
	// Wrap, Fold, Clip: constant, kr (ramped per block) and audio-rate bounds, inputs far
	// outside the range (the floor branch), a degenerate range, control rate. Wrap/Fold's
	// accumulated ramps start from the constructor value: kr bounds from Line (README)
	SynthDef(\case_Wrap, {
		var x = in.value * 3, s = SinOsc.ar(0.3) * 4;
		Out.ar(0, [
			Wrap.ar(x, -0.5, 0.5), Wrap.ar(s, Line.kr(-1, 0, 7), Line.kr(1.5, 0.2, 9)),
			Wrap.ar(x, SinOsc.ar(2) * 0.3 - 0.5, 0.7), Wrap.ar(s, 0.2, 0.2),
			Fold.ar(x, -0.5, 0.5), Fold.ar(s, Line.kr(-1, 0, 7), Line.kr(1.5, 0.2, 9)),
			Fold.ar(s * 3, SinOsc.ar(2) * 0.3 - 0.5, 0.7), Fold.ar(s, 0.2, 0.2),
			Clip.ar(x, -0.5, 0.5), Clip.ar(s, LFTri.kr(0.5).range(-1, 0), LFSaw.kr(0.3).range(0.2, 1.5)),
			Clip.ar(x, SinOsc.ar(2) * 0.3 - 0.5, 0.7), Clip.ar(s, -0.3, LFTri.kr(1.1)),
			K2A.ar(Wrap.kr(LFSaw.kr(0.2) * 3, -1, LFTri.kr(0.4) + 1.5)), K2A.ar(Fold.kr(LFSaw.kr(0.2) * 3, -1, 0.5)),
			K2A.ar(Clip.kr(LFSaw.kr(0.2) * 3, -1, LFTri.kr(0.4)))
		] * 0.5)
	}),
	// LinExp: constant bounds (nova pow at ar), control-rate bounds (per block), audio-rate
	// bounds (both of a pair: sc-findings 22), control rate
	SynthDef(\case_LinExp, {
		var x = in.value, s = SinOsc.ar(0.3);
		Out.ar(0, [
			LinExp.ar(x, -1, 1, 20, 2000) * 0.001, LinExp.ar(s, Line.kr(-1, -0.5, 5), 1, 0.1, Line.kr(10, 3, 7)),
			LinExp.ar(s, DC.ar(-1), SinOsc.ar(2) * 0.2 + 1, 0.1, 10), LinExp.ar(s, -1, 1, DC.ar(0.1), SinOsc.ar(0.5) + 3),
			K2A.ar(LinExp.kr(LFTri.kr(0.2), -1, 1, 0.5, 4)), K2A.ar(LinExp.kr(LFTri.kr(0.2), -1, Line.kr(1, 2, 6), 0.5, 4))
		] * 0.2)
	}),
	// InRange, InRect, Schmidt, ModDif: constant and kr bounds, audio and control rate
	SynthDef(\case_InRange, {
		var x = in.value * 2, s = SinOsc.ar(1.3);
		Out.ar(0, [
			InRange.ar(x, -0.2, 0.3), InRange.ar(s, LFTri.kr(0.4) * 0.5, 0.6),
			InRect.ar(s, SinOsc.ar(0.7), Rect(-0.5, -0.3, 1, 0.9)),
			Schmidt.ar(x, -0.1, 0.2), Schmidt.ar(s, LFTri.kr(0.3) * 0.4 - 0.2, 0.5),
			ModDif.ar(x, 0.1, 0.5), ModDif.ar(s * 3, Line.kr(0, 1, 5), Line.kr(0.4, 1.3, 8)),
			K2A.ar(InRange.kr(LFSaw.kr(0.5), 0, 0.5)), K2A.ar(Schmidt.kr(LFSaw.kr(0.5), -0.3, 0.3)),
			K2A.ar(ModDif.kr(LFSaw.kr(0.5) * 2, 0.3, LFTri.kr(0.2) + 1.5))
		] * 0.5)
	}),
	// Trig, Trig1, TDelay, ToggleFF, SetResetFF: audio and control-rate triggers, an initial
	// trigger (counted from the constructor sample), retriggers while counting, control rate
	SynthDef(\case_Trig, {
		var x = in.value, ia = Impulse.ar(13), ik = Impulse.kr(5);
		Out.ar(0, [
			Trig.ar(x, 0.01), Trig.ar(ik * 0.6, 0.05), Trig1.ar(x, 0.003), Trig1.ar(ia, 0.1),
			Trig1.ar(DC.ar(1), 0.02), Trig.ar(ik, Line.kr(0.01, 0.3, 8)),
			TDelay.ar(x, 0.002), TDelay.ar(ia, 0.05), TDelay.ar(DC.ar(1), 0.01),
			ToggleFF.ar(x), ToggleFF.ar(ia), SetResetFF.ar(x, ia), SetResetFF.ar(ia, Impulse.kr(3.3)),
			K2A.ar(Trig1.kr(Impulse.kr(2), 0.2)), K2A.ar(TDelay.kr(Impulse.kr(2), 0.1)),
			K2A.ar(ToggleFF.kr(Impulse.kr(3))), K2A.ar(SetResetFF.kr(Impulse.kr(3), Impulse.kr(1.3)))
		] * 0.5)
	}),
	// PulseCount, PulseDivider, Stepper, Timer, ZeroCrossing, Sweep: audio and kr resets,
	// constant resets, start offsets, wrapping steps, the four Sweep calc functions, kr
	SynthDef(\case_PulseCount, {
		var x = in.value, ia = Impulse.ar(17), ib = Impulse.ar(2.3), ik = Impulse.kr(1.7);
		Out.ar(0, [
			PulseCount.ar(ia, ib) * 0.05, PulseCount.ar(x, ik) * 0.01, PulseCount.ar(ia) * 0.001,
			PulseDivider.ar(ia, 3), PulseDivider.ar(x, Line.kr(2, 7, 9), 1.5),
			Stepper.ar(ia, ib, -3, 4, 3, 1) * 0.1, Stepper.ar(x, ik, 0, 7, -2) * 0.1, Stepper.ar(ia, 0, 2, 9, 5, 4) * 0.1,
			Timer.ar(ia), Timer.ar(x), ZeroCrossing.ar(SinOsc.ar(Line.kr(100, 2000, 9))) * 0.001, ZeroCrossing.ar(x) * 0.001,
			Sweep.ar(ia, 3), Sweep.ar(x, SinOsc.ar(0.4).range(0.5, 4)), Sweep.ar(ik, Line.kr(1, 5, 7)),
			Sweep.ar(ik, SinOsc.ar(0.3).range(1, 2)), Sweep.ar(0, 0.1),
			K2A.ar(PulseCount.kr(Impulse.kr(9), Impulse.kr(1))) * 0.1, K2A.ar(Stepper.kr(Impulse.kr(9), 0, 0, 5)) * 0.1,
			K2A.ar(Sweep.kr(Impulse.kr(0.7), 2)), K2A.ar(Timer.kr(Impulse.kr(3)))
		] * 0.5)
	}),
	// Gate, Peak, RunningMin/Max, PeakFollower, MostChange, LeastChange, LastValue, T2A:
	// audio, kr and constant triggers, a changing decay, control rate. Inputs read in the
	// constructor (initial levels) come from SinOsc.kr (README, constructor values)
	SynthDef(\case_Peak, {
		var x = in.value, s = SinOsc.ar(3.1), ia = Impulse.ar(4.3), ik = Impulse.kr(2.1);
		Out.ar(0, [
			Gate.ar(x, s), Gate.ar(x, LFPulse.kr(3)), Peak.ar(x, ia), Peak.ar(x, ik), Peak.ar(s * 0.5),
			RunningMin.ar(x, ia), RunningMin.ar(s, ik), RunningMax.ar(x, ia), RunningMax.ar(s, ik), RunningMax.ar(x),
			PeakFollower.ar(x, 0.999), PeakFollower.ar(x, Line.kr(0.99, 0.9999, 6)), PeakFollower.ar(s, Line.kr(0.5, -0.5, 4)),
			MostChange.ar(x, s), LeastChange.ar(x, s), MostChange.ar(x, LFTri.kr(1)),
			LastValue.ar(x, 0.05), LastValue.ar(SinOsc.kr(0.7), 0.3), T2A.ar(ik), T2A.ar(Impulse.kr(3.3), 17),
			K2A.ar(Peak.kr(SinOsc.kr(0.6), Impulse.kr(1))), K2A.ar(RunningMin.kr(SinOsc.kr(0.6))),
			K2A.ar(PeakFollower.kr(SinOsc.kr(0.6), 0.9)), K2A.ar(MostChange.kr(SinOsc.kr(0.6), SinOsc.kr(0.9))),
			K2A.ar(LastValue.kr(SinOsc.kr(0.6), 0.2)), K2A.ar(Gate.kr(SinOsc.kr(0.6), LFPulse.kr(0.4)))
		] * 0.5)
	}),
	// LinPan2, Balance2, XFade2, LinXFade2, Rotate2, Pan4: constant, kr and audio-rate
	// positions, kr levels, positions outside the range, control rate
	SynthDef(\case_Pan4, {
		var x = in.value, s = SinOsc.ar(220) * 0.5, kp = SinOsc.kr(0.3) * 1.3, ap = SinOsc.ar(0.7);
		Out.ar(0, LinPan2.ar(x, 0.3) ++ LinPan2.ar(x, kp, Line.kr(1, 0.2, 5)) ++ LinPan2.ar(x, ap)
			++ Balance2.ar(x, s, -0.4) ++ Balance2.ar(x, s, kp, 0.7) ++ Balance2.ar(x, s, ap, Line.kr(0.5, 1, 4))
			++ [XFade2.ar(x, s, 0.2), XFade2.ar(x, s, kp), XFade2.ar(x, s, ap, Line.kr(1, 0.3, 6)),
				LinXFade2.ar(x, s, -0.6), LinXFade2.ar(x, s, kp), LinXFade2.ar(x, s, ap)]
			++ Rotate2.ar(x, s, 0.3) ++ Rotate2.ar(x, s, SinOsc.kr(0.2))
			++ Pan4.ar(x, 0.2, -0.5) ++ Pan4.ar(x, kp, SinOsc.kr(0.17) * 1.5, Line.kr(1, 0.5, 7))
			++ K2A.ar(Pan2.kr(SinOsc.kr(1.1), SinOsc.kr(0.3))) ++ K2A.ar(Rotate2.kr(SinOsc.kr(1.1), SinOsc.kr(0.6), SinOsc.kr(0.2)))
			++ K2A.ar(Pan4.kr(SinOsc.kr(1.1), SinOsc.kr(0.3) * 1.4, SinOsc.kr(0.23)))
		)
	}),
	// LPZ1, HPZ1, LPZ2, HPZ2, BPZ2, BRZ2, Slope at audio and control rate
	SynthDef(\case_LPZ, {
		var x = in.value, k = SinOsc.kr(3.3) + SinOsc.kr(11.7, 0, 0.3);
		Out.ar(0, [LPZ1.ar(x), HPZ1.ar(x), LPZ2.ar(x), HPZ2.ar(x), BPZ2.ar(x), BRZ2.ar(x), Slope.ar(x) * 0.0001]
			++ K2A.ar([LPZ1.kr(k), HPZ1.kr(k), LPZ2.kr(k), HPZ2.kr(k), BPZ2.kr(k), BRZ2.kr(k), Slope.kr(k) * 0.01]))
	}),
	// FOS, SOS: constant (a resonant lowpass at 300 Hz, Q 8), per-block (Line) and audio-rate
	// coefficients, control rate
	SynthDef(\case_SOS, {
		var x = in.value, w = 2pi * 300 / 48000, al = sin(w) / 16, n = 1 + al;
		var a0 = (1 - cos(w)) / 2 / n, a1 = (1 - cos(w)) / n, b1 = 2 * cos(w) / n, b2 = (al - 1) / n;
		Out.ar(0, [
			SOS.ar(x, a0, a1, a0, b1, b2), SOS.ar(x, a0, a1, a0, Line.kr(b1, b1 * 0.999, 4), b2),
			SOS.ar(x, DC.ar(0.3), DC.ar(0.2), DC.ar(0.1), SinOsc.ar(0.5) * 0.3 + 1.2, DC.ar(-0.6)),
			FOS.ar(x, 0.1, 0.1, 0.8), FOS.ar(x, Line.kr(0.1, 0.5, 5), 0.2, Line.kr(0.9, 0.99, 7)),
			FOS.ar(x, DC.ar(0.3), DC.ar(-0.3), SinOsc.ar(0.3) * 0.2 + 0.7),
			K2A.ar(SOS.kr(SinOsc.kr(3), 0.3, 0.2, 0.1, 1.2, -0.6)), K2A.ar(FOS.kr(SinOsc.kr(3), 0.3, 0.2, 0.7))
		] * 0.3)
	}),
	// Noise: statistics only (scsynth's generator is seeded per server). Each at ar and kr.
	// Rates and densities stay >= 100/s: a statistical comparison needs ~1000 random events
	// per render (LFNoise2 at 20 Hz over 10 s varies ±2.4 dB from seed to seed).
] ++ [\WhiteNoise, \ClipNoise, \GrayNoise, \PinkNoise, \BrownNoise].collect { |u|
	[SynthDef(("case_" ++ u).asSymbol, { Out.ar(0, u.asClass.ar * 0.5) }, metadata: (signals: [\silence])),
	 SynthDef(("case_" ++ u ++ "_kr").asSymbol, { Out.ar(0, K2A.ar(u.asClass.kr) * 0.5) }, metadata: (signals: [\silence]))]
}.flatten ++ [\Dust, \Dust2].collect { |u|
	[SynthDef(("case_" ++ u).asSymbol, { |density = 200| Out.ar(0, u.asClass.ar(density) * 0.5) },
		metadata: (specs: (density: spec.(100, 5000, 200)), signals: [\silence])),
	 SynthDef(("case_" ++ u ++ "_kr").asSymbol, { Out.ar(0, K2A.ar(u.asClass.kr(100)) * 0.5) }, metadata: (signals: [\silence]))]
}.flatten ++ [\LFNoise0, \LFNoise1, \LFNoise2].collect { |u|
	[SynthDef(("case_" ++ u).asSymbol, { |freq = 500| Out.ar(0, u.asClass.ar(freq) * 0.5) },
		metadata: (specs: (freq: spec.(100, 5000, 500)), signals: [\silence])),
	 SynthDef(("case_" ++ u ++ "_kr").asSymbol, { Out.ar(0, K2A.ar(u.asClass.kr(100)) * 0.5) }, metadata: (signals: [\silence]))]
}.flatten
)
