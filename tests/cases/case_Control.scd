// Control: a spec'd kr control scaling the input.
SynthDef(\case_Control, { |gain = 0.5| Out.ar(0, SoundIn.ar(0) * gain) },
	metadata: (specs: (gain: ControlSpec(0, 1, \lin, 0, 0.5))))
