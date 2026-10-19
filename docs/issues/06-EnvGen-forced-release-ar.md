# EnvGen with an audio-rate gate: a forced release corrupts and shortens the release segment

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

With an audio-rate gate, a forced release (gate <= -1) during a running segment does not
start the release correctly: the envelope jumps to an unrelated value, and the release is
shorter than requested. With a control-rate gate the same envelope releases correctly.

## Steps to reproduce

```supercollider
(
{
    var gate = K2A.ar(Line.kr(1, -1.012, 0.05));   // drops below -1 mid-segment
    [
        EnvGen.ar(Env.perc(0.01, 0.3), gate),       // audio-rate gate
        EnvGen.ar(Env.perc(0.01, 0.3), A2K.kr(gate)),  // control-rate gate
        gate
    ]
}.plot(0.1)
)
```

(Also seen with `EnvGen.ar(Env.perc(0.01, 0.3), SoundIn.ar(0))` on white noise: when the
gate dips to -1.012 the level, near 1.0, jumps to -0.0187 instead of starting a 12 ms
curve to 0.)

## Expected

A release from the current level to 0 over `-gate - 1` seconds, as with a control-rate gate.

## Actual

(NRT render of the snippet.) The gate passes -1 at sample 2418. The control-rate gate
channel then releases from 0.5756 to 0 over 589 samples (12 ms = 576 requested; the gate
is read per block). The audio-rate gate channel drops from 0.5758 straight to 0 at sample
2418 and stays there: no release segment at all.

## Cause

`EnvGen_next_aa` (`server/plugins/LFUGens.cpp:2910`) checks the gate inside the
segment loop of `EnvGen_perform` (line 2681), which keeps the running segment's state in
local variables. On a forced release, `check_gate` (line 2608) calls
`EnvGen_initSegment` right there, setting the new segment's `m_b1`, `m_y1`, `m_y2`,
`m_counter`. The loop then breaks and writes its stale locals back
(`unit->m_b1 = b1;` at line 2754 for a curve segment; `m_y1`/`m_y2` for sine, welch,
squared, cubed), overwriting the new segment's state.

Also, `check_gate` adds the in-loop offset to `counter`, but `EnvGen_initSegment`
recomputes the segment from `counter`, and `EnvGen_next_aa` then subtracts `nsmps`
(the offset) from it: the release loses those samples.

## Suggestion

On a forced release, defer `EnvGen_initSegment` until after `EnvGen_perform` has
written back its state (e.g. set a flag in `check_gate` and initialise the segment in
`EnvGen_next_aa`), and do not subtract the offset from the new segment's counter.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
