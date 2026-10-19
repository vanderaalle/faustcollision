# Lag2UD, Lag3UD, AmpComp, AmpCompA, MantissaMask, Hasher

Prepared (source read), not yet written.

- Lag2UD, Lag3UD (FilterUGens.cpp:693...): LagUD's up/down coefficient choice per stage,
  cascaded (y1b follows y1a with the same up/down test); slope added before the sample,
  so at kr a time change applies at once. Port: two/three sc.lagud-style stages; kr per
  plans/lag-family-kr.md.
- AmpComp (LFUGens.cpp:2142-2170): two calc functions with different rounding for the
  same maths: constant root and exp -> AmpComp_next: rootmul = pow(root, exp) (float),
  out = pow(freq, -exp) * rootmul; otherwise AmpComp_next_kk: pow(root / freq, exp).
  Negative freq: sign-mirrored. Constructor runs one sample. checkInputs: .ar needs an
  audio freq. Port: template_by on the root/exp rates.
- AmpCompA (LFUGens.cpp:2192-2210): AmpCompA_calcLevel(freq) (the A-weighting curve, in
  double) * scale + offset, scale/offset from root, minAmp, rootAmp in the constructor
  (double). Inherits AmpComp's checkInputs.
- MantissaMask (NoiseUGens.cpp:872): keeps sign, exponent and the top `bits` mantissa bits
  (mask = -1 << (23 - bits)): truncation of |x| toward zero to bits + 1 significant
  bits. Faust has no bitcast: |x| = m * 2^e (sc.nfrexp), keep floor(m * 2^(bits + 1)) /
  2^(bits + 1). Edge cases: bits >= 23 (no masking; bits > 23 is a negative shift, UB:
  reject unless constant <= 23), bits < 0 (shift > 23 masks exponent bits: reject),
  zero, subnormals (flushed in both?). sc-findings 21 (measured): MantissaMask has
  no checkInputs and reads ZIN(0) per sample, so .ar of a kr/constant input reads past
  the buffer (source; measure).
- Hasher (NoiseUGens.cpp:851): Hash(int bits of the input float) -> 0x40000000 | (h >> 9)
  as float, minus 3: a float in [-1, 1). Needs the input's bit pattern: rebuild it from
  sc.nfrexp (sign, biased exponent, 23-bit mantissa) for normal floats and 0; then the
  32-bit integer Hash (Thomas Wang's, SC_RGen.h) with logical shifts (sc.lsr). Bit-exact
  possible; denormal inputs need a decision (flushed by -ftz in Faust?).
