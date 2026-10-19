# Delays, combs, allpasses .kr

Prepared, not yet applied or tested. Apply, build, test, measure tolerances.


C (DelayUGens.cpp): .kr runs the same calc functions (the `_z` checked variants until the
line is filled, then the plain ones) with inNumSamples = 1 and the control rate's
SAMPLERATE (SR / 64 = 750 Hz):
- buffer: ceil(maxdelay * 750 + 1) + 1 (BUFLENGTH 1), next power of two (line 3440);
- dsamp = clip(delaytime * 750.f, minDelaySamples, fdelaylen) (CalcDelay, 3458; float
  product, as at ar);
- delaytime change: CALCSLOPE with mSlopeFactor 1 -> dsamp jumps to the new value within
  the block's single sample (dsamp += slope before the read);
- decaytime -> feedback via sc_CalcFeedback(delaytime, decaytime) (unchanged maths);
- constructor output 0 (ZOUT0(0) = 0), no step; DelayUnit_init_0 (constant zero delay):
  check what it does at kr (a pass-through calc function?).
So .kr is the ar algorithm on the sequence of block values, one sample per block.

Port idea: no new algorithm. Give the ar delay/comb/allpass ports an `sr` and a `clk`:
- the line: a Faust delay of the block-held input by blocksize * k samples reads block
  b - k exactly (held signals are constant across the block), so integer taps become
  x@(blocksize * k) and the interpolations combine the block values at k and k + 1 (k + 2,
  k - 1 for cubic) exactly as the ar ports combine samples;
- feedback (Comb, Allpass): the recursion must update only at krclk (select2(krclk, y1, y)),
  else it would run 64 times per block; the feedback taps read y@(blocksize * k);
- dsamp in kr samples: delaytime * (SR / 64) as a float product; minDelaySamples and the
  fdelaylen clip as at ar (with the kr buffer length from derive.py: it depends on
  maxdelay, a constant).
- the `_z` start-up: reads of the not-yet-written line return 0 (ar ports model this:
  reuse, counting blocks instead of samples). AllpassC's start-up quirk (sc-findings 17)
  applies at kr too.
Delay1.kr / Delay2.kr: the previous / second previous block value (Delay1: the
constructor primes x1 with in[0]; Delay2: out[0] = 0, out[1] = in[0]).

Cases: K2A.ar(DelayN.kr(LFNoise0.kr(200), 0.2, knob)), DelayL/C with a fractional
block delay (e.g. 0.0213 s = 15.975 blocks), CombN/L/C with feedback, a delay time stepping
mid-run, maxdelay so that the clip to fdelaylen is reached (long delay time knob), and
Delay1/Delay2.kr.

sc.lib today (lines ~619-640): dlylen(maxdt, sr) already takes the rate but adds
`blocksize` as BUFLENGTH: make it dlylen_g(maxdt, sr, buflen) (kr: buflen 1); dly() reads
x @ int(d) per sample: the kr version reads x @ (blocksize * int(d)) on the held input;
dsamp_k / dsampc compute delaytime * SR: add the rate parameter.

