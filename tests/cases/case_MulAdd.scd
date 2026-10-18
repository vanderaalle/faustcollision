// MulAdd with kr mul and add.
SynthDef(\case_MulAdd, { |mul = 0.5, add = 0.1| Out.ar(0, MulAdd(SoundIn.ar(0), mul, add)) },
	metadata: (specs: (mul: ControlSpec(-1, 1, \lin, 0, 0.5), add: ControlSpec(-0.5, 0.5, \lin, 0, 0.1))))
