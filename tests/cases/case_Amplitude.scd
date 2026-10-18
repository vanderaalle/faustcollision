// Amplitude, both rates: ch 0 the .ar envelope, ch 1 the input scaled by the .kr envelope.
SynthDef(\case_Amplitude, { var in = SoundIn.ar(0);
	Out.ar(0, [Amplitude.ar(in, 0.01, 0.1), in * Amplitude.kr(in)]) })
