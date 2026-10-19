# Saw.kr, Pulse.kr and Blip.kr output inf/NaN above 375 Hz

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

At control rate the band-limited oscillators produce non-finite output for any
frequency above SampleRate / 128 (375 Hz at 48 kHz).

## Steps to reproduce

```supercollider
(
{
    var f = Line.kr(300, 450, 2);
    K2A.ar([Saw.kr(f), Pulse.kr(f), Blip.kr(f, 200)])
}.plot(2)
)
```

## Expected

Finite output (aliased, or silent above the control-rate Nyquist).

## Actual

(NRT.) From 375.1 Hz on, every block of all three channels is inf or NaN (750 of 1501
blocks); below, the output is finite.

## Cause

`server/plugins/OscUGens.cpp`: the harmonic count is `N = (int32)((SAMPLERATE * 0.5) /
freq)`; at control rate SAMPLERATE is SR / 64, so N = 0 above 375 Hz, and
`scale = 0.5 / N` is inf. `Saw_next` and `Pulse_next` (and their constructors) never
clamp N; `Blip_next` clamps it to 1 only in the `else` branch, not when `N > maxN` sets
`N = maxN` (= 0).

## Suggestion

Clamp N to at least 1 in all branches (or output 0 above the rate's Nyquist).

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
