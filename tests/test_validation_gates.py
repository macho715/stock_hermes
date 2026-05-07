"""Tests for validation_gates.py — pure-function coverage."""

from __future__ import annotations

import pytest

from stock_rtx4060.validation_gates import (
    GateResult,
    g01_data_freshness,
    g02_price_crosscheck,
    g03_schema_completeness,
    g04_corp_action_sanity,
    g05_model_health,
    g06_oof_coverage,
    g07_risk_plan,
    g08_backtest_sanity,
    g09_approval,
    g10_audit_evidence,
)


# --- G-01 DATA_FRESHNESS ---

def test_g01_no_metadata_returns_red():
    ev = g01_data_freshness(None)
    assert ev.result == GateResult.RED


def test_g01_krx_fresh_passes():
    ev = g01_data_freshness({"ticker_type": "KRX", "data_freshness_minutes": 100})
    assert ev.result == GateResult.PASS


def test_g01_krx_slightly_stale_returns_amber():
    ev = g01_data_freshness({"ticker_type": "KRX", "data_freshness_minutes": 2000})
    assert ev.result == GateResult.AMBER


def test_g01_krx_very_stale_returns_red():
    ev = g01_data_freshness({"ticker_type": "KRX", "data_freshness_minutes": 5000})
    assert ev.result == GateResult.RED


def test_g01_nyse_fresh_passes():
    ev = g01_data_freshness({"ticker_type": "NYSE", "data_freshness_minutes": 500})
    assert ev.result == GateResult.PASS


def test_g01_nyse_stale_returns_red():
    ev = g01_data_freshness({"ticker_type": "NYSE", "data_freshness_minutes": 2000})
    assert ev.result == GateResult.RED


def test_g01_unknown_market_returns_red():
    ev = g01_data_freshness({"ticker_type": "UNKNOWN", "data_freshness_minutes": 100})
    assert ev.result == GateResult.RED


# --- G-02 PRICE_CROSSCHECK ---

def test_g02_both_none_returns_amber():
    ev = g02_price_crosscheck(None, None)
    assert ev.result == GateResult.AMBER


def test_g02_zero_price_returns_red():
    ev = g02_price_crosscheck(0.0, 100.0)
    assert ev.result == GateResult.RED


def test_g02_close_prices_passes():
    ev = g02_price_crosscheck(100.0, 100.5)
    assert ev.result == GateResult.PASS


def test_g02_medium_delta_returns_amber():
    ev = g02_price_crosscheck(100.0, 102.5)
    assert ev.result == GateResult.AMBER


def test_g02_large_delta_returns_red():
    ev = g02_price_crosscheck(100.0, 110.0)
    assert ev.result == GateResult.RED


# --- G-03 SCHEMA_COMPLETENESS ---

GOOD_COLS = ["date", "open", "high", "low", "close", "volume"]


def test_g03_missing_columns_returns_red():
    ev = g03_schema_completeness(100, ["date", "close"])
    assert ev.result == GateResult.RED


def test_g03_too_few_rows_returns_red():
    ev = g03_schema_completeness(10, GOOD_COLS)
    assert ev.result == GateResult.RED


def test_g03_volume_all_zero_returns_red():
    ev = g03_schema_completeness(100, GOOD_COLS, volume_all_zero=True)
    assert ev.result == GateResult.RED


def test_g03_close_invalid_returns_red():
    ev = g03_schema_completeness(100, GOOD_COLS, close_invalid=True)
    assert ev.result == GateResult.RED


def test_g03_valid_data_passes():
    ev = g03_schema_completeness(100, GOOD_COLS)
    assert ev.result == GateResult.PASS


# --- G-04 CORP_ACTION_SANITY ---

def test_g04_single_price_passes():
    ev = g04_corp_action_sanity([100.0])
    assert ev.result == GateResult.PASS


def test_g04_stable_prices_passes():
    ev = g04_corp_action_sanity([100.0, 101.0, 99.0, 100.5])
    assert ev.result == GateResult.PASS


def test_g04_large_drop_returns_amber():
    # 50% drop
    ev = g04_corp_action_sanity([100.0, 50.0])
    assert ev.result == GateResult.AMBER


# --- G-05 MODEL_HEALTH ---

def test_g05_missing_returns_red():
    ev = g05_model_health(None, None)
    assert ev.result == GateResult.RED


def test_g05_good_metrics_passes():
    ev = g05_model_health(auc=0.60, accuracy=0.55)
    assert ev.result == GateResult.PASS


