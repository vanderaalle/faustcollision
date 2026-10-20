# Chaos oscillators: Crackle, Logistic, Cusp*, FBSine*, Gbman*, Henon*, Latoocarfian*, LinCong*, LorenzL, Quad*, Standard*

Prepared (source read), not yet written. server/plugins/ChaosUGens.cpp (Crackle, Logistic:
NoiseUGens.cpp). Read ZIN0 only (no input over-reads).

Structure (NonLinear units): a map iterated in double (xn, yn, ... from double inputs a, b,
c...), one iteration every samplesPerCycle = SR / max(freq, 0.001) samples (1 when freq >=
SR), a float counter (counter++ per sample, -= samplesPerCycle on iteration); N: hold xn;
L: linear interpolation between the last two iterates (frac = counter / samplesPerCycle);
C: cubic over four. x0 (initial condition) inputs reset xn when they change (unit->x0 !=
x0). LorenzL integrates an ODE (h step) in double.

Exactness: chaotic maps amplify rounding differences exponentially; a float port (or even
float pairs: sqrt/sin/cos/fmod in double would need emulation) follows scsynth's sequence
for a few dozen iterations, then diverges. Compare by statistics (as the random UGens),
with the reason in each mapping entry; regression cases at freq >= SR/10 so a render has
many iterations, plus a check that the first iterations match exactly (case at a low
freq, waveform over the first 0.1 s) where the map is a plain polynomial (Quad, Henon,
LinCong, Gbman...).

Per class (to read before writing): CuspN/L (xn = a - b sqrt|xn|), GbmanN/L (gingerbread
man, two state), HenonN/L/C (x' = 1 - a x^2 + b y), LatoocarfianN/L/C (sin terms),
LinCongN/L/C (fmod), LorenzL (RK? Euler with h), QuadN/L/C (a x^2 + b x + c), StandardN/L
(standard map with fmod 2pi), FBSineN/L/C (sin feedback), Crackle (y0 = |y1 * param - y2 -
0.05|), Logistic (y = chaosParam * y * (1 - y) at freq rate).
