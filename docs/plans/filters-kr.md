# Filter .kr

Prepared, not yet applied or tested. Apply, build, test, measure tolerances.


All of LPF, HPF, RLPF, RHPF, BPF, BRF, Resonz, Ringz, Formlet, TwoPole, TwoZero, APF,
MidEQ, OnePole, OneZero, LeakDC have .kr. One step per block at SAMPLERATE = SR / 64
(mRadiansPerSample = 2 pi / 750), double state zapped every step.

Two groups (sc-findings 28, measured on Resonz/APF):
- _next_1 (LPF, HPF, RLPF, RHPF, BPF, BRF, Formlet, LeakDC): coefficients from the
  block's inputs, used at once.
- ar function with loops 0 / remain 1 (Resonz, Ringz, TwoPole, TwoZero, APF, MidEQ,
  OneZero): the block uses the stored coefficients; new ones from the next block on. The
  constructor (PUSH_LOOPVALS: also loops 0 / remain 1) runs one sample with zero
  coefficients (output 0, y1 = in[0]) and stores the first coefficients.
- APF.kr = the input (identity); port as `_` after checking the constructor sample.
- OnePole.kr: OnePole_next_a / _next_k with 1 sample: read which (coef ar vs kr); the k
  version ramps over the block with mSlopeFactor = 1 -> a jump.

Port: generic `rec2_kr(step, coefs, x, late)` (state y1, y2 as float or pair, stepped at
krclk, coefficients from a2k inputs at kr rate, `late` = use kprev(coefs)), reusing the
coefficient expressions of the ar ports with ma.SR replaced by SR / 64 (most use
`ma.SR` inline: give them an sr parameter, as for B filters' beqw).
Precision: as the ar float floors; low-frequency kr filters (30 Hz at 750 Hz is like
1.9 kHz at 48 kHz) are well conditioned.

Cases: X.kr(LFNoise0.kr(200), knob freq) through K2A, a stepped freq (the late/at-once
distinction), constants.

