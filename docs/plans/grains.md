# GrainSin, GrainFM, GrainIn (GrainUGens.cpp)

Deterministic given the triggers: compare by waveform.

## Scope
- envbufnum = -1 only (the built-in Hann; any other value reads a buffer: buffers are
  excluded by design): `require`.
- maxGrains: a constant. A trigger is refused when `mNumActive + 1 >= mMaxGrains`
  ("Too many grains!"), so at most maxGrains - 1 grains play: V = maxGrains - 1 voices.
  Default 512 -> 511 voices: measure the compile time; that is what the SynthDef asks for.
- numChannels 1, 2, > 2 (CALC_GRAIN_PAN).
- GrainIn's `in`: audio rate only (IN(2)[j]; a kr input would read past its one value).

## Per grain (voice)
- Start on a rising trigger (curtrig <= 0 and trig > 0; ar: per sample, kr: per block at
  position 0). Inputs read at the trigger sample (ar) or the block start (kr); GrainFM
  reads its inputs with GRAIN_IN_AT (the audio sample when audio rate, also at kr).
- counter = (int)max(4, dur * SR) samples. Hann by a resonator in double (float pairs):
  w = pi / max(4, dur * SR) (the double, before the (int) cast), b1 = 2 cos w, y1 = sin w,
  y2 = 0, amp = y1^2; per sample: output amp *
  osc, then y0 = b1 y1 - y2, y2 = y1, y1 = y0, amp = y1^2.
- GrainSin: phase int32 from 0, inc (int32)(cpstoinc * freq), lookupi1.
- GrainFM: mod phase from 0, mfreq = (int32)(cpstoinc * modfreq), deviation = index *
  modfreq; per sample thismod = sin(mphase) * deviation, carrier sin(cphase), then cphase
  += (int32)(cpstoinc * (carfreq + thismod)), mphase += mfreq.
- GrainIn: amp * in.
- Pan: 1 out: pan1 = 1; 2 outs: pan = clip(pan * 0.5 + 0.5, 0, 1), angle = pan * pi/2,
  (cos, sin) into channels 0, 1; > 2: pan = wrap(pan * 0.5, 0, 1), cpan = n * pan + 0.5,
  chan = floor(cpan) (wrapped), angle = frac * pi/2, (cos, sin) into chan, chan + 1 (mod n).

## Allocation
Voices are interchangeable (the output is a sum; scsynth's array order only changes the
summation order: ~1 ulp). A trigger takes the lowest free voice; free = counter <= 0.
scsynth frees a grain at the end of the block it ends in, before that block's triggers:
a trigger can reuse a slot whose grain is still sounding earlier in the same block. With
V = maxGrains - 1 voices this differs only at saturation (all voices busy): documented.

## Cases
waveform: GrainSin mono with Impulse triggers (overlapping grains), stereo with pan
sweep, 4 channels; kr trigger; GrainFM; GrainIn on a test signal; maxGrains small enough
to saturate (the refusal).
