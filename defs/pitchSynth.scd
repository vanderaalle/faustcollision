// pitchSynth: the memorandum's translator test case.
// Pitch → 5 harmonic Saws → MoogFF × Amplitude. Knob: filter cutoff, 100 Hz – 8 kHz.
// minFreq 30 so low B and E on bass are tracked (Pitch default is 60).
SynthDef(\pitchSynth, { |knob = 0.5|
	var in = SoundIn.ar(0);
	var freq = Pitch.kr(in, minFreq: 30, maxFreq: 1000)[0];
	var amp = Amplitude.kr(in);
	var harmonics = Saw.ar(freq * [1, 2, 3, 4, 5]) * [1, 1/2, 1/3, 1/4, 1/5];
	var cutoff = 100 * (80 ** knob);
	Out.ar(0, MoogFF.ar(harmonics.sum, cutoff, 2) * amp);
}, metadata: (
	specs: (knob: ControlSpec(0, 1, \lin, 0, 0.5)),
	// Pitch trackers disagree arbitrarily on impulses and noise; layer 3 still sweeps those.
	signals: [\bass_di, \sweep]
))
