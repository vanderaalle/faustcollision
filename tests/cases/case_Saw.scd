// Saw.ar with kr frequency; ignores the input.
SynthDef(\case_Saw, { |freq = 220| Out.ar(0, Saw.ar(freq) * 0.5) },
	metadata: (specs: (freq: ControlSpec(30, 2000, \exp, 0, 220)), signals: [\impulse]))
