"""Pure analytics helpers for factor evaluation.

These functions operate on already-aligned ``pd.Series`` of factor values and
forward returns; they do not perform any data fetching or panel manipulation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

import numpy as np
import pandas as pd


def _aligned(factor_values: pd.Series, fwd_returns: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Return both series aligned on their intersection, with NaN rows dropped."""
    df = pd.concat([factor_values.rename("f"), fwd_returns.rename("r")], axis=1, join="inner")
    df = df.replace([np.inf, -np.inf], np.nan).dropna()
    return df["f"], df["r"]


def compute_ic(
    factor_values: pd.Series,
    fwd_returns: pd.Series,
    method: Literal["pearson", "spearman"] = "spearman",
) -> float:
    """Information Coefficient between a factor and forward returns.

    Returns the rank correlation by default.  NaNs are dropped before computing.
    """
    f, r = _aligned(factor_values, fwd_returns)
    if len(f) < 3 or f.std(ddof=0) == 0.0 or r.std(ddof=0) == 0.0:
        return float("nan")
    return float(f.corr(r, method=method))


def compute_ir(ic_series: pd.Series) -> float:
    """Information Ratio = mean(IC) / std(IC).  NaN if std is zero / not enough data."""
    s = pd.Series(ic_series).dropna()
    if len(s) < 2 or s.std(ddof=1) == 0.0 or not np.isfinite(s.std(ddof=1)):
        return float("nan")
    return float(s.mean() / s.std(ddof=1))


def factor_decay(
    factor_values: pd.Series,
    fwd_returns_by_horizon: Mapping[int, pd.Series],
    method: Literal["pearson", "spearman"] = "spearman",
) -> dict[int, float]:
    """IC at multiple forward horizons.  Useful for half-life estimation."""
    return {int(h): compute_ic(factor_values, ret, method=method) for h, ret in fwd_returns_by_horizon.items()}


def quintile_pnl(
    factor_values: pd.Series,
    fwd_returns: pd.Series,
    n_quantiles: int = 5,
) -> pd.DataFrame:
    """Group factor values into ``n_quantiles`` and compute mean forward return per bucket.

    Returns a DataFrame with one row per bucket: columns ``mean_ret``, ``count``.
    """
    f, r = _aligned(factor_values, fwd_returns)
    if f.empty or n_quantiles < 2:
        return pd.DataFrame(columns=["mean_ret", "count"])
    try:
        buckets = pd.qcut(f, q=n_quantiles, labels=False, duplicates="drop")
    except ValueError:  # pragma: no cover - degenerate input
        return pd.DataFrame(columns=["mean_ret", "count"])
    grouped = r.groupby(buckets)
    out = pd.DataFrame({"mean_ret": grouped.mean(), "count": grouped.count()})
    out.index.name = "quantile"
    return out


def rank_autocorr(factor_values: pd.Series, lag: int = 1) -> float:
    """Lag-``lag`` autocorrelation of cross-sectional ranks (proxy for turnover)."""
    s = pd.Series(factor_values).dropna()
    if len(s) <= lag + 2:
        return float("nan")
    ranks = s.rank()
    auto = ranks.autocorr(lag=lag)
    return float(auto) if auto is not None and np.isfinite(auto) else float("nan")
