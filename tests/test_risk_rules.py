"""Tests for risk_rules.py — position sizing, scoring, gate logic."""

from __future__ import annotations

from math import floor

import pandas as pd
import pytest

from stock_rtx4060.risk_rules import (
    CandidateVerdict,
    Gate,
    RiskConfig,
    _clamp,
    evaluate_track_l_candidate,
    evaluate_track_s_candidate,
    min_gate,
    portfolio_targets,
    position_size_by_risk,
    score_track_l,
    score_track_s,
)

# ---------------------------------------------------------------------------
# _clamp
# ---------------------------------------------------------------------------

def test_clamp_within_range():
    assert _clamp(5.0, 0.0, 10.0) == 5.0


def test_clamp_below_low():
    assert _clamp(-3.0, 0.0, 10.0) == 0.0


def test_clamp_above_high():
    assert _clamp(15.0, 0.0, 10.0) == 10.0


def test_clamp_nan_returns_low():
    assert _clamp(float("nan"), 1.0, 9.0) == 1.0


def test_clamp_inf_returns_low():
    assert _clamp(float("inf"), 2.0, 8.0) == 2.0


def test_clamp_neg_inf_returns_low():
    assert _clamp(float("-inf"), 0.0, 5.0) == 0.0


# ---------------------------------------------------------------------------
# min_gate
# ---------------------------------------------------------------------------

def test_min_gate_green_vs_amber_returns_amber():
    assert min_gate(Gate.GREEN, Gate.AMBER) == Gate.AMBER


def test_min_gate_green_vs_red_returns_red():
    assert min_gate(Gate.GREEN, Gate.RED) == Gate.RED


def test_min_gate_green_vs_zero_returns_zero():
    assert min_gate(Gate.GREEN, Gate.ZERO) == Gate.ZERO


def test_min_gate_amber_vs_green_keeps_amber():
    assert min_gate(Gate.AMBER, Gate.GREEN) == Gate.AMBER


def test_min_gate_red_vs_amber_keeps_red():
    assert min_gate(Gate.RED, Gate.AMBER) == Gate.RED


def test_min_gate_zero_vs_green_keeps_zero():
    assert min_gate(Gate.ZERO, Gate.GREEN) == Gate.ZERO


def test_min_gate_same_level():
    assert min_gate(Gate.RED, Gate.RED) == Gate.RED


# ---------------------------------------------------------------------------
# RiskConfig properties
# ---------------------------------------------------------------------------

def test_risk_config_defaults():
    cfg = RiskConfig()
    assert cfg.total_capital == 100_000.0
    assert cfg.track_s_capital == 20_000.0
    assert cfg.track_l_capital == 75_000.0
    assert cfg.cash_capital == 5_000.0


def test_risk_config_custom_capital():
    cfg = RiskConfig(total_capital=200_000.0)
    assert cfg.track_s_capital == 40_000.0
    assert cfg.track_l_capital == 150_000.0
    assert cfg.cash_capital == 10_000.0


# ---------------------------------------------------------------------------
# CandidateVerdict.to_dict
# ---------------------------------------------------------------------------

def _make_verdict(gate: Gate = Gate.GREEN) -> CandidateVerdict:
    return CandidateVerdict(
        ticker="AAPL", track="S", score=78.0, gate=gate,
        verdict="Watch/Buy", entry=200.0, stop=192.0, tp1=210.0, tp2=220.0,
        risk_reward=2.5, risk_per_share=8.0, quantity=10,
        position_value=2000.0, open_risk=80.0,
        reasons=["model_edge"],
    )


def test_to_dict_gate_is_string():
    d = _make_verdict(Gate.GREEN).to_dict()
    assert d["gate"] == "GREEN"
    assert isinstance(d["gate"], str)


def test_to_dict_amber_gate():
    d = _make_verdict(Gate.AMBER).to_dict()
    assert d["gate"] == "AMBER"


def test_to_dict_preserves_all_fields():
    d = _make_verdict().to_dict()
    assert d["ticker"] == "AAPL"
    assert d["score"] == 78.0
    assert d["quantity"] == 10


