// BinaryOpUGen pow on a bipolar signal (SC keeps the sign).
SynthDef(\case_BinaryOp_pow, { |x = 0.5| Out.ar(0, SoundIn.ar(0) ** x) },
	metadata: (specs: (x: ControlSpec(0.25, 3, \lin, 0, 0.5))))
