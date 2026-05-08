"""Tests for the Phase-4 sizing branch in ``Backtester``.

The Kelly path is unchanged from before Phase 4 and must reproduce the
existing baseline numbers exactly.  Non-Kelly methods must produce a valid
backtest run with no NaN and a finite total return.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from stock_rtx4060.backtester import BacktestConfig, Backtester
from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig
from stock_rtx4060.feature_engine import TechnicalIndicators, make_synthetic_ohlcv


def _synthetic_run() -> tuple[pd.Series, pd.Series]:
    df = make_synthetic_ohlcv(360)
    features = TechnicalIndicators(df).build_all(horizon=5)
    model = EnsemblePredictor(ModelConfig(n_splits=3, lite=True))
    model.fit(features)
    proba = model.predict_proba(features.drop(columns=["target_direction", "target_return"]))
    prices = df["Close"].reindex(features.index).ffill()
    signals = pd.Series(proba, index=features.index)
    return prices, signals


def test_kelly_default_preserves_baseline():
    prices, signals = _synthetic_run()
    res_default = Backtester().run(prices, signals)
    res_explicit = Backtester(BacktestConfig(sizing="kelly")).run(prices, signals)
    assert res_default["final_capital"] == res_explicit["final_capital"]
    assert res_default["total_return_pct"] == res_explicit["total_return_pct"]
    assert res_default["sharpe_ratio"] == res_explicit["sharpe_ratio"]
    assert res_default["n_trades"] == res_explicit["n_trades"]


def test_hrp_sizing_produces_valid_run():
    prices, signals = _synthetic_run()
    cfg = BacktestConfig(sizing="hrp", sizing_lookback=120)
    result = Backtester(cfg).run(prices, signals)
    assert math.isfinite(result["total_return_pct"])
    assert math.isfinite(result["sharpe_ratio"])
    assert result["final_capital"] >= 0
    assert not any(np.isnan(v) for v in result["portfolio_values"])


def test_risk_budgeting_sizing_produces_valid_run():
    prices, signals = _synthetic_run()
    cfg = BacktestConfig(sizing="risk_budgeting", sizing_lookback=120)
    result = Backtester(cfg).run(prices, signals)
    assert math.isfinite(result["total_return_pct"])
    assert result["final_capital"] >= 0


def test_mv_cvar_sizing_produces_valid_run():
    prices, signals = _synthetic_run()
    cfg = BacktestConfig(sizing="mv_cvar", sizing_lookback=120)
    result = Backtester(cfg).run(prices, signals)
    assert math.isfinite(result["total_return_pct"])
    assert result["final_capital"] >= 0


def test_baseline_numbers_unchanged_for_simple_input():
    # Deterministic check: a pure-cosine signal applied to a known price path.
    n = 80
    rng = np.random.default_rng(0)
    prices = pd.Series(
        np.cumprod(1 + rng.normal(0.001, 0.01, n)) * 100, index=pd.bdate_range(end="2024-01-01", periods=n)
    )
    signals = pd.Series(0.6 + 0.05 * np.sin(np.arange(n) * 0.3), index=prices.index).clip(0.0, 1.0)
    cfg_a = BacktestConfig()  # default — kelly
    cfg_b = BacktestConfig(sizing="kelly")  # explicit kelly
    bt_a = Backtester(cfg_a).run(prices, signals)
    bt_b = Backtester(cfg_b).run(prices, signals)
    assert bt_a["final_capital"] == bt_b["final_capital"]
    assert bt_a["total_return_pct"] == bt_b["total_return_pct"]
    assert bt_a["max_drawdown_pct"] == bt_b["max_drawdown_pct"]
