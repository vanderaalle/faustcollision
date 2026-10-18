// MoogFF on the input, kr cutoff and gain.
SynthDef(\case_MoogFF, { |freq = 1000, gain = 2| Out.ar(0, MoogFF.ar(SoundIn.ar(0), freq, gain)) },
	metadata: (specs: (freq: ControlSpec(50, 10000, \exp, 0, 1000), gain: ControlSpec(0, 4, \lin, 0, 2))))