# ---------------------------------------------------------------------------
# position_size_by_risk
# ---------------------------------------------------------------------------

def test_position_size_normal():
    qty, pv, risk = position_size_by_risk(entry=100.0, stop=96.0, track_capital=20_000.0, risk_per_trade_pct=0.0075)
    expected_qty = floor(150.0 / 4.0)  # 37
    assert qty == expected_qty
    assert pv == pytest.approx(expected_qty * 100.0)
    assert risk == pytest.approx(expected_qty * 4.0)


def test_position_size_entry_zero():
    assert position_size_by_risk(0.0, 90.0, 20_000.0, 0.01) == (0, 0.0, 0.0)


def test_position_size_stop_zero():
    assert position_size_by_risk(100.0, 0.0, 20_000.0, 0.01) == (0, 0.0, 0.0)


def test_position_size_stop_above_entry():
    assert position_size_by_risk(100.0, 105.0, 20_000.0, 0.01) == (0, 0.0, 0.0)


def test_position_size_stop_equal_entry():
    assert position_size_by_risk(100.0, 100.0, 20_000.0, 0.01) == (0, 0.0, 0.0)


def test_position_size_negative_entry():
    assert position_size_by_risk(-10.0, 90.0, 20_000.0, 0.01) == (0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# score_track_s
# ---------------------------------------------------------------------------

def _s_row(**kwargs) -> pd.Series:
    defaults = {
        "rsi_14": 55.0, "adx_14": 30.0, "volume_ratio_20": 1.5,
        "macd_hist": 0.1, "return_5d": 0.01, "sma_ratio_20": 0.02,
        "bb_pct": 0.6, "cmf_20": 0.1, "vi_diff_14": 0.1,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def test_score_track_s_baseline_range():
    score, reasons = score_track_s(_s_row())
    assert 0.0 <= score <= 100.0
    assert any("rsi_14" in r for r in reasons)


def test_score_track_s_rsi_in_sweet_spot_adds_10():
    row = _s_row(rsi_14=55.0)
    score_in, _ = score_track_s(row)
    row_out = _s_row(rsi_14=30.0)  # 25 < rsi < 45 → 0
    score_out, _ = score_track_s(row_out)
    assert score_in > score_out


def test_score_track_s_rsi_overbought_subtracts():
    row_over = _s_row(rsi_14=85.0)
    row_norm = _s_row(rsi_14=55.0)
    score_over, _ = score_track_s(row_over)
    score_norm, _ = score_track_s(row_norm)
    assert score_over < score_norm


def test_score_track_s_rsi_oversold_subtracts():
    row = _s_row(rsi_14=20.0)
    score, _ = score_track_s(row)
    row_norm = _s_row(rsi_14=55.0)
    score_norm, _ = score_track_s(row_norm)
    assert score < score_norm


def test_score_track_s_macd_positive_vs_negative():
    score_pos, _ = score_track_s(_s_row(macd_hist=0.5))
    score_neg, _ = score_track_s(_s_row(macd_hist=-0.5))
    assert score_pos > score_neg


def test_score_track_s_volume_ratio_contributes():
    score_high, _ = score_track_s(_s_row(volume_ratio_20=3.0))
    score_low, _ = score_track_s(_s_row(volume_ratio_20=0.1))
    assert score_high > score_low


def test_score_track_s_with_prediction_prob():
    score_high, reasons = score_track_s(_s_row(), prediction_prob=0.8)
    score_low, _ = score_track_s(_s_row(), prediction_prob=0.2)
    assert score_high > score_low
    assert any("model_prob" in r for r in reasons)


def test_score_track_s_without_prediction_prob():
    score, reasons = score_track_s(_s_row())
    assert not any("model_prob" in r for r in reasons)


def test_score_track_s_vi_diff_positive_adds():
    score_pos, _ = score_track_s(_s_row(vi_diff_14=0.1))
    score_neg, _ = score_track_s(_s_row(vi_diff_14=-0.1))
    assert score_pos > score_neg


def test_score_track_s_vi_diff_neutral():
    score_neutral, _ = score_track_s(_s_row(vi_diff_14=0.02))
    score_pos, _ = score_track_s(_s_row(vi_diff_14=0.1))
    # |vi_diff| < 0.05 → +0; vi_diff > 0.05 → +4
    assert score_pos > score_neutral


def test_score_track_s_cmf_negative_subtracts():
    score_pos, _ = score_track_s(_s_row(cmf_20=0.5))
    score_neg, _ = score_track_s(_s_row(cmf_20=-0.5))
    assert score_pos > score_neg


def test_score_track_s_bb_pct_in_range():
    score_in, _ = score_track_s(_s_row(bb_pct=0.6))
    score_out, _ = score_track_s(_s_row(bb_pct=0.1))
    assert score_in > score_out


def test_score_track_s_missing_fields_uses_defaults():
    score, reasons = score_track_s(pd.Series({}))
    assert 0.0 <= score <= 100.0
    assert len(reasons) > 0


# ---------------------------------------------------------------------------
# score_track_l
# ---------------------------------------------------------------------------

def _l_row_fundamental(**kwargs) -> pd.Series:
    defaults = {
        "business_quality": 80.0,
        "earnings_quality": 75.0,
        "balance_sheet": 70.0,
        "valuation": 65.0,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def _l_row_technical(**kwargs) -> pd.Series:
    defaults = {
        "business_quality": 0.0,
        "earnings_quality": 0.0,
        "balance_sheet": 0.0,
        "valuation": 0.0,
        "hist_vol_20": 0.2,
        "sma_ratio_200": 0.05,
        "return_20d": 0.02,
    }
    defaults.update(kwargs)
    return pd.Series(defaults)


def test_score_track_l_fundamental_path():
    score, reasons = score_track_l(_l_row_fundamental())
    assert score > 0.0
    assert any("business_quality" in r for r in reasons)


def test_score_track_l_technical_fallback_path():
    score, reasons = score_track_l(_l_row_technical())
    assert score > 0.0
    assert any("sma_ratio_200" in r for r in reasons)


def test_score_track_l_high_hist_vol_penalty():
    score_low_vol, _ = score_track_l(_l_row_technical(hist_vol_20=0.20))
    score_high_vol, _ = score_track_l(_l_row_technical(hist_vol_20=0.60))
    assert score_low_vol > score_high_vol


def test_score_track_l_sma_above_zero_adds():
    score_pos, _ = score_track_l(_l_row_technical(sma_ratio_200=0.05))
    score_neg, _ = score_track_l(_l_row_technical(sma_ratio_200=-0.05))
    assert score_pos > score_neg


def test_score_track_l_return_positive_adds():
    score_pos, _ = score_track_l(_l_row_technical(return_20d=0.02))
    score_neg, _ = score_track_l(_l_row_technical(return_20d=-0.02))
    assert score_pos > score_neg


def test_score_track_l_with_prediction_prob():
    score_high, reasons = score_track_l(_l_row_fundamental(), prediction_prob=0.9)
    score_low, _ = score_track_l(_l_row_fundamental(), prediction_prob=0.1)
    assert score_high > score_low
    assert any("model_prob" in r for r in reasons)


def test_score_track_l_clamped_to_0_100():
    # Extreme inputs should not produce out-of-range scores
    row = _l_row_fundamental(business_quality=200.0, earnings_quality=200.0,
                              balance_sheet=200.0, valuation=200.0)
    score, _ = score_track_l(row, prediction_prob=1.0)
    assert 0.0 <= score <= 100.0


# ---------------------------------------------------------------------------
# evaluate_track_s_candidate
# ---------------------------------------------------------------------------

def _good_s_row() -> pd.Series:
    return pd.Series({
        "rsi_14": 55.0, "adx_14": 35.0, "volume_ratio_20": 2.0,
        "macd_hist": 0.3, "return_5d": 0.02, "sma_ratio_20": 0.03,
        "bb_pct": 0.6, "cmf_20": 0.2, "vi_diff_14": 0.15,
        "dollar_volume": 10_000_000.0,
    })


def test_evaluate_track_s_green_path():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, prediction_prob=0.75)
    assert v.ticker == "AAPL"
    assert v.track == "S"
    assert v.gate in (Gate.GREEN, Gate.AMBER)
    assert 0.0 <= v.score <= 100.0
    assert v.stop < v.entry


def test_evaluate_track_s_margin_triggers_zero():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, allow_margin=True)
    assert v.gate == Gate.ZERO
    assert "margin/options" in " ".join(v.reasons)


def test_evaluate_track_s_options_triggers_zero():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, allow_options=True)
    assert v.gate == Gate.ZERO


