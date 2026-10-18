# scaleneg in sclang returns -a*b for negative a (documented: a*b)

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

The help for `scaleneg` says: "a*b when a < 0, otherwise a". In sclang the result for
negative `a` has the wrong sign. The server's audio- and control-rate `BinaryOpUGen`
are correct, so language and server disagree.

## Steps to reproduce

```supercollider
[(-2.0).scaleneg(0.5), (-2).scaleneg(0.5)].postln;
// -> [ 1.0, 1.0 ]   expected [ -1.0, -1.0 ]

{ BinaryOpUGen('scaleneg', DC.ar(-2), DC.ar(0.5)) }.plot(0.01);
// -> -1.0 (correct)
```

## Cause

The float and double specialisations in `include/plugin_interface/SC_InlineBinaryOp.h`
(lines 561 and 570) compute

```cpp
b = 0.5 * b + 0.5;
return (std::abs(a) - a) * b + a;
```

which for `a < 0` is `-2a * (b/2 + 1/2) + a = -a*b`. The generic template above them
(`a < 0 ? a * b : a`) is correct. The specialisations are used by sclang
(`lang/LangSource/PyrMathOps.cpp:1678` and neighbours) and by demand-rate
`BinaryOpUGen` (`server/plugins/BinaryOpUGens.cpp:836`); audio-rate `scaleneg_aa` uses
the plain formula.

## Suggestion

Use the generic branch in the specialisations as well.
