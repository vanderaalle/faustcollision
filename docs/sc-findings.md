# scsynth behaviour found while translating

Behaviour of scsynth (SuperCollider 3.13.0) that the documentation does not state,
found by comparing renders sample by sample or by porting the C++. Source references
are to the `Version-3.13.0` tag (`~/src/supercollider`).

Issue drafts for #4, #5, #11: `docs/issues/`.

Status: **measured** = confirmed on scsynth NRT renders; **source** = read in the C++,
not yet confirmed by a render. Kind: **bug?** (looks unintended), **undocumented**,
**convention** (intended, but matters for porting), **limitation**.

| # | UGen | Behaviour | Kind | Status |
| --- | --- | --- | --- | --- |
| 1 | `Amplitude.kr` (audio input) | attack/release 64× faster than stated | bug? | measured, source |
| 2 | `Saw` | falling ramp, every harmonic −6 dB vs an ideal ±1 saw | undocumented | measured |
| 3 | all (constructors) | first input sample processed twice | convention | measured |
| 4 | `BinaryOpUGen` `rrand` (audio rate) | draws from −1..1: range [2a−b, b); kr is correct | bug? | measured, source |
| 5 | `BinaryOpUGen` `unsignedRightShift`, `fill` | not implemented: compute `a + b` | bug? | measured, source |
| 6 | `UnaryOpUGen` `asInteger`, `asFloat` | pass the signal through | undocumented | source |
| 7 | `UnaryOpUGen` `log2` | float version takes no `abs`; double version and `log10` do | bug? | source |
| 8 | `DC` | input read once at construction | convention | source |
| 9 | `Pitch` | no lock on a Karplus-Strong pluck at any reasonable setting | limitation | measured |
| 10 | `UnaryOpUGen` (transcendental) | ar and kr run different maths: nova-simd vs C library | undocumented | measured, source |
| 11 | `scaleneg` (sclang, demand rate) | returns −a·b for a < 0 instead of a·b | bug? | measured |
| 12 | `UnaryOpUGen` `reciprocal` | 1/0 is NaN, not inf, at both rates | undocumented | measured, source |
| 13 | `K2A` (first block) | ramps from the kr source's constructor output | convention | measured |
| 14 | scsynth NRT | occasional abort (exit 134) on a render that succeeds when rerun | bug? | measured, not reproduced |
| 15 | `APF` | not an allpass: +28 dB at its frequency, +38 dB at 100 Hz (indexing errors in the unrolled loop) | bug? | measured, source |
| 17 | `AllpassC` (start-up) | outputs 0 for the first delay length; AllpassN/L output -fb * in there | bug? | measured, source |
| 16 | `Ramp` | reads the input one sample past the segment; past the buffer end at a block boundary | bug? | source |

## 1. `Amplitude.kr` with an audio-rate input releases 64× too fast

`Amplitude.kr(SoundIn.ar(0), 0.01, 0.1)` reaches 0.136 of a unit step 64 samples
after the step ends; `Amplitude.ar` with the same arguments reaches 0.1 after 0.1 s.
The constructor computes coefficients with `SAMPLERATE`, which for a kr unit is the
control rate; `Amplitude_next_atok` then iterates over the full audio block
(`FULLBUFLENGTH`). The effective times are the stated ones divided by the block size.
With a kr input (`Amplitude_next`, one sample per block) the times are correct.

- Source: `server/plugins/FilterUGens.cpp:3495` (coefficients), `:3521` (`Amplitude_next_atok`).
- Translation: reproduced (`sc.amplitude_kr`); `tests/cases/case_Amplitude.scd`, channel 1.

```supercollider
// Step input; compare ch 0 and 1 around 0.5 s.
{ var step = Line.ar(1, 1, 0.5) * (Sweep.ar < 0.5);
  [Amplitude.ar(step, 0.01, 0.1), K2A.ar(Amplitude.kr(step, 0.01, 0.1))] }
```

## 2. `Saw` is a falling ramp at half level

Against Faust's rising ±1 `os.sawtooth`, every harmonic of `Saw.ar(220)` is exactly
6.0 dB lower and the slope is negative. Help says nothing about polarity or level.

- Translation: `-0.5 * os.sawtooth(freq)`; `tests/cases/case_Saw.scd`.

## 3. Constructors compute one sample before the first block

Most UGens call their calc function with one sample in the constructor, then process
the first block from sample 0 again: for stateful UGens the first input sample enters
the state twice. On `MoogFF` with noise starting at full level this caused a 1e-3
relative error over the first 0.25 s, gone once the input starts with silence.

- Source: e.g. `server/plugins/FilterUGens.cpp:4073` (`MoogFF_next(unit, 1)`).
- Test policy: all test signals start with 100 ms of silence (`signals/make_signals.py`).