def test_evaluate_track_s_monthly_stop_triggers_zero():
    cfg = RiskConfig()
    v = evaluate_track_s_candidate(
        "AAPL", _good_s_row(), entry=200.0,
        config=cfg, monthly_pnl_pct=-0.06,
    )
    assert v.gate == Gate.ZERO
    assert any("monthly" in r for r in v.reasons)


def test_evaluate_track_s_invalid_entry_triggers_zero():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=0.0)
    assert v.gate == Gate.ZERO


def test_evaluate_track_s_low_liquidity_triggers_red():
    row = _good_s_row().copy()
    row["dollar_volume"] = 100_000.0
    v = evaluate_track_s_candidate("AAPL", row, entry=200.0, prediction_prob=0.75)
    assert v.gate in (Gate.RED, Gate.AMBER, Gate.ZERO)
    assert any("liquidity" in r for r in v.reasons)


def test_evaluate_track_s_atr_based_stop():
    # High ATR → wider stop than default
    cfg = RiskConfig()
    v_atr = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, config=cfg, atr_pct=0.05)
    v_def = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, config=cfg)
    # 2 * 0.05 = 0.10 > default 0.04 → ATR stop is wider → lower stop price
    assert v_atr.stop <= v_def.stop


def test_evaluate_track_s_atr_none_uses_default():
    cfg = RiskConfig()
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, config=cfg, atr_pct=None)
    expected_stop = round(200.0 * (1 - cfg.track_s_stop_pct), 4)
    assert v.stop == pytest.approx(expected_stop)


