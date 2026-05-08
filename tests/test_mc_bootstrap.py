"""Tests for the block bootstrap and drawdown bounds."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_rtx4060.backtest.mc_bootstrap import block_bootstrap, drawdown_bounds


def _ar1_returns(n: int = 252, *, seed: int = 0, phi: float = 0.2) -> pd.Series:
    rng = np.random.default_rng(seed)
    eps = rng.normal(scale=0.01, size=n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + eps[i]
    return pd.Series(out, index=pd.bdate_range(end="2025-01-01", periods=n))


def test_block_bootstrap_shape():
    rets = _ar1_returns(252)
    paths = block_bootstrap(rets, block_size=10, n_paths=64, seed=42)
    assert paths.shape == (252, 64)
    # No NaNs.
    assert not paths.isna().any().any()


def test_drawdown_bounds_monotonic():
    rets = _ar1_returns(252)
    bounds = drawdown_bounds(rets, block_size=20, n_paths=500, seed=123)
    # Higher percentile selects the worse drawdown -> the values must be
    # monotonically non-decreasing.
    assert bounds["p99_max_dd"] >= bounds["p95_max_dd"] >= bounds["p50_max_dd"]
    # All should be in [0, 1] for sane returns.
    for value in bounds.values():
        assert 0.0 <= value <= 1.0


def test_block_bootstrap_seed_reproducible():
    rets = _ar1_returns(120)
    a = block_bootstrap(rets, block_size=15, n_paths=32, seed=7)
    b = block_bootstrap(rets, block_size=15, n_paths=32, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_block_bootstrap_custom_n_periods():
    rets = _ar1_returns(120)
    paths = block_bootstrap(rets, block_size=10, n_paths=8, n_periods=50, seed=1)
    assert paths.shape == (50, 8)


def test_block_bootstrap_invalid_inputs():
    rets = _ar1_returns(60)
    import pytest

    with pytest.raises(TypeError):
        block_bootstrap([0.01, 0.02], block_size=5, n_paths=10)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        block_bootstrap(rets, block_size=0, n_paths=10)
    with pytest.raises(ValueError):
        block_bootstrap(rets, block_size=5, n_paths=0)
    with pytest.raises(ValueError):
        block_bootstrap(rets, block_size=5, n_paths=10, n_periods=0)
    with pytest.raises(ValueError):
        block_bootstrap(pd.Series([], dtype=float), block_size=5, n_paths=10)


def test_drawdown_bounds_zero_returns():
    rets = pd.Series(np.zeros(60), index=pd.bdate_range(end="2024-01-01", periods=60))
    bounds = drawdown_bounds(rets, block_size=10, n_paths=64, seed=1)
    # Constant-zero returns -> zero drawdown across all percentiles.
    assert bounds["p50_max_dd"] == 0.0
    assert bounds["p95_max_dd"] == 0.0
    assert bounds["p99_max_dd"] == 0.0
