# MoogFF .kr

Prepared (source read), not yet written.

C (FilterUGens.cpp, MoogFF_next): the same calc function runs at kr with one sample per
block and the control rate's SAMPLEDUR / SAMPLERATE (64 / SR, SR / 64):
- freq: wcD = 2 tan(T pi freq) * SAMPLERATE recomputed when freq changes, used at once
  (no ramp). At kr the tan pole sits at 375 Hz: freq near or above it gives huge or
  negative wcD; the code clamps wcD < 0 to 0, so b0 = 0 and the filter closes. Measured
  (NRT, freq Line.kr(300, 450), gain 2): finite throughout; above 380 Hz the output decays
  to silence (max 0.006). A sensible guard: no finding; port the clamp.
- gain k: CALCSLOPE ramp with k += slope_k after the sample (slope factor 1 at kr): a gain
  change applies one block late (as sc-findings 28).
- reset (IN0(3) > 0) clears the state: required 0, as for .ar.
- Constructor: one sample (MoogFF_next(unit, 1)) from zero state with m_freq
  uninitialised: the first block continues from that state.

Port: the ar sc.moogff stepped at krclk with SR / 64, k via kprev; tier "approximate"
like .ar (float floor near self-oscillation). Case: K2A.ar(MoogFF.kr(LFNoise0.kr(200),
knob freq 1..300, gain 0..3.5)).

## Attempt (backed out): a Faust miscompilation to understand first

A port mirroring sc.moogff with the state gated by `select2(krclk, old, new)` (code below)
matched scsynth to 3e-7 in a probe, but failed the regression case (0.77): with two
MoogFF.kr instances whose frequencies are non-constant, or with the frequency passed
through `sc.a2k(slider)`, the gated state advances at samples where krclk is false (at a
signal onset the output changes at block offsets 1 and 2, with the values scsynth has
for the next blocks). With a constant, a raw slider, or a per-sample expression of a
constant, it is right; the ar sc.moogff is unaffected; the filter .kr ports (iir2_kr,
same gating) pass with stepped frequencies. Minimal reproduction (pure Faust, no
scsynth): `moogff-kr-repro/m1b.dsp` vs `m1bw.dsp` differ by 0.25 although `a2k(f1)` and
`f1` print the same values; `m2.dsp` (two instances) changes instance B's output.
Next: dump the C++ (`faust -lang cpp`) of m1b and m1bw and compare the state updates;
suspect select2-to-conditional optimisation or the sAndH recursion scheduling.

```
moogff_kr(freq, gain, x) = (step ~ (_, _, _, _)) : !, !, !, !, _
with {
    k = max(0, min(4, kprev(gain)));
    wcD = max(0, 2 * tan(ma.PI * freq / srk) * srk);
    TwcD = wcD / srk; b0 = TwcD / (TwcD + 2); a1 = (TwcD - 2) / (TwcD + 2); b4 = b0 * b0 * b0 * b0;
    step(s1, s2, s3, s4) = nx(s1, s1n), nx(s2, s2n), nx(s3, s3n), nx(s4, s4n), y
    with {
        o = s4 + b0 * (s3 + b0 * (s2 + b0 * s1));
        y = (b4 * x + o) / (1 + b4 * k); u = x - k * y;
        f1 = b0 * u + s1; s1n = b0 * u - a1 * f1; f2 = b0 * f1 + s2; s2n = b0 * f1 - a1 * f2;
        f3 = b0 * f2 + s3; s3n = b0 * f2 - a1 * f3; s4n = b0 * f3 - a1 * y;
        nx(o1, n1) = select2(krclk, o1, n1);
    };
};
```
