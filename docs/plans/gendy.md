# Gendy1, Gendy2, Gendy3 (GendynUGens.cpp)

Random walks over N = initCPs breakpoints (read once in the constructor; knum, read per
period, limits the walk to the first num, num outside 1..N meaning N). The RNG is the
synth's (not reproducible): compare by statistics.

## Shared
- N is a constant input: the breakpoint memories become N parallel states
  (`par(j, N, ...)`), not tables. Gendy1/2 update one slot per period (select by index ==
  j); Gendy3 updates all of them in one sample.
- Constructor memories from the RNG: a pure hash of (seed, j) (`hrand`), no recursion.
- `Gendyn_distribution(which, a, f)` (cpp:114): a clamped to [0.0001, 1]; cases 0 linear,
  1 Cauchy, 2 logist, 3 hyperbcos, 4 arcsine, 5 expon, 6 sinus (2a - 1), default 2f - 1.
  which = (int) input, read per block. scsynth calls double tan/atan/log on floats; float
  here (statistics anyway).
- `Gendyn_mirroring(lo, hi, x)` (cpp:351), Gendy1's own mirroring (amp: +4, fmod 4, fold;
  dur: +2, fmod 2, 2 - x).
- No constructor step: the constructor writes 0 (OUT0) and the first block starts with
  phase = 1 (a period boundary at its first sample). Gendy1's mDur is uninitialised but
  overwritten there.
- Inputs read per block (ZIN0) except num (per period) and Gendy2's a, c (per period):
  all a2k.

## Gendy1 (cpp:203)
State: phase (double: a float pair or plain float? phase += speed, speed ~ 1e-2: float
drift is small against statistics; start plain), amp, nextamp, speed, index, N amps, N durs.
At phase >= 1: phase -= 1; index = (index + 1) % num; amp = nextamp; nextamp = mirror(mem[index]
+ scaleamp * dist(frand)); rate = fold(memdur[index] + scaledur * dist(frand));
speed = (minfreq + (maxfreq - minfreq) * rate) * sampledur * num. Output (1 - phase) amp
+ phase nextamp, then phase += speed.

## Gendy2 (cpp:370)
As Gendy1 plus per-slot step memories (ampstep, durstep): ampstep walks with the
distribution fed by a Lehmer-style |fmod(amp * a + c, 1)| of the previous amp (amp before
it becomes nextamp), durstep with frand; all through Gendyn_mirroring.

## Gendy3 (cpp:519)
At phase >= 1: all slots j < num walk (slot 0's amp stays 0: memoryamp[0] = 0 in the
constructor and never updated), dur mirrored into [0.01, 1]; normalised by their sum;
the active list keeps slots with dur * (1/sum) >= sampledur (compaction: position = count
of active slots before it), guard amp 0 / phase 2 after the last; speed = freq * sampledur;
nextphase = 0, nextamp = amplist[0], index = -1.
Every sample: if phase >= nextphase, step ONE region (index++, amp = nextamp, lastphase =
nextphase, nextphase += phaselist[index], nextamp = amplist[index + 1], interpmult =
(int)(1 / (nextphase - lastphase))). interp = (phase - lastphase) * interpmult: the
truncation quantises the slope, and regions shorter than speed are consumed one per sample.
Lists: amplist/phaselist as N + 1 parallel states rebuilt at the boundary; reading
phaselist[index] is a selectn over N + 1.

## Cases
statistics: defaults; distribution 0..6 sweep (one instance each, or a few per case);
knum < initCPs; .kr of each. Compile time with N = 12 parallel states x 2..4: check.
