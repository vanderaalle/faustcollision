# PanAz, SplayAz, PanB, PanB2, BiPanB2, DecodeB2

Prepared (source read), not yet written. All in server/plugins/PanUGens.cpp; all have
checkInputs (input rate safe).

- PanB (955), PanB2 (1039), BiPanB2 (1162): gains from the sine table by truncated index
  (no interpolation): isin = mask & (long)(azimuth * 4096.f) (float product; elevation *
  2048.f for PanB), sin = -mSine[isin], cos = mSine[mask & (isin + 2048)]; W = rsqrt2_f *
  level, X = cos (* cosb) * level, Y = sin (* cosb) * level, Z = sinb * level (PanB). On a
  change of azimuth/elevation/level: ramp by CALCSLOPE, the accumulated gains are stored
  (as Pan4: sc.gacc). BiPanB2: W only ramps when its slope is nonzero (optimisation, same
  values); W = (a + b) * W_amp, X/Y = (a - b) * X/Y_amp. Constructors: gains from the
  inputs, then next(1). Outputs 4 (PanB), 3 (PanB2, BiPanB2).
- DecodeB2 (constructor near 1300): orientation read once; angle = twopi_f / numOutputs;
  gains W_amp = 0.7071067811865476f, X_amp = 0.5f * (float)cos(orientation * angle),
  Y_amp = 0.5f * (float)sin(...), rotated per output: X' = X cosa + Y sina, Y' = Y cosa -
  X sina (float): per-output constants from derive.py (float recurrence). The constructor
  calls next(1) before setting the gains (uninitialised for that one sample, not stored:
  no lasting effect). out_k = W * W_amp + X * X_k + Y * Y_k.
- PanAz (1270): ak: rwidth = (float)(1 / (double)width), range = n * rwidth, rrange =
  (float)(1 / (double)range); pos = pos * 0.5 n + width * 0.5 + orientation; per channel:
  chanpos = ((pos - i) * rwidth) wrapped by range * floor(rrange * chanpos); amp = level *
  mSine[(long)(4096.f * chanpos)] if chanpos < 1 else 0. The target is stored (ramp from
  the previous target, float accumulation) - unlike PanB. The constructor's next(1)
  stores the first targets (no ramp in the first block). aa (pos audio rate): per-sample
  amps (read PanAz_next_aa before writing).
- SplayAz: sclang sugar over PanAz + operators: free once PanAz is mapped.

Cases: knob azimuth/pos (kr ramp), an audio-rate pos for PanAz, n = 4, 5, 8 outputs, width
1, 2, 3, orientation 0.5; DecodeB2 with 4 and 6 outputs and orientation 0 / 0.5.
