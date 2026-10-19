# SampleRate, SampleDur, ControlRate, ControlDur, RadiansPerSample, SubsampleOffset

Prepared, not yet applied or tested.

C (DelayUGens.cpp:434-448): ir UGens whose constructor writes one value, a double cast to
float: mWorld->mSampleRate; mBufRate.mSampleRate (SR / 64); mFullRate.mSampleDur
(1 / SR); mFullRate.mBufDuration (64 / SR); mFullRate.mRadiansPerSample (2 pi / SR);
mParent->mSubsampleOffset.

The translator fixes SR at translation time (derive.SR = 48000), so each is a float
constant: float(48000), float(750), float(1/48000), float(64/48000), float(2 pi / 48000).
SubsampleOffset: 0 for a synth that starts on a block boundary (always, outside scsynth's
OffsetOut-scheduled synths in NRT/OSC bundles): map to 0.0 and say so in the entry.

## derive.py
```
def server_info(c):
    """DelayUGens.cpp:434-448: double values written once, cast to float."""
    return {"sr": repr(float(f32(SR))), "cr": repr(float(f32(SR / 64))),
            "sdur": repr(float(f32(1.0 / SR))), "cdur": repr(float(f32(64.0 / SR))),
            "rps": repr(float(f32(2.0 * math.pi / SR)))}
```

## mapping.toml
```
[SampleRate]
tier = "direct"
derive = "server_info"
faust = { ir = "{sr}" }
compare = "waveform"
tol = 0
case = "case_ServerInfo"
# likewise SampleDur ({sdur}), ControlRate ({cr}), ControlDur ({cdur}),
# RadiansPerSample ({rps}); SubsampleOffset = "0.0" (a block-aligned start)
```
Check how codegen handles ir UGens (NumOutputBuses has a kind; the rate key may be
"ir"), and whether derive runs without constant inputs (consts = {} is fine).

## case
```
SynthDef(\case_ServerInfo, { Out.ar(0, DC.ar([SampleRate.ir / 48000, SampleDur.ir * 48000,
    ControlRate.ir / 750, ControlDur.ir * 750, RadiansPerSample.ir, SubsampleOffset.ir])) })
```
(scaled to ~1 so the waveform score is meaningful; tol 0: exact constants.)
