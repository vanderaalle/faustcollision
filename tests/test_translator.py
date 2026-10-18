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
    g = graph(UGen(2, "Gendy1", "ar", 0, [Ref(1, 0)], ["ar"]))
    with pytest.raises(TranslationError, match="unmapped UGen class Gendy1"):
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
    g = graph(UGen(2, "Saw", "kr", 0, [Const(1.0)], ["kr"]))
    with pytest.raises(TranslationError, match="Saw.kr"):
        translate(g, {})


def test_control_without_spec_is_an_error():
    ctl = UGen(2, "Control", "kr", 0, [], ["kr"])
    mul = UGen(3, "BinaryOpUGen", "ar", 2, [Ref(1, 0), Ref(2, 0)], ["ar"])
    g = graph(ctl, mul)
    g.param_names = {0: "gain"}
    with pytest.raises(TranslationError, match="'gain' is used but has no spec"):
        translate(g, {"specs": {}})
