# Faust notes: pitfalls met while generating Faust from SynthDefs

Things about Faust 2.70 (and DawDreamer's embedded libfaust) that matter when the goal
is sample-exact agreement with another implementation, or efficient generated code.
Each was found by a failing comparison against scsynth; the workaround is in
`translator/faust/sc.lib` or the code generator.

## Compile time

**`with` names and function parameters are expanded at every use.** Box evaluation
substitutes the expression, so a definition referenced n times inside a function is
evaluated n times, and nesting multiplies. Five band-limited Saws fed by a pitch tracker
took 2 minutes and 2.3 GB to compile; passing the signals as lambda parameters
(`(a, b) : \(x, y).(...)`) brought it to 0.4 s. The code generator now passes every
signal argument of a library call that way.

**Selecting outputs of a tuple re-expands the tuple.** `f(x) : _, !` and `f(x) : !, _`
evaluate `f(x)` twice; with nesting, this grew exponentially (6 LF oscillators: 14 s).
Route with `<:` and lambdas instead. Float-pair chains are the worst case, every pair
being a tuple: FreqShift's six-stage double cascades took 48 s to compile with
`dmulf(...) : _, !` / `: !, _` in each stage, 0.9 s with each pair bound once
(`dmulf(...) : \(h, l).(...)`), bit-identical output.

## Arithmetic the compiler rewrites

**Algebraic simplification breaks error-free transformations.** `(a + b) - a` is
simplified to `b`, which destroys TwoSum. Wrapping additions in `fmaf(a, 1, b)` (an
opaque `ffunction`, same rounding as `a + b`) prevents it.

**Constants are folded across operations.** `x * 0.04 * SR` became `x * 1920`, changing
the rounding of a delay time (381.99997 vs 382 samples); `y * (1/B)` became `y / B`.
Both fixed with `fmaf(x, k, 0)`.

**Sums may be reordered.** Where the reference sums in a specific order (FreeVerb's
comb outputs), the additions go through `fadd`.

**`1/x < 0` is simplified**, so it cannot detect −0.0; `copysignf` via `ffunction` can.

**`(x - x) * k` folds to 0**, so it cannot produce a NaN; `copysign(1/x, 1) - abs(1/x)`
does (inf − inf).

## Precision on a float target

**Compute filter coefficients in forms that round once.** For a biquad at 30 Hz the
gain depends on `1 - b1 - b2 ≈ 1e-5`; the textbook `-2 (1 - C²) a0` in float is 20×
worse than the float floor. Writing `b1 = 2 - e1`, `b2 = -1 + e2` with the small `e`
computed directly gets the correctly rounded value (or one ulp off near a tie).

**Recursions that the reference runs in double need closed forms or float pairs.**
Phase accumulators (LF oscillators): a float-pair (TwoSum) accumulator. Envelope
segments (EnvGen sine/welch resonator with `2 cos(π/n)` = 2 − 4e-7): closed form from
the sample index. Integer phase increments `(int32)(double × float)` (SinOsc, Saw):
integer long division.

## Runtime and tooling

**Nested `pow` on derived signals crashes the libfaust JIT** (DawDreamer, segfault):
`pow(pow(a, 1/c), k)` where `c` comes from a held value, and GVerb's `pow(alpha, len)`.
`exp(k * log(a))` works.

**DawDreamer aliases input and output buffers.** Without `-inpl`, an output written first
is read back as the input by later outputs of the same sample.

**A constant division by zero in an unselected branch is a compile error** (`select2`
does not protect it): guard denominators with `select2(d == 0, d, 1)`.

**Reserved names:** `round`, `sum` (and other primitives/iterators) cannot be used as
function or variable names in a library.

**Operator precedence:** `&` and `|` bind tighter than comparisons: write
`(a > 0) & (b < 1)`.

**`-ftz 2` flushes only recursive signals.** Products of decayed values can still be
denormal; feeding back a zapped state requires routing the zapped value into `~`.

**`ffunction` is the escape hatch** for libm functions the compiler cannot see into
(`fmaf`, `copysignf`, `expm1f`); available in the LLVM JIT and in C++ output.

**`x * (c / SR)` is rewritten as `x * c / SR`**, one rounding of the exact quotient, where
scsynth multiplies by the float `c / SR` (two roundings). Use the opaque
`fmul(a, b) = fmaf(a, b, 0.0)` for products by a rounded constant (`sc.lib`).

**In a function call, `f(a, x : _, !)` passes three arguments** (`a`, `x : _`, `!`): the
comma splits first. Parenthesise: `f(a, (x : _, !))`.

**The normaliser distributes and folds.** `(r - 1) * sc` becomes `r * sc - sc`, and
`1 / (0.5 / N)` becomes `2 * N`: algebraically equal, different roundings. Where scsynth's
float order matters, hide operands behind `fmul`/`fadd`/`fsub` (opaque `fmaf`). This made
Saw, Pulse and Blip bit-exact (they had been at 1e-3).

**Float division may round a quotient up to an integer** (`24000 / 166.66667f` = 144 in
float, 143.99999 in double): for `(int)(a / b)` computed in double, correct the float
quotient with the exact remainder `fmaf(-q, b, a)` (`sc.bl_N`).

**faust 2.70.3 segfaults** (the CLI; libfaust in DawDreamer compiles the same code) on
`fmod` combined with opaque `fmaf` operations when the modulus is a recursive signal
(`sc.moddif` fed by a per-block ramp). Plain operators there compile; use the opaque forms
only where reassociation would change the result.

**libfaust 2.85 (DawDreamer) asserts in `mterm.cpp`** on a state machine fed a constant
(`sc.trig1(1.0, ...)`), where the 2.70 CLI compiles it. Pass such inputs through the
opaque `fadd(x, 0.0)`.

## A top-level name can clash with stdfaust's environments

`import("stdfaust.lib")` defines `ba`, `db`, `de`, `fi`, `ma`, `os`, `si`... A generated
definition with one of these names (a SynthDef control called `db`) fails to compile:
"redefinition of symbols are not allowed : db". Generated control identifiers are
prefixed (`ctl_db`); the slider label keeps the SynthDef's name.

## NaN cannot be detected with comparisons

libfaust's JIT (DawDreamer) optimises as if no value were NaN: `x != x`, or "fails every
comparison" tests, do not see a NaN (Sanitize passed 0/0 through). Use the C library
through `ffunction` (`isnanf`, `isinff` from <math.h>), which the compiler cannot fold.
Related: Faust arithmetic does not flush subnormals (only `-ftz` on recursive states),
while scsynth runs with flush-to-zero: a product like `x * 1e-39` is subnormal in Faust
and 0 in scsynth.

## Algebraic normalisation can undo an overflow-avoiding regrouping

Faust normalises products and quotients: `K * (r / a)^2 * (r / b)^2 / c`, written to keep
every intermediate in float range, was merged back into `K * r^4 / (a^2 b^2 c)`, which
overflows (AmpCompA's A-weighting: NaN from 1 kHz up). Chain the factors through opaque
`fmul` (fmaf) so the compiler cannot recombine them.

## Several band-limited kr oscillators in one program compile superlinearly

Saw.kr, Pulse.kr and Blip.kr each compile in 5-16 s through DawDreamer; all three in one
SynthDef took over 10 minutes (the ar ports showed the same with five Saws). Regression
cases keep one band-limited oscillator per SynthDef; consumers with several should expect
long compiles.

## -ftz 2 turns -0.0 into +0.0 in recursive signals

The flush-to-zero applied to recursive signals also zeroes the sign of -0.0, so a value held
through `sc.a2k` (a sample-and-hold recursion) loses it; scsynth keeps it. It shows only
in sign-of-zero-sensitive results: Hasher (the bit pattern of -0.0), 1 / x (the sign of
the infinity). Measured: Hasher.kr on bass_di, 4 of 4574 blocks with a -0.0 input. A
non-recursive hold (x@(time % blocksize)) would keep it, at the cost of a delay line per
hold: not done.

## Division by a constant becomes multiplication by its float reciprocal

`ma.SR / max(8000, 0.001)` compiles to `SR * (1 / 8000)`, and 1/8000 is not exact in
float: 6.0000005 where scsynth's `mSampleRate / sc_max(freq, 0.001f)` gives 6. A counter
compared against it (the chaos UGens' samplesPerCycle) then fires one sample late.
Translated code mostly escapes it because inputs arrive through `sc.a2k` (a recursive
signal, not a constant), but a literal argument does not. Make the divisor opaque:
`sr / fadd(max(freq, 0.001), 0.0)` (chaos_g, henon_g).

## DawDreamer's JIT does not round sqrt correctly

libfaust's LLVM JIT inside DawDreamer evaluates `sqrt` with a fast approximation: up to 3
ulp off, 41 % of inputs differ, and sqrt(1) = 0.99999994, sqrt(4) = 1.99999988. Every other
math primitive (exp, log, pow, the trigonometric functions, fmod, the roundings) agrees
bit for bit with the C++ path. An `ffunction` calling `sqrtf` is recognised and
approximated the same way, Faust cannot declare a `double` ffunction, and no compile
flag changes it. The C++ that `faust` generates calls `std::sqrt`, correctly rounded, so
targets are not affected: layer 2 renders through that C++ (tests/arch_render.cpp, g++
-O2) and keeps DawDreamer only for layer 3's automated sweeps.