## 4. `rrand` on signals draws from −1..1

`rrand_aa` computes `xa + frand2() * (xb - xa)`; `frand2` returns −1..1, so for
`a < b` the output covers [2a − b, b) instead of [a, b). The control-rate version
`rrand_1` uses `frand()` and is correct, so the same expression has two ranges
depending on rate.

- Source: `server/plugins/BinaryOpUGens.cpp:3381` (`rrand_aa`; also `_ak`, `_ka`, ...), `:1428` (`rrand_1`).
- Translation: reproduced (`sc.rrand`).

## 5. `unsignedRightShift` and `fill` compute `a + b`

Neither has a case in `ChooseNormalFunc`; the `default:` branch selects `add_aa`.

- Source: `server/plugins/BinaryOpUGens.cpp:5134`.
- Translation: mapped to `+`, faithfully.

## 6. `asInteger` / `asFloat` on signals pass through

No case in the unary dispatch; the default is `thru_a`. `asInteger` does not truncate
on the server.

- Source: `server/plugins/UnaryOpUGens.cpp:644`.

## 7. `log2`: float and double disagree on negative input

`sc_log2(float32)` is `std::log2(x)` (NaN for x < 0); `sc_log2(float64)` is
`std::log2(std::abs(x))`; `sc_log10` takes `abs` in both. scsynth runs the float version.

- Source: `include/plugin_interface/SC_InlineUnaryOp.h:73`, `:317`, `:75`.

## 8. `DC` reads its input once

The constructor stores `in0(0)`; a signal connected to `DC` is frozen at its first value.

- Source: `server/plugins/LFUGens.cpp:1303`.
- Translation: `DC` requires a constant input (`constant_inputs`), else a hard error.

## 9. `Pitch` does not track a Karplus-Strong pluck

On Karplus-Strong plucks (B0–C3, noise excitation) `Pitch` stays unvoiced at `initFreq`
with the default `peakThreshold` 0.5, also at 0.3 and with `clar`; at 0.1 it voices with
wrong pitches. Clean sines and saws, and an additive pluck, track correctly.
Probably the autocorrelation peak of a KS tone stays under threshold.

- Test policy: `bass_di` is an additive pluck (`signals/make_signals.py`).

## 10. Audio-rate and control-rate operators run different maths

`ChooseOperatorFunc` picks the C-library functions for kr units (block length 1) and
nova-simd's vectorised approximations for ar units (block length a multiple of 16).
They agree to ~1e-7 in the normal domain but not at the edges (all values measured on
scsynth; −0.0 on the `bass_di` zero crossings):

| Input | ar (nova-simd) | kr (C library) |
| --- | --- | --- |
| `log(0)` | −88.03 | −inf |
| `log(-0.0)` (sign bit set) | −487.63 | −inf |
| `log(-0.5)` | −400.29 (bits of the sign read as mantissa) | NaN |
| `asin(1.5)`, `acos(1.5)` | 0 | NaN |
| `exp(100)` | 3.4e38 (FLT_MAX) | inf |
| `ampdb(-0.5)` | −6.02 (abs taken) | NaN |
| `log10(-0.5)` | −173.84 (no abs) | −0.30 (abs taken) |

The same SynthDef can therefore output NaN at kr and a finite value at ar, or the reverse.
The translator follows both: `sc.n*` ports of nova-simd for ar, the C library for kr.

- Source: `server/plugins/UnaryOpUGens.cpp:1313` (`ChooseOperatorFunc`);
  `external_libraries/nova-simd/detail/vec_math.hpp` (`vec_log_float`, `vec_exp_float`,
  `vec_asin_float`, ...); `simd_unit_conversion.hpp` (`amp2db` takes `fabs`).
- Regression: `tests/cases/case_ops.scd`, `case_UnaryOp_<op>` and `case_UnaryOp_<op>_kr`.

## 11. `scaleneg` in sclang computes −a·b for negative a

The help says "a*b when a < 0, otherwise a". `(-2.0).scaleneg(0.5)` returns `1.0`.
The float and double specialisations of `sc_scaleneg` compute `(|a| − a)(b/2 + 1/2) + a`,
which is −a·b for a < 0. The server's ar and kr operators use the plain formula and give
−1.0; only sclang and demand-rate `BinaryOpUGen` use the specialisation.

- Source: `include/plugin_interface/SC_InlineBinaryOp.h:561`, `:570`;
  callers `lang/LangSource/PyrMathOps.cpp:1678`, `server/plugins/BinaryOpUGens.cpp:836`.

```supercollider
[(-2.0).scaleneg(0.5), (-2).scaleneg(0.5)]  // -> [1.0, 1.0]; documented: -1.0
```

## 12. `reciprocal` of 0 is NaN

