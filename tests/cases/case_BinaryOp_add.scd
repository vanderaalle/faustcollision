// BinaryOpUGen +
SynthDef(\case_BinaryOp_add, { |x = 0.25| Out.ar(0, SoundIn.ar(0) + x) },
	metadata: (specs: (x: ControlSpec(-1, 1, \lin, 0, 0.25))))
