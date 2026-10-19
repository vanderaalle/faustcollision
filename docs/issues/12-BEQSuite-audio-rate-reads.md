# BEQSuite filters with audio-rate inputs read only the first third of each block (and BBandPass/BBandStop/BHiShelf skip samples)

**Environment:** SuperCollider 3.13.0, Linux x86_64 (Ubuntu 24.04 package), scsynth NRT, 48 kHz, block size 64.

## Description

With every coefficient input at audio rate, `BLowPass`, `BHiPass`, `BAllPass`,
`BBandPass`, `BBandStop`, `BPeakEQ`, `BLowShelf` and `BHiShelf` read `freq`,
`rq`/`bw`/`rs` and `db` once per 3-sample group with `ZXP`. Group g reads the
block's sample g, so the 21 groups use samples 0-20 and the modulation in the rest of the
block is never read. The coefficients then apply to the group's 3 samples, so the filter
follows a time-compressed copy of the first third of each block.

`BBandPass`, `BBandStop` and `BHiShelf` also store the compared value with a second
`ZXP` inside the change branch (`unit->m_freq = ZXP(freq);`), so every change advances
the read pointer by 2: while the input keeps changing they read samples 0, 2, 4 ... 40.

## Steps to reproduce

```supercollider
(
{
    var in = WhiteNoise.ar(0.3);
    var f = SinOsc.ar(3) * 1500 + 2000, q = SinOsc.ar(5) * 0.3 + 0.7;
    BLowPass.ar(in, f, q)
}.plot(0.1)
)
```

## Expected

The coefficients follow `freq` and `rq` across the block (per sample, or at least
spread evenly over it).

## Actual

(NRT, 2 s, all eight classes, inputs stepped with `LFNoise0.ar` and continuous with
`SinOsc.ar`.) A double-precision simulation reading sample g in group g (plus the extra
read for the three classes above) matches scsynth bit for bit; a simulation reading each
group's own first sample (3g) differs on 99% of the samples. Swapping the extra-read rule
between classes differs on 28-41% of the samples.

## Cause

`server/plugins/FilterUGens.cpp`, `BLowPass_next_aa` and the other `*_next_aa` /
`*_next_aaa`: `nextfreq = ZXP(freq); nextrq = ZXP(rq);` once per `mFilterLoops`
iteration; in `BBandPass_next_aa`, `BBandStop_next_aa`, `BHiShelf_next_aaa` also
`unit->m_freq = ZXP(freq);` (and `m_bw`/`m_rs`/`m_db`) when the values changed.

## Suggestion

Read `freq[3 * g]` (index the input buffer instead of `ZXP`), and store the value just
read (`unit->m_freq = nextfreq;`) in the three classes with the extra read.

## Note

Found while writing a SynthDef-to-Faust translator that is checked sample by sample
against scsynth renders.
