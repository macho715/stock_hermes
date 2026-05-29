import numpy as np

from stock_rtx4060.sizing import CRISIS, CalibBook, HorizonScore
from stock_rtx4060.sizing.integration import apply_sizing, snapshot_additive_fields


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


def _candidate(verdict="ELIGIBLE_RECOMMENDATION", rank=1.0, raw=0.7):
    return {
        "ticker": "SYNTH-A",
        "verdict": verdict,
        "recommendation_rank_score": rank,
        "raw_score": raw,
    }


def test_raw_score_preserved():
    candidate = _candidate(raw=0.7)
    app = apply_sizing(candidate, _hs(), _book(), "CALM", {CRISIS: 0.0})
    assert candidate["raw_score"] == 0.7
    assert app.audit_event["raw_score_unchanged"] is True


def test_rank_score_downgrade_only():
    app = apply_sizing(_candidate(rank=1.0), _hs(), _book(), "CALM", {CRISIS: 0.0})
    assert 0.0 <= app.size_multiplier <= 1.0
    assert app.new_rank_score <= 1.0


def test_non_downgradeable_verdict_untouched():
    app = apply_sizing(_candidate(verdict="RED_BLOCKED", rank=1.0), _hs(), _book(), "CALM", {CRISIS: 0.0})
    assert app.size_multiplier == 1.0
    assert app.new_rank_score == 1.0
    assert app.audit_event["applied"] is False


def test_zero_verdict_untouched():
    app = apply_sizing(_candidate(verdict="ZERO_NO_DATA", rank=0.8), _hs(), _book(), CRISIS, {CRISIS: 0.9})
    assert app.size_multiplier == 1.0
    assert app.new_rank_score == 0.8


def test_screening_flag():
    app = apply_sizing(_candidate(), _hs(), _book(), "CALM", {CRISIS: 0.0})
    assert app.screening_output_only is True
    assert app.audit_event["screening_output_only"] is True


def test_snapshot_additive_fields_include_coverage():
    app = apply_sizing(
        _candidate(),
        _hs(),
        _book(),
        "CALM",
        {CRISIS: 0.0},
        coverage_status="PASS",
    )
    fields = snapshot_additive_fields(app)
    assert set(fields) == {"size_multiplier", "sizing_strategy_used", "sizing_coverage_status"}
    assert fields["sizing_coverage_status"] == "PASS"


def test_audit_event_name_is_new():
    app = apply_sizing(_candidate(), _hs(), _book(), "CALM", {CRISIS: 0.0})
    assert app.audit_event["event"] == "sizing_strategy_selected"
    assert app.audit_event["event"] != "backtest_honesty_summary"


def test_structural_no_upgrade_possible():
    for regime, probs in [("CALM", {CRISIS: 0.0}), (CRISIS, {CRISIS: 0.9})]:
        app = apply_sizing(_candidate(rank=1.0), _hs(), _book(), regime, probs)
        assert app.new_rank_score <= 1.0


def test_crisis_downgrades_more_than_calm():
    calm = apply_sizing(_candidate(), _hs(), _book(), "CALM", {CRISIS: 0.0}).new_rank_score
    crisis = apply_sizing(_candidate(), _hs(), _book(), CRISIS, {CRISIS: 0.9}).new_rank_score
    assert crisis <= calm
