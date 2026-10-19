# Median

Prepared, not yet applied or tested against scsynth. Standalone check: compiles; bit-exact against a NumPy sliding median (lengths 3, 8).

## sc.lib.part

```

//------------------------------------------------------------------------------
// Median (FilterUGens.cpp:2622): the last n inputs kept sorted by insertion; out =
// values[n >> 1] (the upper middle for even n). The window starts filled with the first
// input (Median_InitMedian; the constructor inserts it once more, which changes nothing
// with equal values). Here: an odd-even transposition sort of the n delayed values.
// n = clip((int)length, 0, 32) is read once (derive.median; 0 is rejected).
//------------------------------------------------------------------------------
mce = _, _ <: min, max;
mstage(n, 0) = par(i, int(n / 2), mce), si.bus(n % 2);
mstage(n, 1) = _, par(i, int((n - 1) / 2), mce), si.bus(1 - n % 2);
msort(1) = _;
msort(n) = seq(r, n, mstage(n, r % 2));
mwin(n, d, x) = par(k, n, select2(ba.time < k * d, x@(k * d), x0)) with { x0 = ba.sAndH(ba.time == 0, x); };
median(n, x) = mwin(n, 1, x) : msort(n) : ba.selector(int(n / 2), n);
median_kr(n, x) = mwin(n, blocksize, x) : msort(n) : ba.selector(int(n / 2), n);
```

## derive.part

```


def median(c):
    """FilterUGens.cpp Median_Ctor: size = sc_clip((int)length, 0, kMAXMEDIANSIZE = 32).
    Size 0 indexes values[-1] in Median_InsertMedian: rejected."""
    n = min(max(int(c["length"]), 0), 32)
    if n == 0:
        raise ValueError("length < 1 makes Median_InsertMedian index values[-1]")
    return {"n": n}
```

## mapping.part

```

[Median]
tier = "direct"
inputs = ["length", "in"]
constant_inputs = ["length"]
derive = "median"
faust = { ar = "sc.median({n}, {in})", kr = "sc.median_kr({n}, {in})" }
compare = "waveform"
tol = 1e-6
case = "case_Median"
```

## case.part

```
	// Median: odd and even lengths (even: the upper middle), the 32 clip; kr over block values
	SynthDef(\case_Median, { Out.ar(0, [Median.ar(3, in.value), Median.ar(8, in.value), Median.ar(40, in.value),
		K2A.ar(Median.kr(5, Latch.kr(in.value, Impulse.kr(200))))]) }),
```