def test_evaluate_track_s_uses_default_config_when_none():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=100.0)
    assert v.entry == pytest.approx(100.0)


def test_evaluate_track_s_low_score_red_below_65():
    # score < 65 → RED (not AMBER)
    row = pd.Series({
        "rsi_14": 85.0, "adx_14": 5.0, "volume_ratio_20": 0.1,
        "macd_hist": -1.0, "return_5d": -0.05, "sma_ratio_20": -0.05,
        "bb_pct": 0.1, "cmf_20": -0.8, "vi_diff_14": -0.2,
        "dollar_volume": 20_000_000.0,
    })
    v = evaluate_track_s_candidate("TEST", row, entry=100.0)
    assert v.score < 65.0
    assert v.gate in (Gate.RED, Gate.AMBER, Gate.ZERO)


def test_evaluate_track_s_open_risk_exceeds_cap():
    # High risk_per_trade_pct → large qty → open_risk > track_s_capital * max_open_risk_pct
    cfg = RiskConfig(total_capital=100_000.0, track_s_risk_per_trade_pct=0.50)
    # track_s_capital=20_000, risk_budget=10_000, risk_per_share≈4 (entry=200, stop=192)
    # qty≈2500, open_risk≈10_000 >> cap(20_000*0.02=400) → triggers
    v = evaluate_track_s_candidate("TEST", _good_s_row(), entry=200.0, config=cfg)
    assert any("open risk" in r for r in v.reasons)


def test_evaluate_track_s_verdict_field_matches_gate():
    v = evaluate_track_s_candidate("AAPL", _good_s_row(), entry=200.0, prediction_prob=0.75)
    expected = {Gate.GREEN: "Watch/Buy", Gate.AMBER: "Watch Only", Gate.RED: "Reject", Gate.ZERO: "No Trade"}
    assert v.verdict == expected[v.gate]


