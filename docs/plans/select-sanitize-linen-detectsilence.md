# Select, Sanitize, Linen, DetectSilence

Prepared, not yet applied or tested against scsynth. Standalone checks: all compile; Select bit-exact against truncate-and-clip indexing; Sanitize replaces exactly the inf/NaN samples; DetectSilence fires on the endCounter-th silent sample; Linen gives the expected shape (attack 37 blocks, release 75 at 750 Hz).

## sc.lib.part

```

//------------------------------------------------------------------------------
// Select (OscUGens.cpp:487): out = input[clip((int)which, 0, n - 1)] ((int32) truncates).
// .ar with audio-rate which: per sample (next_a); otherwise the block's value (next_k:
// kr signals are already per block); .kr: next_1.
//------------------------------------------------------------------------------
select(n, w, ins) = ins : ba.selectn(n, max(0, min(n - 1, int(w))));

//------------------------------------------------------------------------------
// Sanitize (TestUGens.cpp:167): infinite, NaN and subnormal samples become `replace`
// (std::fpclassify). NaN fails every comparison, so `ok` is false for it.
//------------------------------------------------------------------------------
sanitize(x, r) = select2(ok, r, x) with { a = abs(x); ok = (x == 0.0) | ((a >= ma.MIN) & (a <= ma.MAX)); };

//------------------------------------------------------------------------------
// (int)(a * b) for a float a and an exact b, as the double product C computes: the float
// product can round up to an integer (0.7f * 750 = 525 in float, 524.99999 in double);
// the exact remainder fmaf(a, b, -p) tells.
//------------------------------------------------------------------------------
iprod(a, b) = int(p) - ((p == floor(p)) & (fmaf(a, b, 0.0 - p) < 0.0) & (p > 0.0)) with { p = fmul(a, b); };

//------------------------------------------------------------------------------
// Linen (LFUGens.cpp, Linen_next_k; .kr only): one step per block, SAMPLERATE = SR / 64.
// Stages: 0 attack, 1 sustain, 2 release, 3 done (outputs 0 once), 4 idle (0). A gate rise
// starts the attack from the current level: counter = max(1, (int)(attack * SR)), slope =
// (sus - level) / counter. Only the sustain stage reads the gate for release (gate <= -1:
// forced, time -gate - 1; gate <= 0: releaseTime), so a gate that closes during the attack
// still reaches sus first. The constructor runs one step from (stage 4, or 1 when gate <=
// -1; level 0; prevGate 0); the first block steps again from its state.
//------------------------------------------------------------------------------
// one step: (stage, level, slope, counter, prevGate) -> same, plus the output
linen_step(g, at, sl, rt, st0, lv0, sp0, ct0, pg) = st2, lv2, sp2, ct2, g, out
with {
    srk = ma.SR / blocksize;
    rise = (pg <= 0.0) & (g > 0.0);
    ca = max(1, iprod(at, srk));
    st = select2(rise, st0, 0); ct = select2(rise, ct0, ca);
    sp = select2(rise, sp0, (sl - lv0) / float(ca));
    ramp = (st == 0) | (st == 2);
    out = select2(st >= 3, lv0, 0.0);
    rc = max(1, select2(g <= -1.0, iprod(rt, srk), iprod(0.0 - g - 1.0, srk)));
    rel = (st == 1) & (g <= 0.0);
    ctr = ct - 1;
    lv2 = select2(ramp, lv0, fadd(lv0, sp));
    st2 = select2(ramp, select2(rel, select2(st == 3, st, 4), 2), st + (ctr == 0));
    ct2 = select2(ramp, select2(rel, ct, rc), ctr);
    sp2 = select2(ramp, select2(rel, sp, (0.0 - lv0) / float(rc)), sp);
};
// state (5 wires) plus the held output, stepped at block starts; at time 0 the incoming
// state is the constructor's step from the initial state
linen_kr(g, at, sl, rt) = loop ~ si.bus(6) : par(i, 6, !), _
with {
    t0 = ba.time == 0;
    ctor(k) = linen_step(g, at, sl, rt, select2(g <= -1.0, 4, 1), 0.0, 0.0, 0, 0.0) : ba.selector(k, 6);
    loop(st, lv, sp, ct, pg, ho) = par(k, 5, select2(krclk, old(k), nxt(k))), select2(krclk, ho, nxt(5)), select2(krclk, ho, nxt(5))
    with {
        old(k) = (st, lv, sp, ct, pg) : ba.selector(k, 5);
        cur(k) = select2(t0, old(k), ctor(k));
        nxt(k) = linen_step(g, at, sl, rt, cur(0), cur(1), cur(2), cur(3), cur(4)) : ba.selector(k, 6);
    };
};

//------------------------------------------------------------------------------
// DetectSilence (FilterUGens.cpp): the counter starts at -1 and arms when |in| > amp
// (documented); armed, it counts samples with |in| <= amp and outputs 1 from the
// endCounter-th on (until |in| > amp again). endCounter = (int32)(SAMPLERATE * time) in
// double. Constant amp/time: read once (next), else per block (next_k): a2k. kr: one step
// per block (clk), SAMPLERATE = SR / 64. Constructor output 0 (ClearUnitOutputs).
//------------------------------------------------------------------------------
detsil_g(x, th, tm, sr, clk) = (\(c).(step(c))) ~ _ : !, _ : ba.sAndH(clk)
with {
    n = iprod(tm, sr);
    step(c0) = c2, out
    with {
        c = select2(ba.time == 0, c0, -1);
        loud = abs(x) > th;
        c1 = select2(loud, select2(c >= 0, c, c + 1), 0);
        c2 = select2(clk, c, c1);
        out = select2(loud | (c < 0), float(c1 >= n), 0.0);
    };
};
detectsilence(x, th, tm) = detsil_g(x, a2k(th), a2k(tm), ma.SR, 1);
detectsilence_kr(x, th, tm) = detsil_g(x, th, tm, ma.SR / blocksize, krclk);
```

