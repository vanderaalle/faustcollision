"""Translator rules that need no audio: fail loudly, never guess."""
import pytest

from translator.codegen import TranslationError, translate
from translator.scsyndef import Const, Ref, SynthDef, UGen

SOUNDIN = [UGen(0, "NumOutputBuses", "ir", 0, [], ["ir"]), UGen(1, "In", "ar", 0, [Ref(0, 0)], ["ar"])]


def graph(*ugens):
    body = SOUNDIN + list(ugens)
    out = UGen(len(body), "Out", "ar", 0, [Const(0.0), Ref(len(body) - 1, 0)], [])
    return SynthDef("t", [], [], {}, body + [out])


def test_unmapped_ugen_names_the_class():
    g = graph(UGen(2, "NoSuchUGen", "ar", 0, [Ref(1, 0)], ["ar"]))  # never mapped
    with pytest.raises(TranslationError, match="unmapped UGen class NoSuchUGen"):
        translate(g, {})


def test_unmapped_operator_names_the_index():
    g = graph(UGen(2, "BinaryOpUGen", "ar", 60, [Ref(1, 0), Const(2.0)], ["ar"]))  # no such operator
    with pytest.raises(TranslationError, match="special index 60"):
        translate(g, {})


def test_require_violation_is_an_error():
    g = graph(UGen(2, "MoogFF", "ar", 0, [Ref(1, 0), Const(1000.0), Const(2.0), Const(1.0)], ["ar"]))
    with pytest.raises(TranslationError, match="reset"):
        translate(g, {})


def test_unmapped_rate_is_an_error():
    g = graph(UGen(2, "Formant", "kr", 0, [Const(440.0), Const(1760.0), Const(880.0)], ["kr"]))
    with pytest.raises(TranslationError, match="Formant.kr"):
        translate(g, {})


def test_control_without_spec_is_an_error():
    ctl = UGen(2, "Control", "kr", 0, [], ["kr"])
    mul = UGen(3, "BinaryOpUGen", "ar", 2, [Ref(1, 0), Ref(2, 0)], ["ar"])
    g = graph(ctl, mul)
    g.param_names = {0: "gain"}
    with pytest.raises(TranslationError, match="'gain' is used but has no spec"):
        translate(g, {"specs": {}})


# One Faust voice per possible grain: the default maxGrains (512) does not compile.
def test_grain_voices_beyond_the_limit_are_an_error():
    g = graph(UGen(2, "GrainSin", "ar", 0, [Const(0.0), Const(1.0), Const(440.0), Const(0.0), Const(-1.0), Const(512.0)], ["ar"]))
    with pytest.raises(TranslationError, match="maxGrains <= 65"):
        translate(g, {})


# doneAction 2 frees the synth (every output stops); other done actions act on other nodes.
def test_done_action_other_than_0_or_2_is_an_error():
    g = graph(UGen(2, "Line", "ar", 0, [Const(0.0), Const(1.0), Const(0.1), Const(1.0)], ["ar"]))
    with pytest.raises(TranslationError, match="doneAction must be the constant 0 or 2"):
        translate(g, {})


# Excluded by design (translator/excluded.toml): refused with the reason, never "unmapped".
def test_excluded_class_states_the_reason():
    g = graph(UGen(2, "MouseX", "kr", 0, [Const(0.0), Const(1.0), Const(0.0), Const(0.2)], ["kr"]))
    with pytest.raises(TranslationError, match="MouseX: excluded by design .user interface"):
        translate(g, {})


def test_excluded_classes_are_not_mapped():
    import tomllib
    from translator.codegen import EXCLUDED, load_table
    with open(EXCLUDED, "rb") as f:
        ex = tomllib.load(f)
    assert not set(ex["classes"]) & set(load_table()), "a class is both mapped and excluded"
    assert set(ex["classes"].values()) <= set(ex["reasons"])


# Rejections with a reason (sc-findings 21, 22; not causal): scsynth reads garbage or
# computes from the current audio block.
def test_ar_input_of_constant_is_rejected():
    g = graph(UGen(2, "Wrap", "ar", 0, [Const(0.3), Const(0.0), Const(1.0)], ["ar"]))
    with pytest.raises(TranslationError, match="must be audio rate"):
        translate(g, {})


def test_linexp_half_audio_range_is_rejected():
    g = graph(UGen(2, "LinExp", "ar", 0, [Ref(1, 0), Const(0.0), Ref(1, 0), Const(1.0), Const(10.0)], ["ar"]))
    with pytest.raises(TranslationError, match="sc-findings 22"):
        translate(g, {})


def test_t2k_is_rejected_as_not_causal():
    g = graph(UGen(2, "T2K", "kr", 0, [Ref(1, 0)], ["kr"]), UGen(3, "K2A", "ar", 0, [Ref(2, 0)], ["ar"]))
    with pytest.raises(TranslationError, match="not ported"):
        translate(g, {})


def test_peak_kr_of_audio_is_rejected():
    g = graph(UGen(2, "Peak", "kr", 0, [Ref(1, 0), Const(0.0)], ["kr"]), UGen(3, "K2A", "ar", 0, [Ref(2, 0)], ["ar"]))
    with pytest.raises(TranslationError, match="Peak.kr of an audio input"):
        translate(g, {})

