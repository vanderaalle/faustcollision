// BinaryOpUGen *, audio × audio.
SynthDef(\case_BinaryOp_mul, { var in = SoundIn.ar(0); Out.ar(0, in * (in + 0.5)) })
