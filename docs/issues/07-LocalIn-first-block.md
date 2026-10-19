# LocalIn outputs its uninitialised bus instead of the default in the server's first block

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`LocalIn` should output its `default` until a `LocalOut` writes to it. A synth that
starts in the server's very first block (`mBufCounter == 0`, e.g. an NRT score with
`/s_new` at time 0) instead outputs the bus memory, which nothing has written. In our
renders the memory happened to be zero; a server reusing that memory would output stale
data. Started from block 1 on, the default is output as documented.

## Steps to reproduce

NRT score, synth started at time 0 vs. at 64 samples:

```supercollider
SynthDef(\li, { |out| var x = LocalIn.ar(1, 0.5); LocalOut.ar(x * 0); Out.ar(out, x) }).add;
// /s_new at time 0: first block is 0.0
// /s_new at 64 / sampleRate: first block is 0.5
```

(`LocalIn.ar(3, [0.5, 0.1, -0.2])` and `LocalIn.kr(1, 0.1)` measured likewise.)

## Expected

The default (0.5) in the first block in both cases.

## Actual

0 (the content of the freshly allocated bus) when the synth starts at block 0.

## Cause

`LocalIn_Ctor` sets `m_busTouched[i] = -1` (`server/plugins/IOUGens.cpp:1560`).
`LocalIn_next_a` (line 1462) copies the bus when `diff = bufCounter - touched` is 0
or 1. In the first block of the server `bufCounter` is 0 (`server/scsynth/SC_World.cpp:350`),
so `diff == 1` and the untouched bus is copied. The control-rate `LocalIn_next_k` does
the same.

## Suggestion

Initialise `m_busTouched` to a value that can never give `diff` 0 or 1 (e.g.
`bufCounter - 2` at construction, or `INT32_MIN / 2`), or clear the bus in the
constructor.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