Both rates compute 1/x with a reciprocal estimate plus one Newton–Raphson step; at 0
the estimate is inf and the step multiplies inf by 0, so the result is NaN, not inf.

- Source: `include/plugin_interface/SC_InlineUnaryOp.h:238` (kr), nova-simd
  `vec_reciprocal_newton` (ar).

## 13. `K2A`'s first block ramps from the constructor output

`K2A` (and an audio-rate `BinaryOpUGen` with a kr input) initialises its previous value
from what the kr source wrote during construction. Sources whose constructor sample
differs from their first block (the LF oscillators, which advance their phase in the
constructor) give a ramp across the first block: `K2A.ar(LFSaw.kr(3, -0.5))` starts at
−0.5 and reaches the block-0 value at sample 63. The port starts at the block-0 value.

- Test policy: comparisons skip the first 64 samples (`tests/compare.py`, `SKIP`).

## 14. scsynth NRT occasionally aborts

Twice in a few thousand renders, `scsynth -N` exited with status 134 (SIGABRT) on a
control-rate operator case (`case_BinaryOp_amclip_kr` on `impulse`, and one in the
first operator batch); rerunning the identical command succeeded. Not reproduced on
demand; possibly timing- or memory-dependent.

- Test policy: `translator/batch.scd` retries a failed render once and logs it.
- To do: catch a core dump (`ulimit -c`) next time it happens.

## 15. `APF`'s unrolled loop indexes the wrong past output

`APF_next` processes 3 samples per loop iteration with rotating variables. The b2 term of
the second sample uses `y2` before it is reassigned (y[n-3] where the recursion needs
y[n-2]), and the third sample uses the just-computed `y2` (y[n-1]). Only the first sample of
each group, and the 64th sample of a block (`mFilterRemain`), compute the documented
allpass `y = x + b1 (y1 - x1) + b2 (y2 - x2)`.

```cpp
// server/plugins/FilterUGens.cpp, APF_next (both branches)
x0 = ZXP(in); ZXP(out) = y0 = x0 + b1 * (y1 - x1) + b2 * (y2 - x2);
x2 = ZXP(in); ZXP(out) = y2 = x2 + b1 * (y0 - x0) + b2 * (y2 - x1);   // should be (y1 - x1)
x1 = ZXP(in); ZXP(out) = y1 = x1 + b1 * (y2 - x2) + b2 * (y2 - x0);   // should be (y0 - x0)
```

Moreover the per-sample formula itself, `y = x + b1 (y1 - x1) + b2 (y2 - x2)`, has the
same numerator and denominator, `(1 - b1 z^-1 - b2 z^-2) / (1 - b1 z^-1 - b2 z^-2)`: as
written it is the identity, not an allpass. What `APF` outputs is therefore decided by the
indexing errors. Measured magnitude response of `APF.ar(impulse, 1000, 0.95)` (NRT,
8192-point FFT of the impulse response):

| Frequency | 100 Hz | 300 Hz | 1 kHz | 2 kHz | 5 kHz | 12 kHz |
| --- | --- | --- | --- | --- | --- | --- |
| Gain | +37.8 dB | +35.6 dB | +27.9 dB | +21.8 dB | +11.1 dB | +4.9 dB |

- Translation: reproduced sample for sample (`sc.apf`, `case_APF` within 1.3e-5).


## 16. `Ramp` reads past its input buffer

`Ramp_next` advances the input pointer by the samples just output, then reads `*in` to set
the next slope. When a segment ends at the end of the block, that is `in[inNumSamples]`,
one past the buffer; with a control-rate input (a one-sample buffer) every read past the
first is out of bounds. The value read is whatever lies in adjacent memory.

```cpp
// server/plugins/FilterUGens.cpp, Ramp_next
LOOP(nsmps, ZXP(out) = level; level += slope;);
in += nsmps;
...
if (counter <= 0) { ...; slope = (*in - level) / counter; }
```

- Translation: `Ramp` not mapped until measured.

## 17. `AllpassC` drops its direct path at start-up

While the delay line is not yet filled (`AllpassC_helper<true>`, the "checked" variant),
a sample whose newest read index is negative outputs `0`. The allpass output there is
`value - feedbk * dwr` with `value = 0`, i.e. `-feedbk * in`, which is what `AllpassN` and
`AllpassL` output in the same situation. So for the first delay-length of samples
`AllpassC` lacks the `-feedbk * in` term. Seen with a 0.2 s delay on signals that start
within the first 0.2 s (error 1.2e-2 against a zero-buffer allpass; exact once reproduced).

- Source: `server/plugins/DelayUGens.cpp`, `AllpassC_helper<true>` (`if (irdphase0 < 0) { ...; ZXP(out) = 0.f; }`)
  vs `AllpassL_helper<true>` (`ZXP(out) = -feedbk * zin;`).
- Translation: reproduced (`sc.allpassx`).
