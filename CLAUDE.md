# FaustCollision

SuperCollider SynthDef → Faust translator; every UGen port checked against scsynth.
See README.md for usage. Consumers (e.g. the vairi pedal project) use it as a git submodule
and run `translator.build --project DIR` / `pytest --project=DIR` on their own `defs/`.

## Rules

- Port from scsynth's C++ (`~/src/supercollider`, tag Version-3.13.0, nova-simd submodule
  fetched), not from the help files. Cite file:line in comments for non-obvious behaviour.
- The mapping table (`translator/mapping.toml`) is data, not code. Tolerances live in its
  entries; a tolerance above the exact level states the measured floor and its cause.
- Unmapped UGen → hard error naming the class. Never guess a translation; inputs a port
  ignores are `require`d constants, inputs scsynth reads once are `constant_inputs`.
- Every mapping entry (every operator) has a regression case in `tests/cases/`, covering
  the calc functions scsynth picks by input rate (ar/kr, constant/kr/audio inputs).
- Behaviour of scsynth that differs from its documentation goes into `docs/sc-findings.md`
  with status measured/source; measure before calling something a bug.
- Faust pitfalls go into `docs/faust-notes.md`.
- sclang runs headless and once per batch; Faust renders via DawDreamer with
  `-single -ftz 2 -inpl`. `build/`, `report/` are generated.

## Semantics fixed so far

- kr UGens fed by audio are held per block, one block late (`sc.krhold`); kr UGens fed only
  by kr inputs are sampled at the block start (`sc.a2k`); BinaryOpUGen and K2A ramp kr
  inputs across the block like scsynth (`sc.kr2ar`).
- Constructor samples (most UGens compute one sample in the constructor) are modelled per UGen.
- Not modelled: the constructor-time value of an input. Where scsynth reads an input in the
  constructor (initial state, ramp start), the port uses its first-block value. They differ
  when the input comes from a UGen whose constructor sample differs from its first block
  (LF oscillators, XLine, VarSaw...). Regression cases feed such inputs from Line or constants.
- Test signals start with 100 ms of silence; comparisons skip the first block.
- Double-precision state in scsynth: float pairs (phase), exact integer math (increments,
  counters), closed forms (envelope segments), or a documented float floor.