## mapping.part

```

[Select]
tier = "direct"
inputs = ["which"]
variadic = { group = ["in"] }
faust = { ar = "sc.select({n}, {which}, ({ins}))", kr = "sc.select({n}, {which}, ({ins}))" }
compare = "waveform"
tol = 0
case = "case_Select"

[Sanitize]
tier = "direct"
inputs = ["in", "replace"]
faust = { ar = "sc.sanitize({in}, {replace})", kr = "sc.sanitize({in}, {replace})" }
compare = "waveform"
tol = 0
case = "case_Sanitize"

[Linen]
tier = "direct"
inputs = ["gate", "attackTime", "susLevel", "releaseTime", "doneAction"]
require = { doneAction = 0.0 }
self_hold = true
faust = { kr = "sc.linen_kr({gate}, {attackTime}, {susLevel}, {releaseTime})" }
compare = "waveform"
tol = 1e-7
case = "case_Linen"

[DetectSilence]
tier = "direct"
inputs = ["in", "amp", "time", "doneAction"]
require = { doneAction = 0.0 }
self_hold = true
faust = { ar = "sc.detectsilence({in}, {amp}, {time})", kr = "sc.detectsilence_kr({in}, {amp}, {time})" }
compare = "waveform"
tol = 0
case = "case_DetectSilence"
```

## case.part

```
	// Select: kr which (next_k), audio which (next_a), out-of-range and negative which (clip), kr
	SynthDef(\case_Select, { |which = 1| Out.ar(0, [Select.ar(which, [in.value, in.value.abs, in.value.neg]),
		Select.ar(in.value * 3, [in.value, DC.ar(0.25), in.value.squared]), Select.ar(in.value * 8 - 2, [in.value, DC.ar(-0.5)]),
		K2A.ar(Select.kr(LFNoise0.kr(3) * 3, [DC.kr(0.1), DC.kr(0.2), DC.kr(0.3)]))]) },
		metadata: (specs: (which: spec.(-1, 4, 1, \lin)))),
	// Sanitize: inf/NaN from a division by a 0/1 gate, a subnormal from a tiny product; kr replace; .kr
	SynthDef(\case_Sanitize, { Out.ar(0, [Sanitize.ar(in.value / (in.value.abs > 0.1), 0.5),
		Sanitize.ar(in.value * 1e-39, -0.5), Sanitize.ar(in.value / (in.value.abs > 0.1), LFNoise0.kr(5)),
		K2A.ar(Sanitize.kr(Latch.kr(in.value, Impulse.kr(50)) / (Latch.kr(in.value, Impulse.kr(50)).abs > 0.1), -0.25))]) }),
	// Linen: gate from the test signal (rises, falls, forced release via gate <= -1), attack
	// longer than some gates (the attack completes before release)
	SynthDef(\case_Linen, { |att = 0.05| var g = Latch.kr(in.value, Impulse.kr(20)) * 4;
		Out.ar(0, [K2A.ar(Linen.kr(g, att, 0.8, 0.1)), K2A.ar(Linen.kr(g.clip(-1.05, 1), 0.7, 0.5, 0.3))]) },
		metadata: (specs: (att: spec.(0.001, 1, 0.05)))),
	// DetectSilence: constant amp/time (next), kr amp (next_k), .kr; time with a product near an integer
	SynthDef(\case_DetectSilence, { |amp = 0.01| Out.ar(0, [DetectSilence.ar(in.value, 0.01, 0.05),
		DetectSilence.ar(in.value, amp, 0.0007), K2A.ar(DetectSilence.kr(Latch.kr(in.value, Impulse.kr(100)), 0.02, 0.7))]) },
		metadata: (specs: (amp: spec.(0.0001, 0.5, 0.01)))),
```

