// Pitch: a Saw following the tracked frequency (statistics only: the tracker is not a port).
SynthDef(\case_Pitch, { Out.ar(0, Saw.ar(Pitch.kr(SoundIn.ar(0), minFreq: 30, maxFreq: 1000)[0]) * 0.2) },
	metadata: (signals: [\bass_di, \sweep]))