def test_g05_marginal_auc_returns_amber():
    ev = g05_model_health(auc=0.51, accuracy=0.55)
    assert ev.result == GateResult.AMBER


def test_g05_poor_auc_returns_red():
    ev = g05_model_health(auc=0.45, accuracy=0.45)
    assert ev.result == GateResult.RED


# --- G-06 OOF_COVERAGE ---

def test_g06_none_returns_red():
    ev = g06_oof_coverage(None)
    assert ev.result == GateResult.RED


def test_g06_high_coverage_passes():
    ev = g06_oof_coverage(80.0)
    assert ev.result == GateResult.PASS


def test_g06_medium_coverage_returns_amber():
    ev = g06_oof_coverage(60.0)
    assert ev.result == GateResult.AMBER


def test_g06_low_coverage_returns_red():
    ev = g06_oof_coverage(30.0)
    assert ev.result == GateResult.RED


# --- G-07 RISK_PLAN ---

def test_g07_missing_fields_returns_red():
    ev = g07_risk_plan(None, None, None, None)
    assert ev.result == GateResult.RED


def test_g07_invalid_stop_returns_red():
    ev = g07_risk_plan(stop_pct=1.0, tp2_pct=10.0, risk_budget_pct=0.75, risk_reward=2.5)
    assert ev.result == GateResult.RED


def test_g07_valid_track_s_passes():
    ev = g07_risk_plan(stop_pct=-4.0, tp2_pct=10.0, risk_budget_pct=0.75, risk_reward=2.5, track="S")
    assert ev.result == GateResult.PASS


def test_g07_marginal_rr_returns_amber():
    ev = g07_risk_plan(stop_pct=-4.0, tp2_pct=6.0, risk_budget_pct=0.75, risk_reward=1.6, track="S")
    assert ev.result == GateResult.AMBER


def test_g07_below_1_5_rr_returns_amber():
    ev = g07_risk_plan(stop_pct=-4.0, tp2_pct=4.0, risk_budget_pct=0.75, risk_reward=1.0, track="S")
    assert ev.result == GateResult.AMBER


# --- G-08 BACKTEST_SANITY ---

def test_g08_none_returns_amber():
    ev = g08_backtest_sanity(None, None)
    assert ev.result == GateResult.AMBER


def test_g08_good_metrics_passes():
    ev = g08_backtest_sanity(sharpe=1.0, mdd_pct=10.0)
    assert ev.result == GateResult.PASS


def test_g08_high_mdd_returns_red():
    ev = g08_backtest_sanity(sharpe=1.0, mdd_pct=25.0)
    assert ev.result == GateResult.RED


def test_g08_negative_sharpe_returns_amber():
    ev = g08_backtest_sanity(sharpe=-0.3, mdd_pct=10.0)
    assert ev.result == GateResult.AMBER


def test_g08_very_negative_sharpe_returns_amber():
    ev = g08_backtest_sanity(sharpe=-1.0, mdd_pct=10.0)
    assert ev.result == GateResult.AMBER


# --- G-09 APPROVAL ---

def test_g09_any_red_blocked():
    ev = g09_approval(all_gates_pass=False, any_red=True, amber_cleared=False, has_amber=False)
    assert ev.result == GateResult.RED


def test_g09_all_pass_approved():
    ev = g09_approval(all_gates_pass=True, any_red=False, amber_cleared=False, has_amber=False)
    assert ev.result == GateResult.PASS


def test_g09_uncleared_amber_pending():
    ev = g09_approval(all_gates_pass=False, any_red=False, amber_cleared=False, has_amber=True)
    assert ev.result == GateResult.AMBER


def test_g09_cleared_amber_approves():
    ev = g09_approval(all_gates_pass=False, any_red=False, amber_cleared=True, has_amber=True)
    assert ev.result == GateResult.PASS


def test_g09_fallback_returns_amber():
    ev = g09_approval(all_gates_pass=False, any_red=False, amber_cleared=False, has_amber=False)
    assert ev.result == GateResult.AMBER


# --- G-10 AUDIT_EVIDENCE ---

def test_g10_both_events_passes():
    ev = g10_audit_evidence(5, has_provider_event=True, has_recommend_event=True)
    assert ev.result == GateResult.PASS


def test_g10_missing_provider_event_returns_red():
    ev = g10_audit_evidence(1, has_provider_event=False, has_recommend_event=True)
    assert ev.result == GateResult.RED


def test_g10_missing_recommend_event_returns_red():
    ev = g10_audit_evidence(1, has_provider_event=True, has_recommend_event=False)
    assert ev.result == GateResult.RED