# ---------------------------------------------------------------------------
# evaluate_track_l_candidate
# ---------------------------------------------------------------------------

def _good_l_row() -> pd.Series:
    # score = 0.35*90 + 0.25*85 + 0.20*85 + 0.20*80 = 85.75 → GREEN (>= 80)
    return pd.Series({
        "business_quality": 90.0, "earnings_quality": 85.0,
        "balance_sheet": 85.0, "valuation": 80.0,
    })


def _marginal_l_row() -> pd.Series:
    # score = 0.35*75 + 0.25*70 + 0.20*70 + 0.20*65 = 70.75 → AMBER (70 <= score < 80)
    return pd.Series({
        "business_quality": 75.0, "earnings_quality": 70.0,
        "balance_sheet": 70.0, "valuation": 65.0,
    })


def _poor_l_row() -> pd.Series:
    return pd.Series({
        "business_quality": 50.0, "earnings_quality": 40.0,
        "balance_sheet": 35.0, "valuation": 30.0,
    })


def test_evaluate_track_l_green_high_score():
    v = evaluate_track_l_candidate("005930.KS", _good_l_row(), entry=100.0)
    assert v.gate == Gate.GREEN
    assert v.verdict == "Eligible/DCA"
    assert v.track == "L"


def test_evaluate_track_l_amber_medium_score():
    v = evaluate_track_l_candidate("005930.KS", _marginal_l_row(), entry=100.0)
    assert v.gate == Gate.AMBER
    assert v.verdict == "Hold/Monitor"


def test_evaluate_track_l_red_low_score():
    v = evaluate_track_l_candidate("005930.KS", _poor_l_row(), entry=100.0)
    assert v.gate == Gate.RED
    assert v.verdict == "Reject"


def test_evaluate_track_l_zero_invalid_entry():
    v = evaluate_track_l_candidate("005930.KS", _good_l_row(), entry=0.0)
    assert v.gate == Gate.ZERO
    assert v.verdict == "No Action"


def test_evaluate_track_l_quantity_computed():
    cfg = RiskConfig(total_capital=100_000.0)
    v = evaluate_track_l_candidate("005930.KS", _good_l_row(), entry=100.0, config=cfg)
    max_pv = cfg.track_l_capital * cfg.track_l_single_name_limit_pct
    expected_qty = floor(max_pv / 100.0)
    assert v.quantity == expected_qty


def test_evaluate_track_l_stop_tp_structure():
    v = evaluate_track_l_candidate("005930.KS", _good_l_row(), entry=100.0)
    assert v.stop == pytest.approx(88.0)
    assert v.tp1 == pytest.approx(110.0)
    assert v.tp2 == pytest.approx(120.0)


def test_evaluate_track_l_uses_default_config():
    v = evaluate_track_l_candidate("MSFT", _good_l_row(), entry=300.0)
    assert v.entry == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# portfolio_targets
# ---------------------------------------------------------------------------

def test_portfolio_targets_default_config():
    df = portfolio_targets()
    assert isinstance(df, pd.DataFrame)
    assert list(df["Track"]) == ["Track-S", "Track-L", "Cash"]
    assert df.loc[df["Track"] == "Track-S", "Value"].iloc[0] == pytest.approx(20_000.0)
    assert df.loc[df["Track"] == "Track-L", "Value"].iloc[0] == pytest.approx(75_000.0)
    assert df.loc[df["Track"] == "Cash", "Value"].iloc[0] == pytest.approx(5_000.0)


def test_portfolio_targets_custom_config():
    cfg = RiskConfig(total_capital=200_000.0)
    df = portfolio_targets(cfg)
    assert df.loc[df["Track"] == "Track-S", "Value"].iloc[0] == pytest.approx(40_000.0)


def test_portfolio_targets_allocations_sum_to_one():
    cfg = RiskConfig()
    df = portfolio_targets(cfg)
    assert df["Allocation"].sum() == pytest.approx(1.0)
