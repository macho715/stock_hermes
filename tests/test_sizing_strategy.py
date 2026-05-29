import numpy as np
import pytest

from stock_rtx4060.sizing import (
    CRISIS,
    AutoSizingRouter,
    CalibBook,
    GlobalCMRS,
    HorizonScore,
    MondrianCMRS,
    coverage_honesty_gate,
    make_sizer,
)


def _book(calm=0.01, crisis=0.05, n=250, seed=0):
    rng = np.random.default_rng(seed)
    mk = lambda s: {h: np.abs(rng.normal(0, s, n)) for h in ("1d", "5d", "20d")}
    return CalibBook({"CALM": mk(calm), CRISIS: mk(crisis)}, mk((calm + crisis) / 2))


def _hs():
    return [
        HorizonScore("1d", 0.05),
        HorizonScore("5d", 0.06),
        HorizonScore("20d", 0.05),
    ]


@pytest.mark.parametrize("kind", ["global", "mondrian", "auto"])
def test_same_output_contract(kind):
    result = make_sizer(kind).size(_hs(), _book(), "CALM", {CRISIS: 0.0})
    assert 0.0 <= result.size_mult <= 1.0
    assert result.screening_output_only is True
    assert result.coverage_target == pytest.approx(0.9)


@pytest.mark.parametrize("kind", ["global", "mondrian", "auto"])
def test_empty_input(kind):
    assert make_sizer(kind).size([], _book(), "CALM", {CRISIS: 0.5}).size_mult == 0.0


@pytest.mark.parametrize("kind", ["global", "mondrian", "auto"])
def test_downgrade_only_invariant(kind):
    result = make_sizer(kind).size(_hs(), _book(), CRISIS, {CRISIS: 0.9})
    assert result.size_mult <= 1.0


def test_auto_picks_mondrian_when_buckets_full():
    result = make_sizer("auto").size(_hs(), _book(n=250), "CALM", {CRISIS: 0.0})
    assert result.strategy_used == "auto->mondrian"


def test_auto_falls_back_to_global_when_thin():
    book = _book(n=250)
    book.by_regime["THIN"] = {
        h: np.abs(np.random.default_rng(2).normal(0, 0.01, 5))
        for h in ("1d", "5d", "20d")
    }
    result = make_sizer("auto").size(_hs(), book, "THIN", {CRISIS: 0.0})
    assert result.strategy_used == "auto->global"


def test_unknown_regime_mondrian_uses_fallback():
    result = MondrianCMRS().size(_hs(), _book(), "MARS", {CRISIS: 0.0})
    assert all(value == "fallback_global" for value in result.sources.values())


def test_strategy_classes_expose_names():
    assert GlobalCMRS().name == "global"
    assert MondrianCMRS().name == "mondrian"
    assert AutoSizingRouter().name == "auto"


def test_make_sizer_rejects_unknown_kind():
    with pytest.raises(ValueError):
        make_sizer("quantum")


def test_crisis_regime_downgrades_size():
    calm = make_sizer("mondrian").size(_hs(), _book(), "CALM", {CRISIS: 0.0}).size_mult
    crisis = make_sizer("mondrian").size(_hs(), _book(), CRISIS, {CRISIS: 0.8}).size_mult
    assert crisis < calm


def test_disagreement_reduces_agreement():
    hs = [
        HorizonScore("1d", 0.05),
        HorizonScore("5d", -0.05),
        HorizonScore("20d", 0.05),
    ]
    assert make_sizer("auto").size(hs, _book(), "CALM", {CRISIS: 0.0}).agreement < 1.0


def test_no_calibration_yields_zero():
    assert GlobalCMRS().size(_hs(), CalibBook({}, {}), "CALM", {CRISIS: 0.0}).size_mult == 0.0


def test_coverage_gate_pass():
    hits = np.ones(1000)
    hits[:80] = 0
    assert coverage_honesty_gate(hits, alpha=0.1).status == "PASS"


def test_coverage_gate_amber():
    hits = np.ones(1000)
    hits[:170] = 0
    assert coverage_honesty_gate(hits, alpha=0.1).status == "AMBER"


def test_coverage_gate_zero_collapse():
    hits = np.ones(1000)
    hits[:400] = 0
    assert coverage_honesty_gate(hits, alpha=0.1).status == "ZERO"


def test_coverage_gate_empty():
    result = coverage_honesty_gate(np.array([]), alpha=0.1)
    assert result.status == "ZERO"
    assert result.n == 0
