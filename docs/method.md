# Method

How FaustCollision ports SuperCollider UGens to Faust, and how it shows that each port
behaves like scsynth. The rules here are the project's working rules; the numbers are
those of the 3.13.0 port as of October 2026.

## 1. Principle: port the server, not the documentation

A SynthDef is a graph of UGens; scsynth runs it with each UGen's C++ calc function. The
translator maps every UGen to a Faust function in `translator/faust/sc.lib`, and that
function is written from scsynth's source (tag `Version-3.13.0`, with the nova-simd
submodule), not from the help files. Where the behaviour is not obvious, the port cites
the source file and line.

Three consequences follow.

- **What scsynth does is the specification**, including what it does differently from its
  documentation. Such differences are measured, recorded in `docs/sc-findings.md` and, by
  default, reproduced (section 6).
- **Nothing is translated by guesswork.** A UGen the table does not cover is a translation
  error naming the class. Inputs a port does not model are `require`d to have the one value
  it handles (for example `doneAction: 0`), and inputs scsynth reads only once, in the
  constructor, must be constants (`constant_inputs`). A refusal states its reason.
- **The mapping table is data.** `translator/mapping.toml` holds, per UGen: its inputs, the
  Faust template for each rate, the calc function scsynth would pick from the input rates
  (`template_by`), constructor-time constants computed in Python (`derive`), the comparison
  metric and the tolerance, and the regression case.

## 2. The execution model

A Faust program computes one sample at a time; scsynth computes blocks of 64 samples,
audio-rate (ar) UGens a block of samples, control-rate (kr) UGens one value per block.
The ports reproduce the block semantics explicitly:

- A kr UGen reads an audio input's **first sample of the current block** (`sc.a2k`). The
  few whose kr calc function consumes the whole audio block (Amplitude, Pitch) can only
  be known once the block has ended: the causal port holds them **one block late**
  (`sc.krhold`), a documented difference.
- kr values feeding audio-rate arithmetic are **ramped across the block** where scsynth
  ramps them (BinaryOpUGen, K2A: `sc.kr2ar`), held where it holds them.
- Most UGens compute **one sample in their constructor**, before the first block, and some
  advance their state doing so (a counter, a phase, a grain). Each port models its own
  constructor step.
- Inputs scsynth reads per block (`ZIN0`) are read per block in the port, inputs it reads
  per sample are read per sample, and the template is chosen by the same input rates that
  select scsynth's calc function.

Not modelled: the constructor-time value of an input. Where scsynth reads an input in
the constructor (an initial phase, the start of a ramp), the port uses that input's
first-block value. The two differ only when the input comes from a UGen whose
constructor sample differs from its first block (an LF oscillator, for instance).

## 3. Precision

The target is single-precision Faust with denormals flushed (`-single -ftz 2 -inpl`, the
flags of the Daisy embedded board). scsynth computes in float, but much of its state is
double. Rather than accept the difference, the ports reproduce it:

- **Double state as float pairs.** A double value is carried as a (high, low) pair of
  floats with error-free transformations (TwoSum, FMA-based products): phases,
  envelopes, filter states that scsynth keeps in double.
- **Evaluation order kept.** The Faust compiler normalises arithmetic, which would undo
  error-free transformations and reorder roundings. Additions, subtractions and products
  that must round as in C are written as opaque `fmaf` calls (`sc.fadd`, `sc.fsub`,
  `sc.fmul`).
- **Exact integer arithmetic** where scsynth uses it: 32-bit phase accumulators,
  `(int32)(float * double)` conversions computed exactly, counters.
- **Constants computed as scsynth computes them.** Constructor-time values are derived in
  Python with explicit float32 rounding (`translator/derive.py`), matching the C++
  expression by expression (including which of `cos` and `cosf` the C++ overload rules
  pick).

What remains is either exact or a measured floor with a known cause (section 4).

## 4. Verification

### References and signals

