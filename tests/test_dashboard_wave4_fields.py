"""Tests for Wave 4 dashboard fields: tft_prob, advisor_regime, model_kind_used."""

from __future__ import annotations

import pytest


def _make_result(**overrides):
    """Minimal valid RecommendationResult dict for bridge tests."""
    base = {
        "ticker": "AAPL", "track": "S", "verdict": "AMBER_WATCHLIST",
        "recommendation_rank_score": 60.0, "candidate_label": "test",
        "screening_output_only": True, "latest_close": 150.0,
        "entry": 100.0, "stop": 95.0, "tp1": 105.0, "tp2": 110.0,
        "stop_pct": -5.0, "tp2_pct": 10.0, "risk_reward": 2.0,
        "risk_budget_pct": 0.5, "max_position_pct": 10.0,
        "suggested_quantity": 0, "suggested_position_value": 0.0,
        "direction_prob": 0.6, "probability": 0.6, "expected_value_pct": 2.0,
        "model_accuracy": 0.55, "model_auc": 0.58, "oof_coverage": 0.9,
        "backtest_return_pct": 5.0, "backtest_sharpe": 1.0, "backtest_sortino": 1.2,
        "backtest_mdd_pct": -10.0, "profit_factor": 1.5,
        "avg_dollar_volume_20d": 1_000_000.0, "volume_ratio_20d": 1.0,
        "market_regime_score": 65.0, "return_20d_pct": 2.0,
        "return_60d_pct": 5.0, "drawdown_252d_pct": -8.0,
        "confirmations_passed": 5, "confirmations_total": 8,
        "validations": [], "reasons": [], "generated_at_utc": "2026-05-29T12:00:00",
        "backtest_honesty": None, "raw_score": 60.0,
    }
    base.update(overrides)
    return base


def _make_snapshot(result):
    return {
        "schema_version": "dashboard_snapshot.v1",
        "generated_at": "2026-05-29T12:00:00",
        "results": [result],
        "source_config": {},
    }


# ---------------------------------------------------------------------------
# RecommendationResult additive compatibility
# ---------------------------------------------------------------------------

def test_recommendation_result_new_fields_default_none():
    """Creating RecommendationResult without new fields → defaults to None."""
    from stock_rtx4060.recommendation_engine import RecommendationResult, ValidationCheck
    r = RecommendationResult(
        ticker="AAPL", track="S", verdict="AMBER_WATCHLIST",
        recommendation_rank_score=60.0, candidate_label="test",
        screening_output_only=True, latest_close=150.0,
        entry=100.0, stop=95.0, tp1=105.0, tp2=110.0,
        stop_pct=-5.0, tp2_pct=10.0, risk_reward=2.0,
        risk_budget_pct=0.5, max_position_pct=10.0,
        suggested_quantity=0, suggested_position_value=0.0,
        direction_prob=0.6, expected_value_pct=2.0,
        model_accuracy=0.55, model_auc=0.58, oof_coverage=0.9,
        backtest_return_pct=5.0, backtest_sharpe=1.0, backtest_sortino=1.2,
        backtest_mdd_pct=-10.0, profit_factor=1.5,
        avg_dollar_volume_20d=1_000_000.0, volume_ratio_20d=1.0,
        market_regime_score=65.0, return_20d_pct=2.0, return_60d_pct=5.0,
        drawdown_252d_pct=-8.0, confirmations_passed=5, confirmations_total=8,
        validations=[], reasons=[], generated_at_utc="2026-05-29T12:00:00",
    )
    assert r.tft_prob is None
    assert r.advisor_regime is None
    assert r.model_kind_used is None


def test_recommendation_result_wave4_fields_in_to_dict():
    """tft_prob, advisor_regime, model_kind_used appear in to_dict()."""
    from stock_rtx4060.recommendation_engine import RecommendationResult
    r = RecommendationResult(
        ticker="AAPL", track="S", verdict="AMBER_WATCHLIST",
        recommendation_rank_score=60.0, candidate_label="test",
        screening_output_only=True, latest_close=150.0,
        entry=100.0, stop=95.0, tp1=105.0, tp2=110.0,
        stop_pct=-5.0, tp2_pct=10.0, risk_reward=2.0,
        risk_budget_pct=0.5, max_position_pct=10.0,
        suggested_quantity=0, suggested_position_value=0.0,
        direction_prob=0.6, expected_value_pct=2.0,
        model_accuracy=0.55, model_auc=0.58, oof_coverage=0.9,
        backtest_return_pct=5.0, backtest_sharpe=1.0, backtest_sortino=1.2,
        backtest_mdd_pct=-10.0, profit_factor=1.5,
        avg_dollar_volume_20d=1_000_000.0, volume_ratio_20d=1.0,
        market_regime_score=65.0, return_20d_pct=2.0, return_60d_pct=5.0,
        drawdown_252d_pct=-8.0, confirmations_passed=5, confirmations_total=8,
        validations=[], reasons=[], generated_at_utc="2026-05-29T12:00:00",
        tft_prob=0.71, advisor_regime="risk_off", model_kind_used="lightgbm",
    )
    d = r.to_dict()
    assert d["tft_prob"] == pytest.approx(0.71)
    assert d["advisor_regime"] == "risk_off"
    assert d["model_kind_used"] == "lightgbm"


# ---------------------------------------------------------------------------
# dashboard_bridge passthrough
# ---------------------------------------------------------------------------

def test_bridge_passes_tft_prob_through():
    """dashboard_bridge includes tft_prob in candidate output."""
    from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
    result = _make_result(tft_prob=0.71, advisor_regime="risk_off", model_kind_used="lightgbm")
    snapshot = build_dashboard_snapshot(_make_snapshot(result))
    c = snapshot["results"][0]
    assert c["tft_prob"] == pytest.approx(0.71)
    assert c["advisor_regime"] == "risk_off"
    assert c["model_kind_used"] == "lightgbm"


def test_bridge_null_wave4_fields_safe():
    """Missing new fields → None in snapshot (no KeyError)."""
    from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
    result = _make_result()  # no wave4 fields
    snapshot = build_dashboard_snapshot(_make_snapshot(result))
    c = snapshot["results"][0]
    assert c.get("tft_prob") is None
    assert c.get("advisor_regime") is None
    assert c.get("model_kind_used") is None


def test_bridge_regime_values_preserved():
    """All 3 regime values flow through correctly."""
    from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot
    for regime in ("risk_on", "neutral", "risk_off"):
        result = _make_result(advisor_regime=regime)
        snapshot = build_dashboard_snapshot(_make_snapshot(result))
        assert snapshot["results"][0]["advisor_regime"] == regime
