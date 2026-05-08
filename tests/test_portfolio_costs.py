"""Tests for ``stock_rtx4060.portfolio.costs``."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.portfolio.costs import (
    TransactionCosts,
    apply_turnover_penalty,
    cost_estimate,
    turnover,
)


def test_linear_bps_per_side_sums_commission_and_spread():
    costs = TransactionCosts(commission_bps=5.0, spread_bps=10.0)
    assert costs.linear_bps_per_side == pytest.approx(15.0)
    assert costs.linear_fraction_per_side == pytest.approx(0.0015)


def test_default_costs():
    costs = TransactionCosts()
    assert costs.commission_bps == 5.0
    assert costs.spread_bps == 10.0
    assert costs.impact_lambda == 0.0


def test_apply_turnover_penalty_lambda_zero_returns_new():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.2, 0.8], index=["A", "B"])
    result = apply_turnover_penalty(prev, new, TransactionCosts(), lambda_turnover=0.0)
    pd.testing.assert_series_equal(result, new)


def test_apply_turnover_penalty_high_lambda_shrinks_to_prev():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.0, 1.0], index=["A", "B"])
    result = apply_turnover_penalty(
        prev, new, TransactionCosts(commission_bps=200.0, spread_bps=200.0), lambda_turnover=10_000.0
    )
    np.testing.assert_allclose(result.values, prev.values, atol=1e-6)


def test_apply_turnover_penalty_intermediate_lambda():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.3, 0.7], index=["A", "B"])
    result = apply_turnover_penalty(prev, new, TransactionCosts(), lambda_turnover=1.0)
    # Should be between prev and new for at least one asset.
    assert min(prev["A"], new["A"]) - 1e-9 <= result["A"] <= max(prev["A"], new["A"]) + 1e-9


def test_apply_turnover_penalty_no_change_returns_same():
    prev = pd.Series([0.4, 0.6], index=["A", "B"])
    new = pd.Series([0.4, 0.6], index=["A", "B"])
    result = apply_turnover_penalty(prev, new, TransactionCosts(), lambda_turnover=5.0)
    pd.testing.assert_series_equal(result, new)


def test_apply_turnover_penalty_aligns_disjoint_universes():
    prev = pd.Series([1.0], index=["A"])
    new = pd.Series([1.0], index=["B"])
    result = apply_turnover_penalty(prev, new, TransactionCosts(), lambda_turnover=0.0)
    assert set(result.index) == {"A", "B"}


def test_apply_turnover_penalty_negative_lambda_raises():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.3, 0.7], index=["A", "B"])
    with pytest.raises(ValueError):
        apply_turnover_penalty(prev, new, TransactionCosts(), lambda_turnover=-1.0)


def test_turnover_l1_norm():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.2, 0.8], index=["A", "B"])
    assert turnover(prev, new) == pytest.approx(0.6)


def test_cost_estimate_scales_with_turnover():
    prev = pd.Series([0.5, 0.5], index=["A", "B"])
    new = pd.Series([0.2, 0.8], index=["A", "B"])
    costs = TransactionCosts(commission_bps=5.0, spread_bps=10.0)
    expected = 0.6 * 0.0015
    assert cost_estimate(prev, new, costs) == pytest.approx(expected)
