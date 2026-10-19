# IEnvGen truncates curvatures to integers

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`IEnvGen` interpolates a curve segment with its curvature truncated toward zero:
`Env([0, 1], [1], -4.5)` is read with curve -4, and any |curve| < 1 becomes linear.
`EnvGen` uses the given value.

## Steps to reproduce

```supercollider
(
{
    var idx = Line.ar(0, 1, 1);
    [IEnvGen.ar(Env([0, 1], [1], -4.5), idx), IEnvGen.ar(Env([0, 1], [1], -4), idx),
     IEnvGen.ar(Env([0, 1], [1], 0.7), idx)]
}.plot(1)
)
```

## Expected

Three different curves (-4.5, -4, 0.7).

## Actual

(NRT.) The first channel equals the curve -4 formula within 1.5e-7 (it differs from -4.5
by 3.9e-2); the third is linear within 3e-8.

## Cause

`server/plugins/LFUGens.cpp`, `IEnvGen_Ctor` / `IEnvGen_next_a` / `IEnvGen_next_k`:
`int curve = (int)unit->m_envvals[(stage * 4) + 3];`, then `GET_ENV_VAL` uses
`exp((float)curve)`.

## Suggestion

`float curve = unit->m_envvals[(stage * 4) + 3];`

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
