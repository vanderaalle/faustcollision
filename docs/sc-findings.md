# scsynth behaviour found while translating

Behaviour of scsynth (SuperCollider 3.13.0) that the documentation does not state,
found by comparing renders sample by sample or by porting the C++. Source references
are to the `Version-3.13.0` tag (`~/src/supercollider`).

Issue drafts for #4, #5, #11, #15, #17-#28, #30-#33: `docs/issues/`.

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
| 16 | `Ramp` | reads the input one sample past the segment; past the buffer end at a block boundary | bug? | measured, source |
| 17 | `AllpassC` (start-up) | outputs 0 for the first delay length; AllpassN/L output -fb * in there | bug? | measured, source |
| 18 | `EnvGen` (audio-rate gate) | forced release (gate <= -1) during a segment corrupts the new segment and shortens it | bug? | measured, source |
| 19 | `LocalIn` (server's first block) | outputs its uninitialised bus instead of the default when the synth starts at block 0 (e.g. NRT time 0) | bug? | measured, source |
| 20 | `Formant` | phase sync product `phase1 * freq2` overflows int32: formant and bandwidth phases restart near 0 instead of at the fundamental's fraction | bug? | measured, source |
| 21 | `Vibrato.ar`, `Wrap.ar`, `Fold.ar`, `Clip.ar`, `InRange.ar`, `ToggleFF.ar`, `PulseDivider.ar`, `MantissaMask.ar`, `TRand.ar`, `TIRand.ar`, `TExpRand.ar`, `CoinGate.ar`, `Ball.ar`, `Spring.ar`, `Hilbert.ar` (constant or kr input) | read the input as an audio buffer: past the single value of a constant or control wire (garbage, NaN); defaults like `Vibrato.ar(440)` are affected | bug | measured, source |
| 22 | `LinExp.ar` (one bound of a range at audio rate) | the calc function reads both bounds per sample when either is audio rate: the other is read past its value (NaN, inf) | bug | measured, source |
| 23 | `PeakFollower` (changing decay) | the decay ramp starts at the new value and moves past it, only on decaying samples; the overshoot is stored, so the decay keeps oscillating around the target | bug? | measured, source |
| 24 | BEQSuite (`BLowPass` ... `BHiShelf`, every coefficient input at audio rate) | inputs read once per 3 samples from the block's first 21 (BBandPass, BBandStop, BHiShelf: a second read per change, so every other sample) | bug? | measured, source |
| 25 | `Saw.kr`, `Pulse.kr`, `Blip.kr` | inf/NaN above 375 Hz (harmonic count 0 at the control rate) | bug? | measured, source |
| 26 | `VarLag.ar` (`warp: \lin`) | a time change after the ramp ended adds one stale slope step | bug? | measured, source |
| 27 | `IEnvGen` | curvatures truncated to integers | bug? | measured, source |
| 28 | `Resonz.kr`, `Ringz.kr`, `TwoPole.kr`, `TwoZero.kr`, `APF.kr`, `MidEQ.kr`, `OneZero.kr` | coefficient changes apply one block late; `APF.kr` passes its input through | undocumented | measured, source |
| 29 | `SubsampleOffset` | 0.5, not 0, for a synth scheduled exactly on a sample; 0 for an untimestamped command | convention | measured, source |
| 30 | `Lag3UD` | the third stage picks its up/down time by comparing stages 1 and 2, not its own input and state | bug? | measured, source |
| 31 | `TWindex` (normalize 0, weights summing below 1) | returns n + 2 (outside the array) for the missing probability | undocumented | measured, source |
| 32 | `FreqShift` (constant or kr phase) | the phase argument is ignored: the constructor multiplies it by `m_radtoinc` before setting it | bug? | measured, source |
| 33 | `Gendy1/2/3.kr` (default arguments) | output far outside ±1 (up to ~1e5): the phase drops by 1 at most per step while a kr step covers several breakpoints | bug? | measured, source |

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

Measured (NRT, `Ramp.ar(LFNoise1.ar(300), 21.5 / 48000)`: 21-sample segments, the first one
1 sample long, so one segment in 64 ends on a block boundary): the value each segment
ramps to, inferred from its slope, equals the input sample at the segment start for all
4499 segments that start inside a block, and differs (up to 0.84) for all 71 that start
at a block boundary.

- Translation: `Ramp` not mapped yet; the boundary read cannot be reproduced (it is
  whatever follows the input buffer). A port would read the next block's first sample,
  and document the difference.

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

## 18. `EnvGen` with an audio-rate gate: forced release corrupts the release segment

With an audio-rate gate, `EnvGen_next_aa` checks the gate inside the running segment's
sample loop (`EnvGen_perform`, which keeps that shape's state in local variables). A gate
of -1 or below forces the last stage: `check_gate` calls `EnvGen_initSegment` right there,
setting the new segment's `m_b1`, `m_y1`, `m_y2`, `m_counter`. The loop then breaks and
writes its stale locals back (`unit->m_b1 = b1` for a curve segment, `m_y1`/`m_y2` for
sine/welch/squared/cubed), overwriting the new segment's state. Also, `check_gate` adds the
in-loop offset to the counter but `EnvGen_initSegment` recomputes the counter without it,
and the caller then subtracts the offset: the release is shortened by the samples already
run in that loop.

Measured: `EnvGen.ar(Env.perc(0.01, 0.3), SoundIn.ar(0))` on white noise; the gate dips to
-1.012, the envelope (near 1.0) jumps to -0.0187 instead of starting a 12 ms curve to 0.
The port reproduces both effects for curve -> curve (scsynth's `Env.perc`/`adsr` shapes)
within 2.7e-7; other shape pairs are not reproduced.

- Source: `server/plugins/LFUGens.cpp` `check_gate` (forced branch), `EnvGen_perform`
  (write-back after the loop), `EnvGen_next_aa`.

## 19. `LocalIn` ignores its default in the server's first block

`LocalIn` outputs its bus when a `LocalOut` touched it in this block or the previous one
(`diff = mBufCounter - touched`, 0 or 1), otherwise its `default` input. The constructor
sets `touched = -1`, so a synth whose first block is `mBufCounter == 0` (the server's very
first block, e.g. an NRT score with `/s_new` at time 0) gets `diff == 1`: it copies the bus,
which nothing has written: `RTAlloc`ed memory, not cleared. The default is never output.
In a running server (or from block 1 on in NRT) `diff >= 2` and the default is used, as
documented. Both the audio and the control-rate `LocalIn` are affected.

Measured: `LocalIn.ar(3, [0.5, 0.1, -0.2])` and `LocalIn.kr(1, 0.1)` in an NRT render with
`/s_new` at time 0 output 0 in the first block (the fresh memory happened to be zero);
started in block 1, they output the defaults. A server that reuses that memory would
output stale data. FaustCollision ports the documented behaviour; its NRT reference for
`case_LocalIn` starts the synth in block 1 (`startBlock` metadata in `translator/batch.scd`).

Also: a second `LocalIn` of the same rate in a SynthDef outputs zeros (`ClearUnitOutputs`),
and a `LocalOut` whose channel count differs from the `LocalIn`'s is silently ignored; the
translator rejects both.

- Source: `server/plugins/IOUGens.cpp` `LocalIn_Ctor`, `LocalIn_next_a`, `LocalOut_next_a`;
  `server/scsynth/SC_World.cpp` (NRT loop: `mBufCounter` starts at 0; commands run up to the
  end of the current block).

## 20. `Formant`: the phase sync overflows int32

When the fundamental's phase passes a cycle, `Formant_next` restarts the formant and
bandwidth phases in proportion to the fundamental's overshoot:

    phase1 -= onecyc13;
    phase2 = phase1 * freq2 / freq1;
    phase3 = phase1 * freq3 / freq1;

All are `int32`. `phase1` (the overshoot, up to `freq1`) times `freq2` is of the order of
`freq1 * freq2`, e.g. 4.5e6 * 2e7 for 440/1760 Hz: far beyond 2^31. The product wraps (the
overflow is undefined behaviour in C++; x86-64 code wraps), and the division gives a
small, essentially arbitrary value: the phases restart near 0 instead of at
`phase1 * freq2 / freq1`, a fraction of a sample's increment. The intended restart is
sub-sample accurate; the actual one jitters by up to one sample of the formant phase.

Measured: `Formant.ar` (440, 1760, 880): at the first restart the overshoot is 4473848;
intended `phase2` 17895393 (3.3% of a cycle), actual 118. A port wrapping the product in
int32 is bit-exact against scsynth on all test signals; the same simulation with 64-bit
products differs on half the samples of the first second (14.6% relative RMS). A wrapped
product can also be exactly -2^31.

- Source: `server/plugins/OscUGens.cpp` `Formant_next`. Fix: compute the products in
  int64 (or as `(int32)((double)phase1 * freq2 / freq1)`).

## 21. Audio-rate UGens read a constant or control-rate input as an audio buffer

`Vibrato_next` reads its input with `float* in = ZIN(0)` and `ZXP(in)` for every sample of
the block, at any input rate. A constant or control-rate wire holds one value: the other 63
reads go past it, into whatever follows in memory. `Vibrato` has no `checkInputs`, and the
class's own defaults (`Vibrato.ar(freq: 440.0)`) take this path; the help file's examples
use `DC.ar(400)`.

Measured (NRT, depth 0, so the output should equal the input): `Vibrato.ar(0.5, 6, 0, 0,
0, 0, 0)` outputs 0.5 on the first sample of each block and 0, tiny values and NaN on the
others; with `LFNoise0.kr` as input, likewise; with `DC.ar(0.5)`, 0.5 throughout. The
garbage depends on the memory layout, so it differs between servers and runs.

The same holds for `Wrap`, `Fold`, `Clip` and `InRange` (`Trig.sc`: `InRange` and its
subclasses have no `checkInputs` either; their calc functions read `in` with `ZXP`).
Measured (NRT, input 0.3, range 0..1): `Wrap.ar(0.3, 0, 1)`, `Fold.ar`, `Clip.ar` output
0.3 on each block's first sample and then denormals, zeros and NaN (30300 NaN samples in
10 s for Wrap and Fold); `InRange.ar` flips between 0 and 1; `Wrap.ar(LFNoise0.kr(..))`
likewise; `Wrap.ar(DC.ar(0.3), 0, 1)` is correct. `ToggleFF.ar` and `PulseDivider.ar`
(no `checkInputs`) with `Impulse.kr(5)` as trigger read past it too: `PulseDivider.ar(k, 2)`
outputs 22750 ones in 10 s instead of 25 (with `T2A.ar(k)`: 25). `MantissaMask.ar(0.3, 3)` (no `checkInputs` either) is
0.28125 on each block's first sample only (1501 of 96064 samples), garbage elsewhere
(1501 non-finite, values up to -1.7e38); with `DC.ar(0.3)` it is right throughout. `TRand.ar`, `TIRand.ar`,
`TExpRand.ar` and `CoinGate.ar` with `Impulse.kr(10)` as trigger (10 s): 22502, 29803 and
30100 value changes, and 22502 nonzero samples, instead of 100 (with `T2A.ar(k)`: 100).
Their constructors pick the calc function by the unit's rate (TRand* also by `lo`'s), and
the `.ar` ones read the trigger with `ZXP` per sample; no `checkInputs`. `Ball.ar`,
`Spring.ar` and `Hilbert.ar` (no `checkInputs`, `in` read with `ZXP`) with
`LFNoise0.kr(20) * 0.5` as input (2 s): Ball's output reaches 3.7e25, Spring is NaN on
96056 of 96064 samples, Hilbert on 84056; with the same signal through `K2A.ar` all three
are finite. (`TBall.ar` differed from the `K2A` version on 21 samples by at most 0.02,
consistent with K2A's ramp: not shown to be affected.) LinExp, TDelay,
SetResetFF, PulseCount, Stepper, Timer and ZeroCrossing are protected: sclang rejects a
non-audio first input ("first input is not audio rate").

- Source: `server/plugins/LFUGens.cpp` `Vibrato_next`, `Wrap_next_*`, `Fold_next_*`,
  `Clip_next_*`, `InRange_next` (`ZIN(0)`/`ZXP(in)`); `NoiseUGens.cpp` `MantissaMask_next`, `TRand_next_a(a)`, `TIRand_next_a(a)`, `TExpRand_next_a(a)`, `CoinGate_next`; `PhysicalModelingUGens.cpp` `Ball_next`, `Spring_next`; `FilterUGens.cpp` `Hilbert_next`;
  `Osc.sc` `Vibrato`, `Trig.sc` `InRange`, `Noise.sc` `MantissaMask`. Fix: `checkInputs { ^this.checkSameRateAsFirstInput }`-style checks requiring
  an audio-rate input for `.ar` (or calc functions reading `ZIN0(0)` otherwise).

## 22. `LinExp.ar` with one audio-rate bound reads the other past its value

`LinExp_SetCalc` picks the per-sample calc functions when *either* bound of a range is
audio rate (`INRATE(1) == calc_FullRate || INRATE(2) == calc_FullRate`, likewise for
dstlo/dsthi), and those (`LinExp_next_aa`, `_ak`, `_ka`) then read *both* bounds with
`ZXP`. A constant or control-rate partner is read past its single value. Unlike finding
21 this is not about the input: `LinExp` checks `checkSameRateAsFirstInput`.

Measured (NRT, in = `DC.ar(0.5)`, 10 s): `LinExp.ar(in, 0, SinOsc.ar(1).range(0.9, 1.1),
1, 10)` outputs NaN on 15150 samples; `LinExp.ar(in, 0, 1, 1, SinOsc.ar(1).range(9, 11))`
on 371175 (and inf on 15150); with both bounds of the pair at audio rate (`DC.ar(0)`,
`DC.ar(1)`) the output is correct.

- Source: `server/plugins/LFUGens.cpp` `LinExp_SetCalc`, `LinExp_next_aa/_ak/_ka`. Fix:
  read a bound per sample only when it is audio rate (or select on `&&` and add mixed
  calc functions).

## 23. `PeakFollower`: the decay ramp starts at the target and overshoots

When `decay` changes, `PeakFollower_next` computes `decay_slope = CALCSLOPE(decay,
unit->mDecay)` but ramps a local variable initialised to the *new* value (`float decay =
ZIN0(1)`), not the old one, adding the slope only on samples where the level decays. At the
end of the block the overshot value is stored as `mDecay`. The next block sees `decay !=
mDecay` again and ramps from the target by `(target - overshoot) / 64`, the other way: with
a steadily decaying input (64 decaying samples per block) the stored value alternates
between target + e and target - e indefinitely instead of settling. The sign-dependent
formulas are also chosen from the new and the stored (overshot) values.

Measured: a float simulation of this logic is bit-exact against scsynth over 10 s of
`PeakFollower.ar(SoundIn, Line.kr(0.99, 0.9999, 6))` on bass_di (0 of 484800 samples
differ); the FaustCollision port reproduces it.

- Source: `server/plugins/TriggerUGens.cpp` `PeakFollower_next`. Fix: ramp from
  `unit->mDecay` (`float decay = unit->mDecay;`) and store the target at the block end.

## 24. BEQSuite with audio-rate inputs reads them once per 3 samples, from the block's start

With every coefficient input at audio rate (`next_aa` / `next_aaa`), the BEQSuite filters
(`BLowPass`, `BHiPass`, `BAllPass`, `BBandPass`, `BBandStop`, `BPeakEQ`, `BLowShelf`,
`BHiShelf`) read `freq`, `rq`/`bw`/`rs` and `db` once per 3-sample group
(`mFilterLoops`), with `ZXP`: group g reads the block's sample g, not sample 3g. The 21
groups use the first 21 samples of the block; the rest of the block's modulation is never
read. The coefficients are recomputed when the read values differ from the stored ones
(no ramp); the 64th sample keeps group 20's.

`BBandPass`, `BBandStop` and `BHiShelf` store the compared value with another `ZXP`
(`unit->m_freq = ZXP(freq)`) inside the change branch, so each change advances the read
pointer by 2: while the input keeps changing they read samples 0, 2, 4 ... 40, and the
stored value is the sample after the one used. At the block end the stored value is the
next unread sample (`BLowPass`, `BAllPass`, `BPeakEQ`, `BLowShelf`, `BHiShelf`) or the last
one read (`BHiPass`: no store; `BBandPass`, `BBandStop`: `nextfreq`).

Measured (NRT, 2 s, white noise through each filter; inputs stepped with `LFNoise0.ar`
and continuous with `SinOsc.ar`): a double-precision simulation of these rules is
bit-exact against scsynth for all eight classes and both input kinds from block 10 on
(blocks 1-4 differ by the start-up transient of constructor-time input values). A model
reading the group's own sample (3g) differs on 99% of samples; swapping the extra-read
rule between classes differs on 28-41% of samples. The block-end rule did not change the
output on these signals (it matters only when a block's first value equals one candidate
stored value but not the other); the port follows the source.

- Source: `server/plugins/FilterUGens.cpp` `BLowPass_next_aa` ... `BHiShelf_next_aaa`.
- Translation: `sc.beq_a` (per-class flags), within the float-coefficient floor of next_kk.

## 25. `Saw.kr`, `Pulse.kr`, `Blip.kr` output inf/NaN above 375 Hz

The band-limited oscillators compute the harmonic count N = (int32)((SAMPLERATE * 0.5) /
freq). At control rate SAMPLERATE is SR / 64 (750 Hz at 48 kHz), so any frequency above
375 Hz gives N = 0 and `scale = 0.5 / N` = inf. `Saw` and `Pulse` never clamp N; `Blip`
clamps it to 1 only when `numharm` is below the maximum, not in the `N > maxN` branch
that sets N = maxN = 0. The same happens at audio rate above SR / 2, where it does not
matter.

Measured (NRT, `Line.kr(300, 450, 2)` as frequency, through `K2A`): from 375.1 Hz on,
every block of `Saw.kr`, `Pulse.kr` and `Blip.kr(f, 200)` is non-finite (750 of 1501
blocks); below it the output is finite.

- Source: `server/plugins/OscUGens.cpp` `Saw_next`, `Pulse_next`, `Blip_next` (the
  maxN branch). Fix: clamp N to at least 1 in every branch (or output 0 when the
  frequency exceeds the rate's Nyquist).

## 26. `VarLag.ar`: a time change after the ramp has ended adds one stale step

When `time` changes while the input is unchanged, `VarLag_next` rescales the ramp:
`counter = max(1, (int)(counter * time / oldTime))`, `slope /= scaleFactor`. It does so
even when the ramp has already ended (counter 0): the counter becomes 1, and the next
sample adds the old slope once more to the level that already equals the target; the
sample after snaps back to the target (`level = m_in`). `VarLag_next_1` (control rate)
checks `counter != 0` and is not affected.

Measured (NRT): `VarLag.ar` with `warp: \lin`, a step 0 -> 1 ramped over 0.02 s, then
`time` changed from 0.02 to 0.03 s after the ramp: one sample reads 1.0006951 = (1/960) /
1.5, the old per-sample slope over the time ratio.

Only `warp: \lin` creates the VarLag UGen; other warps (including the default) build an
EnvGen (`Filter.sc`, `VarLag.new1`).

- Source: `server/plugins/FilterUGens.cpp` `VarLag_next` (the `else` branch), vs
  `VarLag_next_1`. Fix: rescale only while `counter > 0`.

## 27. `IEnvGen` truncates curvatures to integers

`GET_ENV_VAL` reads the curve as `int curve = (int)unit->m_envvals[...]` before
`exp((float)curve)`: a fractional curvature is truncated toward zero, and any curvature
with |c| < 1 becomes linear. `EnvGen` uses the float value.

Measured (NRT, index `Line.ar(0, 1, 1)`): `IEnvGen.ar(Env([0, 1], [1], -4.5), idx)`
matches the curve -4 formula within 1.5e-7 (and differs from -4.5 by 3.9e-2);
`Env([0, 1], [1], 0.7)` is linear within 3e-8.

- Source: `server/plugins/LFUGens.cpp` `GET_ENV_VAL` (shape_Curve) and its callers
  `IEnvGen_Ctor`, `IEnvGen_next_a`, `IEnvGen_next_k`. Fix: `float curve`.

## 28. Control-rate filters without a `_next_1` apply coefficient changes one block late; `APF.kr` passes its input through

At control rate the buffer length is 1, so `mFilterLoops` = 0, `mFilterRemain` = 1 and
`mFilterSlope` = 0 (`server/scsynth/SC_Rate.cpp:34-40`). Filters whose `.kr` runs the
unrolled audio-rate function (`Resonz`, `Ringz`, `TwoPole`, `TwoZero`, `APF`, `MidEQ`,
`OneZero`) compute the new coefficients when an input changes, but the ramp slopes are
`(next - current) * 0`: the block's single sample uses the old coefficients, and the new
ones are stored for the next block. `LPF`, `HPF`, `RLPF`, `RHPF`, `BPF`, `BRF`, `Formlet`
and `LeakDC` have a `_next_1` that uses the new coefficients at once.

`APF.kr` runs only the remainder loop, whose per-sample formula is the identity (finding
15): from zero state it outputs its input exactly.

Measured (NRT, input `LFNoise0.kr(200)`, frequency stepping 30 -> 70 Hz): a double
simulation of `Resonz.kr` applying new coefficients one block late is bit-exact (0 of 748
blocks differ); applying them immediately differs on 121 blocks by up to 0.94.
`APF.kr(x, 50, 0.9)` equals `x` on every block. `Ringz.kr`, `TwoPole.kr`, `TwoZero.kr`,
`MidEQ.kr` likewise bit-exact one block late (TwoPole/TwoZero with `reson * reson` as a
float product). `OneZero.kr` is late for another reason: `OneZero_next` adds its
CALCSLOPE step after the sample (slope factor 1 at control rate), also bit-exact.

- Kind: undocumented (Resonz ... OneZero); bug? (APF.kr, a consequence of finding 15).

## 29. `SubsampleOffset` is 0.5 for a synth scheduled exactly on a sample

For timestamped commands the scheduler computes `diffTime = (schedTime - oscTime) *
oscToSamples + 0.5`, takes `mSampleOffset = floor(diffTime)` and `mSubsampleOffset =
diffTime - floor(diffTime)`: the start sample is rounded to the nearest, and a start
exactly on a sample boundary reports 0.5. Commands without a timestamp set 0. The help
describes it only as the offset from the synth start within one sample.

Measured: `SubsampleOffset.ir` in an NRT score with `/s_new` at time 0 is 0.5.

- Source: `server/scsynth/SC_World.cpp:691` (NRT), `SC_Jack.cpp:453-465`, `SC_PortAudio.cpp`,
  `SC_CoreAudio.cpp` (real time: same formula; 0 when nothing is scheduled).
- Translation: 0.5 (the scheduled value, as in the NRT references).

## 30. `Lag3UD`'s third stage tests the wrong stages

Each stage of `Lag2UD`/`Lag3UD` uses the up time when its input is above its state, else the
down time. In `Lag3UD_next` the third stage tests `y1a > y1b` (stage 1 against stage 2,
both just updated) instead of `y1b > y1c` (its own input against its state), in both the
fixed- and the changing-time loops; `Lag2UD` is right.

Measured (NRT, `Lag3UD.ar(LFPulse.ar(7, 0, 0.3) + (LFNoise0.ar(40) * 0.3), 0.005, 0.08)`,
2 s): a double simulation with the C's test is bit-exact (0 differing samples from block
10 on); with the intended test it differs on 45813 samples, by up to 0.2.

- Source: `server/plugins/FilterUGens.cpp` `Lag3UD_next` (`if (y1a > y1b) { y1c = y1b + b1u
  * (y1c - y1b); }`). Fix: `if (y1b > y1c)`.
- Translation: reproduced (`sc.lag3ud`).

## 31. `TWindex` returns n + 2 when the weights sum to less than 1

With `normalize = 0`, a draw r = frand() in [0, 1) is compared with the running sum of the
weights; if no partial sum reaches r, `TWindex_chooseNewIndex` returns its initial value,
`mNumInputs`, which is n + 2 for n weights (the trigger and normalize inputs count): an
index outside the array, with the missing probability. The help says the weights
"should sum to 1.0" without stating this; `Select` would clip it to the last element.

Measured (NRT, `TWindex.ar(Impulse.ar(200), [0.2, 0.3, 0.3], 0)`, 10 s): indices 0, 1, 2
with 0.18 / 0.30 / 0.30 of the triggers, and index 5 with 0.22.

- Source: `server/plugins/OscUGens.cpp` `TWindex_chooseNewIndex` (`int32 index = maxindex;`).
- Translation: reproduced (`sc.twindex_clk`).

## 32. `FreqShift` ignores a constant or control-rate phase

With freq and phase both constant or control rate (`FreqShift_next_kk`), the constructor
sets the initial phase as `unit->m_phase = (int32)(unit->m_radtoinc * IN0(2))`, but
`m_radtoinc` is only assigned a few lines later: it is read uninitialised. Later blocks only
add the phase input's changes (a slope in the increment), never its value, so the absolute
phase offset comes from that one product. In NRT the fresh unit memory is 0 and the phase
argument has no effect; in a running server it is whatever the memory held. With an
audio-rate phase (`next_aa`, `next_ka`) the phase is added per sample, as documented.

Measured (NRT, `x = SinOsc.ar(440) * 0.5`): `FreqShift.ar(x, 100, 0.5)` is identical to
`FreqShift.ar(x, 100, 0)` (difference 0) and differs from `FreqShift.ar(x, 100,
DC.ar(0.5))` by up to 0.25; with phase 0 the constant and DC versions are identical.

- Source: `server/plugins/FilterUGens.cpp` `FreqShift_Ctor` (the kk branch assigns
  `m_phase` before `m_radtoinc = tableSizeSin * (rtwopi * 65536.)`). Fix: compute
  `m_radtoinc` first.
- Translation: reproduced as phase 0 (the NRT value).

## 33. `Gendy1/2/3.kr` with their default arguments leave ±1 by orders of magnitude

Gendy1/Gendy2 advance `phase += speed` with speed = (minfreq + (maxfreq - minfreq) * rate)
* sampleDur * num, and at a breakpoint only `phase -= 1.0` once. At kr (sampleDur =
1/750 at 48 kHz, 64-sample blocks) the defaults minfreq 20, maxfreq 1000 with num 12 give
speeds from 0.32 to 16 per step: phase climbs without bound and `(1 - phase) * amp +
phase * nextamp` extrapolates. Gendy3 steps at most one breakpoint region per sample; at
kr its default freq 440 moves the phase 0.59 per step across regions of ~1/12, so
`interp = (phase - lastphase) * interpmult` far exceeds 1. The same happens at audio rate
when maxfreq * num exceeds the sample rate (Gendy1/2), or for regions narrower than one
step (Gendy3, to a much smaller degree).

Measured (NRT, 10 s, `K2A.ar(Gendy1.kr)` etc.): max |x| 1.0e5 (Gendy1), 1.6e5 (Gendy2),
475 (Gendy3); `Gendy1.kr(minfreq: 1, maxfreq: 10)` stays within ±1.

- Source: `server/plugins/GendynUGens.cpp` `Gendy1_next_k`, `Gendy2_next_k` (`if (phase >=
  1.0) { phase -= 1.0; ...`), `Gendy3_next_k` (`if (phase >= nextphase) { ++index; ...`).
  Fix: loop the breakpoint step while phase >= 1 (Gendy3: while phase >= nextphase), or
  clamp speed below 1.
- Translation: reproduced.

