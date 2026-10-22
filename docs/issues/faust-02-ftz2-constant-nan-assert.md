# `-ftz 2`: assertion in mterm.cpp on a constant NaN inside a recursion

**Environment:** Faust 2.70.3 (Ubuntu 24.04 package) and 2.85.9 (built from the tag), C++
backend, Linux x86_64.

## Description

With `-ftz 2`, a recursion whose signal contains a constant NaN (or infinity), as constant
folding produces for a division by zero hidden behind an `ffunction`, makes the compiler
stop with an internal assertion. A filter whose coefficients become infinite at a constant
0 Hz triggers it the same way.

## Steps to reproduce

```faust
import("stdfaust.lib");
fadd(a, b) = ffunction(float fmaf(float, float, float), <math.h>, "")(a, 1.0, b);
process = (+ : *(0.0 / fadd(0.0, 0.0))) ~ _;
```

```
faust -single -ftz 2 m.dsp -o m.cpp
```

## Expected

C++ that computes NaN at run time (as without `-ftz 2`), or an error message.

## Actual

```
A[0] == SigBinOp[14,SigBitCast[0],2139095040]
ASSERT : please report this message, the stack trace, and the failing DSP file to Faust developers
(file: mterm.cpp, line: 519, version: 2.70.3 ...)    // line 533 in 2.85.9
```

## Note

Found while writing a SuperCollider-to-Faust translator whose output is compiled as C++
(for an embedded target) with `-ftz 2`.
