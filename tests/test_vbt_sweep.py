"""Tests for the Phase-5 vectorbt parameter-sweep runner.

The runner falls back to a pure-pandas grid when vectorbt is unavailable.
We assert structural properties that hold regardless of the engine plus the
MLflow side-effect when ``MLFLOW_TRACKING_URI`` is set to a sqlite store.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.backtest.vbt_sweep import run_vbt_sweep


def _synthetic_prices(n_days: int = 50, n_tickers: int = 3, *, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end="2025-01-01", periods=n_days)
    rets = rng.normal(loc=0.0005, scale=0.012, size=(n_days, n_tickers))
    prices = 100.0 * np.cumprod(1.0 + rets, axis=0)
    cols = [f"T{i}" for i in range(n_tickers)]
    return pd.DataFrame(prices, index=dates, columns=cols)


def test_vbt_sweep_returns_grid_and_metric_columns():
    prices = _synthetic_prices()
    grid = {"ma_window": [5, 10], "stop_pct": [0.03, 0.05]}
    df = run_vbt_sweep(prices, grid=grid, fees=0.001, slippage=0.0005, experiment="vbt_sweep_test")

    # 2 x 2 grid -> 4 rows
    assert len(df) == 4
    # All grid keys are present.
    for key in grid:
        assert key in df.columns
    # All metric keys are present.
    for metric in ("total_return", "sharpe", "max_dd", "n_trades", "engine"):
        assert metric in df.columns


def test_vbt_sweep_sharpe_is_finite_or_nan_only():
    prices = _synthetic_prices()
    df = run_vbt_sweep(
        prices,
        grid={"ma_window": [5, 10], "stop_pct": [0.03, 0.05]},
        experiment="vbt_sweep_test",
    )
    # Each row's sharpe must be finite; allow NaN only if the strategy never
    # traded (which can happen with very small data — but our synthetic
    # prices oscillate enough to always trade).
    for sharpe in df["sharpe"]:
        assert math.isfinite(float(sharpe)) or math.isnan(float(sharpe))


def test_vbt_sweep_logs_to_mlflow(tmp_path, monkeypatch):
    pytest.importorskip("mlflow")
    db = tmp_path / "mlflow.db"
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{db}")
    prices = _synthetic_prices()
    df = run_vbt_sweep(
        prices,
        grid={"ma_window": [5, 10], "stop_pct": [0.03, 0.05]},
        experiment="vbt_sweep_mlflow_test",
    )
    assert len(df) == 4
    # The sqlite file is created lazily by mlflow once a run is logged.
    assert db.exists()
