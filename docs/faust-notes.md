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
Route with `<:` and lambdas instead.

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
