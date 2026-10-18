# unsignedRightShift and fill on UGens compute a + b

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

The binary operators `unsignedRightShift` and `fill`, applied to UGens, are not
implemented on the server: they silently compute `a + b`.

## Steps to reproduce

```supercollider
(
{
    [
        BinaryOpUGen('unsignedRightShift', DC.ar(-8), DC.ar(1)),
        BinaryOpUGen('fill', DC.ar(8), DC.ar(1))
    ]
}.plot(0.01)
)
```

## Expected

`unsignedRightShift(-8, 1)` = 2147483644 (an unsigned 32-bit shift), or an error if the
operator is not supported on the server; `fill` either implemented or rejected.

## Actual

`unsignedRightShift(-8, 1)` = -7.0 and `fill(8, 1)` = 9.0, i.e. `a + b` (NRT render).

## Cause

`ChooseNormalFunc` in `server/plugins/BinaryOpUGens.cpp` has no case for
`opUnsignedShift` or `opFill`; the `default:` branch selects `add_aa`
(`BinaryOpUGens.cpp:5134`). The other rate combinations fall back the same way.

## Suggestion

Implement them, or reject operators the server does not support instead of falling back
to addition.
