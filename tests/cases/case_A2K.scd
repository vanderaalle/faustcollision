// A2K → K2A round trip: first sample per block, ramped across the next. Exact in both directions.
SynthDef(\case_A2K, { Out.ar(0, K2A.ar(A2K.kr(SoundIn.ar(0)))) })
