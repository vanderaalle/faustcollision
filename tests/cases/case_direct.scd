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
	SynthDef(\case_LFPar_kr, { |freq = 3| Out.ar(0, K2A.ar(LFPar.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
	SynthDef(\case_LFCub, { |freq = 440| Out.ar(0, [LFCub.ar(freq, 0.2), LFCub.ar(in.value * 300 + 200)] * 0.5) },
		metadata: (specs: (freq: spec.(0.5, 5000, 440)))),
	SynthDef(\case_LFCub_kr, { |freq = 3| Out.ar(0, K2A.ar(LFCub.kr(freq))) }, metadata: (specs: (freq: spec.(0.1, 300, 3)), signals: [\impulse])),
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
	// Delays: constant and knob (kr) delay time; Delay1/2 (audio-rate delay time: not mapped yet)
	SynthDef(\case_DelayN, { |dt = 0.01| Out.ar(0, [DelayN.ar(in.value, 0.2, 0.0123), DelayN.ar(in.value, 0.2, dt)]) },
		metadata: (specs: (dt: spec.(0.0001, 0.2, 0.01)))),
	SynthDef(\case_DelayL, { |dt = 0.01| Out.ar(0, [DelayL.ar(in.value, 0.2, 0.0123), DelayL.ar(in.value, 0.2, dt)]) },
		metadata: (specs: (dt: spec.(0.0001, 0.2, 0.01)))),
	SynthDef(\case_Delay1, { Out.ar(0, Delay1.ar(in.value)) }),
	SynthDef(\case_Delay2, { Out.ar(0, Delay2.ar(in.value)) }),
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
