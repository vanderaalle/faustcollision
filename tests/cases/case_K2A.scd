// K2A: a kr control brought to audio rate.
SynthDef(\case_K2A, { |x = 0.5| Out.ar(0, SoundIn.ar(0) * K2A.ar(x)) },
	metadata: (specs: (x: ControlSpec(0, 1, \lin, 0, 0.5))))
