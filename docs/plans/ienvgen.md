# IEnvGen

Prepared, not yet applied or tested. Apply, build, test, measure tolerances.


Inputs (Env.asArrayForInterpolation, Env.sc:385): index, offset, initLevel, numStages,
totalDur, then per stage [dur, shape, curve, level]. Read once in the constructor
(m_envvals): all envelope inputs must be constants (constant_inputs + variadic constant,
like Klank); index read per sample (next_a, ar index) or per block (next_k).

Behaviour (LFUGens.cpp:3155, GET_ENV_VAL at 3172):
- point = max(index - offset, 0); point >= totalDur -> last level; point <= 0 -> init
  level; else the segment j with cumulative float time > point (float accumulation of
  durations: newtime += seglen), pos = segpos / seglen (float).
- Probable sc-findings 27 (measure first): `int curve = (int)m_envvals[...]` truncates the
  curvature toward zero before exp((float)curve): Env([0, 1], [1], -4.5) interpolates
  with curve -4; any |curve| < 1 becomes linear (the 0.0001 test). EnvGen uses the float
  curve.
- Hold: returns the level computed by the previous lookup (level = m_level; m_level =
  endLevel), so the output depends on the previous index, not only on the current one.
  Step: endLevel. Note it as a convention in the mapping comment (or finding, if the help
  says otherwise: check IEnvGen.schelp).
- The unchanged-index shortcut compares the raw index with the stored offset-subtracted
  point: with a nonzero offset it always recomputes; no output effect except via Hold
  (recomputing a Hold segment advances m_level). Matters only for Hold: model it.
- Shapes as in EnvGen but per lookup, in float with double intermediates (pow, exp, sin,
  cos of float arguments: check which resolve to float or double libm, as in derive.py's
  fsinosc note).

Port: per-sample function of the index (ar: per sample; kr: a2k at block start; when the
index is unchanged, hold the output, which also keeps Hold right) with the envelope as
compile-time constants: derive.py precomputes the cumulative times (float accumulation),
levels, shapes and integer curves into a Faust table or a select chain (numStages is
small). Cases: index from Line/LFSaw over all shapes (linear, exp, sine, welch, curve with
an integer and a fractional curvature, squared, cubed, step, hold), offset nonzero, kr.

