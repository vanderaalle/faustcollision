# C++ backend: `-ftz 2` generates `&-fTemp` (address of an rvalue) for a negated recursion

**Environment:** Faust 2.70.3 (Ubuntu 24.04 package) and 2.85.9 (built from the tag), C++
backend, g++ 13.3, Linux x86_64.

## Description

With `-ftz 2` (flush denormals by bit masking), the C++ backend writes the recursive value
through `*reinterpret_cast<int*>(&EXPR)`. When the value Faust has normalised into a plain
negation, EXPR is `-fTempN`, an rvalue, and the generated C++ does not compile. A
first-order highpass from the standard library is enough to trigger it.

## Steps to reproduce

```faust
import("stdfaust.lib");
process = fi.highpass(1, 20.0);
```

```
faust -single -ftz 2 hp.dsp -o hp.cpp
g++ -c hp.cpp      # with a minimal architecture
```

## Expected

Compilable C++, as with `-ftz 0` or `-ftz 1`, e.g. the value stored in a temporary first:
`float fTemp2 = -fTemp1; fRec0[0] = ((*reinterpret_cast<int*>(&fTemp2) & 2139095040) ? fTemp2 : 0.0f);`

## Actual

```
fRec0[0] = ((*reinterpret_cast<int*>(&-fTemp1) & 2139095040) ? -fTemp1 : 0.0f);
error: lvalue required as unary '&' operand
```

The LLVM backend (libfaust, e.g. in DawDreamer) is not affected, so the problem only shows
when the C++ is compiled. `an.pitchTracker` inherits it through its `fi.highpass(1, 20.0)`.

## Suggestion

In the `-ftz 2` code path, bind the value to a temporary when it is not already a variable,
or use a `std::bit_cast`/`memcpy` helper taking the value rather than its address.

## Note

Found while writing a SuperCollider-to-Faust translator whose output is compiled as C++
(for an embedded target) and checked sample by sample against scsynth.
