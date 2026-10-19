# LocalIn outputs its uninitialised bus instead of the default in the server's first block

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

`LocalIn` should output its `default` until a `LocalOut` writes to it. A synth that
starts in the server's very first block (`mBufCounter == 0`, e.g. an NRT score with
`/s_new` at time 0) instead outputs the bus memory, which nothing has written. In our
renders the memory happened to be zero; a server reusing that memory would output stale
data. Started from block 1 on, the default is output as documented.

## Steps to reproduce

NRT score, one synth started in block 0, the same SynthDef started in block 1. (NRT runs
every command timestamped up to the end of the current block, so block 1 needs a time
strictly after 64 samples.)

```supercollider
(
var sr = 48000;
var defs = [0, 1].collect { |o|
    SynthDef(("li" ++ o).asSymbol, { var x = LocalIn.ar(1, 0.5); LocalOut.ar(x * 0); Out.ar(o, x) })
};
Score([
    [0, ['/d_recv', defs[0].asBytes]], [0, ['/d_recv', defs[1].asBytes]],
    [0, Synth.basicNew(\li0, nil, 1000).newMsg],             // starts in block 0
    [64.5 / sr, Synth.basicNew(\li1, nil, 1001).newMsg]      // starts in block 1
]).recordNRT(nil, "localin.wav", nil, sr, "WAV", "float",
    ServerOptions.new.numOutputBusChannels_(2).sampleRate_(sr), "", 0.01);
)
```

(`LocalIn.ar(3, [0.5, 0.1, -0.2])` and `LocalIn.kr(1, 0.1)` measured likewise.)

## Expected

Each synth outputs the default (0.5) in its first block, then 0 (what `LocalOut` wrote).

## Actual

Channel 1 (started in block 1): 0.5 for samples 64-127, then 0, as expected. Channel 0
(started in block 0): 0 from the first sample: the content of the freshly allocated bus.

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
