# FreqShift ignores a constant or control-rate phase (m_radtoinc read before it is set)

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`FreqShift.ar(in, freq, phase)` with a constant or control-rate `phase` behaves as if the
phase were 0 (in NRT; in a running server, as if it were an arbitrary value).

## Steps to reproduce

```supercollider
(
{
    var x = SinOsc.ar(440) * 0.5;
    [FreqShift.ar(x, 100, 0.5), FreqShift.ar(x, 100, 0), FreqShift.ar(x, 100, DC.ar(0.5))]
}.plot(0.05)
)
```

## Expected

The first and third channels equal (phase 0.5 either way), the second different.

## Actual

(NRT.) The first channel equals the second exactly; it differs from the third by up to
0.25.

## Cause

`server/plugins/FilterUGens.cpp`, `FreqShift_Ctor`: in the kk branch,
`unit->m_phase = (int32)(unit->m_radtoinc * IN0(2));` runs before
`unit->m_radtoinc = tableSizeSin * (rtwopi * 65536.);`, so it multiplies by uninitialised
memory. `FreqShift_next_kk` afterwards adds only changes of the phase input (through the
increment), never its value.

## Suggestion

Assign `m_radtoinc` (and `m_cpstoinc`, `m_lomask`) before the rate switch.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
