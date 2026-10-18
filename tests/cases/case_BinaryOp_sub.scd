// BinaryOpUGen -
SynthDef(\case_BinaryOp_sub, { |x = 0.25| Out.ar(0, SoundIn.ar(0) - x) },
	metadata: (specs: (x: ControlSpec(-1, 1, \lin, 0, 0.25))))
