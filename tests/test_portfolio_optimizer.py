"""Tests for ``stock_rtx4060.portfolio.optimizer``.

These tests must pass without skfolio, PyPortfolioOpt or cvxpy installed —
the pure-Python HRP fallback exercised below is the only mandatory backend.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.portfolio import LLMViews, ViewItem, optimize
from stock_rtx4060.portfolio import optimizer as opt_module


def _random_walk_returns(n_days: int = 200, n_tickers: int = 5, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    tickers = [f"T{i:02d}" for i in range(n_tickers)]
    data = rng.normal(0.0005, 0.012, size=(n_days, n_tickers))
    return pd.DataFrame(data, columns=tickers, index=pd.bdate_range(end="2024-01-01", periods=n_days))


# ---------------------------------------------------------------------------
# HRP
# ---------------------------------------------------------------------------


def test_hrp_returns_valid_weights_summing_to_one():
    returns = _random_walk_returns(200, 5)
    weights = optimize(returns, method="hrp", max_weight=0.25, min_weight=0.0, seed=42)
    assert isinstance(weights, pd.Series)
    assert abs(weights.sum() - 1.0) < 1e-6
    assert weights.min() >= 0.0 - 1e-9
    assert weights.max() <= 0.25 + 1e-9
    assert list(weights.index) == list(returns.columns)


def test_hrp_respects_box_constraints_when_clusters_force_high_weight():
    rng = np.random.default_rng(1)
    n = 200
    common = rng.normal(0, 0.001, n)
    data = np.column_stack(
        [
            common + rng.normal(0, 0.0001, n),  # near-zero vol cluster member
            common + rng.normal(0, 0.0001, n),
            common + rng.normal(0, 0.0001, n),
            rng.normal(0, 0.04, n),  # wild
            rng.normal(0, 0.04, n),  # wild
        ]
    )
    returns = pd.DataFrame(data, columns=list("ABCDE"))
    weights = optimize(returns, method="hrp", max_weight=0.30, min_weight=0.0)
    assert weights.max() <= 0.30 + 1e-9


# ---------------------------------------------------------------------------
# Mean-variance / risk-budgeting / cvar
# ---------------------------------------------------------------------------


def test_mean_variance_respects_max_weight():
    returns = _random_walk_returns(200, 5)
    weights = optimize(returns, method="risk_budgeting", max_weight=0.25, seed=42)
    assert weights.max() <= 0.25 + 1e-9
    assert abs(weights.sum() - 1.0) < 1e-6


def test_cvar_returns_valid_weights():
    returns = _random_walk_returns(200, 4)
    weights = optimize(returns, method="mv_cvar", max_weight=0.30, cvar_alpha=0.05, seed=42)
    assert weights.max() <= 0.30 + 1e-9
    assert abs(weights.sum() - 1.0) < 1e-6
    assert (weights >= -1e-9).all()


# ---------------------------------------------------------------------------
# Pure-Python HRP works without skfolio/pypfopt
# ---------------------------------------------------------------------------


def test_pure_python_hrp_works_without_optional_libs(monkeypatch):
    monkeypatch.setattr(opt_module, "_has_skfolio", lambda: False)
    monkeypatch.setattr(opt_module, "_has_pypfopt", lambda: False)
    returns = _random_walk_returns(150, 5, seed=7)
    weights = optimize(returns, method="hrp", max_weight=0.40)
    assert isinstance(weights, pd.Series)
    assert abs(weights.sum() - 1.0) < 1e-6
    assert weights.min() >= 0.0 - 1e-9


def test_pure_python_risk_budgeting_works_without_optional_libs(monkeypatch):
    monkeypatch.setattr(opt_module, "_has_skfolio", lambda: False)
    monkeypatch.setattr(opt_module, "_has_pypfopt", lambda: False)
    returns = _random_walk_returns(120, 4, seed=3)
    weights = optimize(returns, method="risk_budgeting", max_weight=0.5)
    assert abs(weights.sum() - 1.0) < 1e-6


def test_pure_python_black_litterman_with_views(monkeypatch):
    monkeypatch.setattr(opt_module, "_has_skfolio", lambda: False)
    monkeypatch.setattr(opt_module, "_has_pypfopt", lambda: False)
    returns = _random_walk_returns(150, 4, seed=5)
    prior = pd.Series(0.001, index=returns.columns)
    views = LLMViews(items=[ViewItem(ticker=returns.columns[0], advisory_score=0.8, confidence=0.9)])
    weights = optimize(returns, method="black_litterman", expected_returns=prior, views=views, max_weight=0.8)
    assert abs(weights.sum() - 1.0) < 1e-6
    # The high-confidence positive view should give the first asset more weight
    # than the equal-weight baseline (0.25).
    assert weights.iloc[0] > 0.25


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------


def test_reproducibility_same_seed_same_weights():
    returns = _random_walk_returns(200, 5, seed=11)
    w1 = optimize(returns, method="hrp", seed=99)
    w2 = optimize(returns, method="hrp", seed=99)
    pd.testing.assert_series_equal(w1, w2)


def test_reproducibility_risk_budgeting_seed():
    returns = _random_walk_returns(200, 5, seed=11)
    w1 = optimize(returns, method="risk_budgeting", seed=99)
    w2 = optimize(returns, method="risk_budgeting", seed=99)
    pd.testing.assert_series_equal(w1, w2)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_optimize_requires_dataframe():
    with pytest.raises(TypeError):
        optimize([[0.01, 0.02]], method="hrp")  # type: ignore[arg-type]


def test_optimize_requires_at_least_two_tickers():
    df = pd.DataFrame({"A": [0.01, -0.01, 0.005]})
    with pytest.raises(ValueError):
        optimize(df, method="hrp")


def test_optimize_drops_nan_rows():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(0, 0.01, (50, 3)), columns=["A", "B", "C"])
    df.iloc[5, 1] = np.nan
    weights = optimize(df, method="hrp", max_weight=0.5)
    assert abs(weights.sum() - 1.0) < 1e-6


def test_optimize_unknown_method_raises():
    df = _random_walk_returns(100, 3)
    with pytest.raises(ValueError):
        optimize(df, method="not_a_method")  # type: ignore[arg-type]
