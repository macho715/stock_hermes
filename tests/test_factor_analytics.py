"""Tests for the analytics helpers (IC/IR/decay/quintile P&L/rank-autocorr)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_rtx4060.factors.analytics import (
    compute_ic,
    compute_ir,
    factor_decay,
    quintile_pnl,
    rank_autocorr,
)


def test_compute_ic_perfect_signal_high() -> None:
    rng = np.random.default_rng(0)
    n = 200
    factor = pd.Series(rng.normal(0, 1, n))
    fwd = factor + rng.normal(0, 0.05, n)
    ic = compute_ic(factor, fwd, method="spearman")
    assert ic > 0.5


def test_compute_ic_inverse_signal_negative() -> None:
    rng = np.random.default_rng(1)
    n = 200
    factor = pd.Series(rng.normal(0, 1, n))
    fwd = -factor + rng.normal(0, 0.05, n)
    ic = compute_ic(factor, fwd)
    assert ic < -0.5


def test_compute_ic_random_low() -> None:
    rng = np.random.default_rng(2)
    factor = pd.Series(rng.normal(0, 1, 500))
    fwd = pd.Series(rng.normal(0, 1, 500))
    ic = compute_ic(factor, fwd)
    assert abs(ic) < 0.3


def test_compute_ic_pearson_method() -> None:
    rng = np.random.default_rng(3)
    factor = pd.Series(rng.normal(0, 1, 200))
    fwd = factor * 2.0 + rng.normal(0, 0.1, 200)
    ic_p = compute_ic(factor, fwd, method="pearson")
    ic_s = compute_ic(factor, fwd, method="spearman")
    assert abs(ic_p) > 0.9
    assert abs(ic_s) > 0.9


def test_compute_ic_handles_constants() -> None:
    factor = pd.Series([1.0] * 50)
    fwd = pd.Series(range(50), dtype=float)
    ic = compute_ic(factor, fwd)
    assert np.isnan(ic)


def test_compute_ir_basic() -> None:
    ic_series = pd.Series([0.04, 0.05, 0.03, 0.06, 0.04])
    ir = compute_ir(ic_series)
    assert ir > 1.0  # tight cluster around 0.04 -> high IR


def test_compute_ir_zero_std() -> None:
    ic_series = pd.Series([0.05] * 5)
    ir = compute_ir(ic_series)
    assert np.isnan(ir)


def test_factor_decay_dict() -> None:
    rng = np.random.default_rng(4)
    factor = pd.Series(rng.normal(0, 1, 200))
    fwd1 = factor + rng.normal(0, 0.1, 200)
    fwd5 = factor * 0.5 + rng.normal(0, 0.5, 200)
    out = factor_decay(factor, {1: fwd1, 5: fwd5})
    assert set(out.keys()) == {1, 5}
    assert out[1] > out[5]  # signal decays at longer horizon


def test_quintile_pnl_shape() -> None:
    rng = np.random.default_rng(5)
    n = 500
    factor = pd.Series(rng.normal(0, 1, n))
    fwd = factor * 0.1 + rng.normal(0, 0.05, n)
    out = quintile_pnl(factor, fwd, n_quantiles=5)
    assert "mean_ret" in out.columns
    assert "count" in out.columns
    assert len(out) == 5
    # Top quintile mean should exceed bottom quintile.
    assert out["mean_ret"].iloc[-1] > out["mean_ret"].iloc[0]


def test_rank_autocorr_persistent_signal() -> None:
    # AR(1) with rho = 0.8: high rank autocorr
    rng = np.random.default_rng(6)
    n = 500
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = 0.85 * x[i - 1] + rng.normal(0, 0.1)
    s = pd.Series(x)
    rho = rank_autocorr(s, lag=1)
    assert rho > 0.5


def test_rank_autocorr_white_noise_low() -> None:
    rng = np.random.default_rng(7)
    s = pd.Series(rng.normal(0, 1, 1000))
    rho = rank_autocorr(s, lag=1)
    assert abs(rho) < 0.1
