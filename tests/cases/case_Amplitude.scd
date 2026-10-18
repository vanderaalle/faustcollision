// Amplitude, all three calc functions: ch 0 the .ar envelope, ch 1 the input scaled by the
// .kr envelope of an audio input, ch 2 the .kr envelope of a kr input (true control-rate follower).
SynthDef(\case_Amplitude, { var in = SoundIn.ar(0);
	Out.ar(0, [Amplitude.ar(in, 0.01, 0.1), in * Amplitude.kr(in), K2A.ar(Amplitude.kr(A2K.kr(in), 0.01, 0.1))]) })
