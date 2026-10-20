# Spring, Ball, TBall

Prepared (source read), not yet written. server/plugins/PhysicalModelingUGens.cpp; none has
checkInputs and all read `in` per sample (sc-findings 21, measured for Ball and Spring):
require an audio-rate input at .ar (ar_inputs). kr: one step per block at SR / 64.

- Spring (77): float state pos, vel; c = SAMPLEDUR, rc = SAMPLERATE (float), spring *= c,
  damping = 1 - damp: force = in * c - pos * spring; vel = (force + vel) * damping; pos +=
  vel; out = force * rc. Deterministic: exact in float.
- Ball (105): float pos, vel, prev floor; g = c * gravity, k = friction * gravity (double
  product, stored float), inter = c * 1000; per sample: vel -= g; pos += vel; dist = pos -
  floor; floorvel = clip(floor - prev, -c*1000, c*1000); |dist| < k: stick (|dist| < k *
  0.005: vel = 0, pos = floor + g; else vel/pos pulled with inter); dist <= 0: bounce (pos
  = floor - dist, vel = (floorvel - vel) * damping + frand * 0.00005 * gravity). out = pos.
- TBall: as Ball with pos and prev floor in double (pairs), inter = c * 10000, output the
  bounce velocity on bounce samples (else 0), dither frand * 0.001 * gravity.
- The dither uses scsynth's RNG: our stream differs, so trajectories drift after each
  bounce by ~dither: compare by waveform with a measured floor, or envelope (TBall's
  impulses: timing exact until dithers accumulate). Measure on a case with few bounces.
- Constructors: read once (Ball_Ctor 96: pos = in, vel = 0, prev = in?) check before writing.
