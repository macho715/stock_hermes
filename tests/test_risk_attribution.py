"""Tests for rolling factor regression + Brinson attribution."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_rtx4060.backtest.risk_attribution import (
    brinson_attribution,
    factor_exposure_regression,
)


def test_factor_regression_recovers_known_betas():
    rng = np.random.default_rng(0)
    n = 240
    dates = pd.bdate_range(end="2025-01-01", periods=n)
    f1 = rng.normal(scale=0.01, size=n)
    f2 = rng.normal(scale=0.008, size=n)
    f3 = rng.normal(scale=0.012, size=n)
    factors = pd.DataFrame({"mkt": f1, "size": f2, "value": f3}, index=dates)

    true_alpha = 0.0002
    true_beta = np.array([1.10, -0.30, 0.50])
    eps = rng.normal(scale=0.001, size=n)
    y = true_alpha + factors.to_numpy() @ true_beta + eps
    returns = pd.Series(y, index=dates, name="strategy")

    out = factor_exposure_regression(returns, factors, window=60)
    # Look at the *last* fitted row only — early rows are NaN by design.
    last = out.dropna().iloc[-1]
    assert abs(float(last["mkt"]) - 1.10) < 0.1
    assert abs(float(last["size"]) - (-0.30)) < 0.1
    assert abs(float(last["value"]) - 0.50) < 0.1
    # R² should be close to 1 since we generated y from the factors.
    assert float(last["r_squared"]) > 0.95


def test_brinson_attribution_sums_to_active_return():
    dates = pd.bdate_range(end="2025-01-01", periods=10)
    sectors = ["Tech", "Energy", "Healthcare"]
    rng = np.random.default_rng(1)

    pw = pd.DataFrame(rng.dirichlet(np.ones(3), size=10), index=dates, columns=sectors)
    bw = pd.DataFrame(rng.dirichlet(np.ones(3), size=10), index=dates, columns=sectors)
    pr = pd.DataFrame(rng.normal(0.001, 0.01, size=(10, 3)), index=dates, columns=sectors)
    br = pd.DataFrame(rng.normal(0.001, 0.01, size=(10, 3)), index=dates, columns=sectors)

    out = brinson_attribution(pw, bw, pr, br)

    # Sum of three total effects must equal active return within rounding.
    totals = out["__total__"]
    sum_effects = totals["total_allocation"] + totals["total_selection"] + totals["total_interaction"]
    np.testing.assert_allclose(sum_effects.to_numpy(), totals["active_return"].to_numpy(), atol=1e-10)


def test_factor_regression_raises_when_window_too_small():
    rng = np.random.default_rng(2)
    n = 120
    dates = pd.bdate_range(end="2025-01-01", periods=n)
    factors = pd.DataFrame({"mkt": rng.normal(size=n)}, index=dates)
    returns = pd.Series(rng.normal(size=n), index=dates)
    try:
        factor_exposure_regression(returns, factors, window=2)
    except ValueError:
        return
    raise AssertionError("expected ValueError for too-small window")


def test_factor_regression_input_type_validation():
    import pytest

    with pytest.raises(TypeError):
        factor_exposure_regression([1.0, 2.0], pd.DataFrame(), window=10)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        factor_exposure_regression(pd.Series([1.0]), [[1.0]], window=10)  # type: ignore[arg-type]


def test_factor_regression_no_overlap_raises():
    import pytest

    a = pd.Series([0.01], index=pd.to_datetime(["2024-01-01"]))
    b = pd.DataFrame({"x": [0.01]}, index=pd.to_datetime(["2024-02-01"]))
    with pytest.raises(ValueError):
        factor_exposure_regression(a, b, window=10)


def test_factor_regression_too_few_observations_raises():
    import pytest

    rng = np.random.default_rng(2)
    n = 30
    dates = pd.bdate_range(end="2025-01-01", periods=n)
    factors = pd.DataFrame({"mkt": rng.normal(size=n)}, index=dates)
    returns = pd.Series(rng.normal(size=n), index=dates)
    with pytest.raises(ValueError):
        factor_exposure_regression(returns, factors, window=60)


def test_brinson_attribution_input_validation():
    import pytest

    df = pd.DataFrame({"Tech": [0.5]}, index=pd.to_datetime(["2024-01-01"]))
    with pytest.raises(TypeError):
        brinson_attribution([1.0], df, df, df)  # type: ignore[arg-type]


def test_brinson_attribution_no_shared_sectors_raises():
    import pytest

    pw = pd.DataFrame({"A": [1.0]}, index=pd.to_datetime(["2024-01-01"]))
    bw = pd.DataFrame({"B": [1.0]}, index=pd.to_datetime(["2024-01-01"]))
    pr = pd.DataFrame({"A": [0.01]}, index=pd.to_datetime(["2024-01-01"]))
    br = pd.DataFrame({"B": [0.01]}, index=pd.to_datetime(["2024-01-01"]))
    with pytest.raises(ValueError):
        brinson_attribution(pw, bw, pr, br)
