// DC: a constant audio-rate signal.
SynthDef(\case_DC, { Out.ar(0, SoundIn.ar(0) + DC.ar(0.25)) })