Every reference is rendered by scsynth itself, in non-real-time mode (NRT), at 48 kHz.
The test signals (`signals/make_signals.py`) are an impulse, an exponential sine sweep,
white noise, silence (10 s, for generators) and a synthetic plucked bass line. Each
starts with 100 ms of silence, so that the constructor sample does not meet a signal at
full level. A SynthDef with controls is rendered at the defaults and at each control's
minimum and maximum. scsynth's console output is checked: a synth that fails to build
(too few wire buffers, for instance) would otherwise render silence. The Faust code is
rendered from the same signals and settings through the C++ that `faust` generates for a
target (with the target's flags, compiled by g++ without fast-math); the control sweeps
of layer 3 use DawDreamer (libfaust's JIT), which can automate controls.

### Three layers

1. **Compile, I/O and controls:** every SynthDef translates, the Faust compiles, and its
   inputs, outputs and controls match the SynthDef.
2. **Fidelity:** each Faust render is compared with the scsynth render of the same signal
   and setting, using the metric and tolerance of the mapping entries involved (the
   loosest applies). The first block is skipped: it holds the constructor transient.
3. **Control sweeps (Faust only):** every control is swept from minimum to maximum and back
   over every signal, plus DC and full-scale inputs, followed by silence. The output must
   stay finite and must not get stuck in denormals (a CPU hazard on embedded targets).

### Metrics

| Metric | Measures | For |
| --- | --- | --- |
| waveform | RMS of the difference / RMS of the reference | sample-exact ports |
| envelope | mean dB difference of 10 ms RMS envelopes | detectors, followers |
| spectrum | mean dB difference of 1/3-octave STFT cells | phase-insensitive ports |
| statistics | mean dB difference of long-term 1/3-octave spectra, at least the level difference | random, chaotic and tracking UGens |
| distribution | Kolmogorov-Smirnov distance between sample-value distributions | values drawn once (Rand, IRand...), many instances cycled through one channel |

### Tolerances from measured floors

A tolerance is never chosen to make a test pass. It is the exact level (1e-6 for a
waveform), or, where a port cannot be exact, the **measured floor**, with its cause
stated in the mapping entry. Typical causes are a double computation that float pairs
approximate to ~1e-10, or a non-causal block computation.

For random and chaotic UGens, the port cannot reproduce scsynth's random generator, and
a chaotic map amplifies any rounding difference, so only distributions can agree. Their
floor is measured as **scsynth against itself**: the same SynthDef rendered with several
`RandSeed` seeds (or a chaotic map started from slightly perturbed values), the
tolerance being set above the largest score between those renders. A port that scores
within scsynth's own spread is indistinguishable from scsynth by this metric. Where the
float32 dynamics differ qualitatively from the double ones (the logistic map falls into
short cycles in float32), the map is ported in double precision (float pairs) instead.

### Coverage

- **Regression cases** (`tests/cases/`): every mapping entry has one, covering the calc
  functions scsynth selects by input rate (ar and kr, constant, control and audio
  inputs). The full suite runs before every merge (5190 results for 3.13.0).
- **Census** (`translator/census.py`, `report/census.md`): every core UGen class of the
  class library is classified as in scope or excluded (with the reason), and each in-scope
  class is probed at each of its rates with generic arguments: 470 probes, 446 passing.
  The census report explains each probe that does not pass. Most are probe artifacts:
  random UGens measured on few draws, or chaotic maps driven into degenerate regimes.
- **Corpus tests:** real SynthDefs translated in bulk (`translator.build --project DIR`),
  for example the examples of *Introduction to SuperCollider*: which translate, which
  are refused and why. Each refusal names either an exclusion by design or work to do.

## 5. Scope

Excluded by design, as they have no counterpart in a self-contained Faust program:
buffers, buses (other than the audio input and output), demand-rate UGens, FFT and phase
vocoders, server communication (SendReply, Poll), and the user interface (MouseX, KeyState
and similar); `translator/excluded.toml` lists them with the reason the translator gives.
A UGen that ends its node (PSinGrain) and `doneAction: 2` (free this synth: Line, XLine,
EnvGen) are translated as permanent silence of the whole program from the end of the block
in which scsynth frees the synth; the build prints a note. Other done actions act on other
nodes and are refused; Linen, DetectSilence and LFGauss still require `doneAction: 0`.
Ending the node is faithful, but on an always-running target such as an effects pedal it
means the program falls silent for good.

Controls: plain arguments become sliders (a spec is required); `t_` arguments
(TrigControl) output their value for one block when set, then 0; arguments with lag times
(LagControl) are lagged once per block. Audio-rate `a_` arguments are not supported.

Some ports carry resource limits where scsynth allocates dynamically: the grain UGens get
one Faust voice per possible grain, so `maxGrains` must be at most 65.

## 6. Findings

Porting at this level of detail surfaces behaviour of scsynth that its documentation does
not state, some of it probably unintended: buffer over-reads, filters reading inputs
from the wrong samples, random walks folded out of their range. The rules:

- **Measure before calling it a bug.** A finding is confirmed on scsynth NRT renders
  (status *measured*) and traced in the source (*source*); one only read in the source
  says so.
- **Reproduce by default.** The port follows scsynth, so that a translated SynthDef
  sounds like the original, bugs included. A deviation is recorded as such.
- **Report upstream.** Each likely bug has a draft issue in `docs/issues/`, with a
  reproducer, the measured result, the cause in the source and a suggested fix.

`docs/sc-findings.md` lists them (36 for 3.13.0). Pitfalls of Faust itself met along the
way (constant folding, compile-time expansion, rewritten arithmetic) are in
`docs/faust-notes.md`.

## 7. Known limits of the verification

- **Constructor-time inputs** are not modelled (section 2). Regression cases feed such
  inputs from constants or from UGens whose first block equals their constructor sample.
- **Denormals are flushed** in the port, as on the target, but not in scsynth. A state
  that scsynth keeps in the subnormal range is zero in the port. This only matters when an
  unstable system amplifies such tiny values (a Lorenz attractor driven out of its
  physical range).
- **Fidelity is measured on the C++ a target compiles,** generated by the `faust` on the PATH
  (2.70.3 here) and compiled on x86-64 with g++; layer 3 runs on DawDreamer's libfaust
  (2.85.9). Three Faust C++ issues are worked around in sc.lib (docs/faust-notes.md). A target
  compiler that contracts multiply-adds into FMA instructions (common on ARM) may round
  differently where the ports do not use opaque operations. The control sweeps of layer 3
  run on DawDreamer's JIT, whose `sqrt` is not correctly rounded; they only check that
  outputs stay finite and leave denormals.
- **The first block is skipped, but not its echo.** Where the constructor limitation makes
  the first block differ (a kr envelope ramped from its constructor value), a recursive
  effect after it (a reverb, a long delay) carries that block into later samples. Corpus
  tests show it; the regression cases avoid it.
- **Quantizers amplify rounding.** A `round`, a comparison or a trigger turns a last-bit
  difference near its threshold into an event one sample early or late (a pitch step in a
  Formant, observed on a corpus SynthDef); after it the outputs differ, as for chaotic maps.
  TrigControl's constructor value (0) is modelled for EnvGen's gate, the common
  `EnvGen.kr(env, t_trig)` idiom.
- **Controls are compared at their initial values.** The scsynth references set controls
  when the synth is created, so a lag's glide or a trigger set later is ported from the
  source but not compared with a render.
