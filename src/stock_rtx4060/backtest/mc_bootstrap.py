"""Stationary block bootstrap for Monte Carlo path simulation.

The block bootstrap preserves short-term autocorrelation by resampling
contiguous blocks of returns rather than i.i.d. observations.  It is the
standard tool for distribution-free confidence bounds on path-dependent
metrics such as max drawdown.

Pure NumPy — no optional deps.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def block_bootstrap(
    returns: pd.Series,
    *,
    block_size: int = 20,
    n_paths: int = 2000,
    n_periods: int | None = None,
    seed: int | None = None,
) -> pd.DataFrame:
    """Generate ``n_paths`` bootstrapped return paths from ``returns``.

    Parameters
    ----------
    returns:
        Realized return series.  Index is preserved positionally — only the
        values are sampled.
    block_size:
        Length of contiguous blocks drawn from ``returns``.  Larger blocks
        preserve more serial correlation.
    n_paths:
        Number of synthetic return paths to generate.
    n_periods:
        Length of each synthetic path.  Defaults to ``len(returns)``.
    seed:
        Optional seed for reproducibility.

    Returns
    -------
    DataFrame of shape ``(n_periods, n_paths)``; column names are integer
    indices ``0..n_paths-1``.
    """
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if block_size < 1:
        raise ValueError("block_size must be >= 1")
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")

    arr = np.asarray(returns.dropna().values, dtype=float)
    if arr.size == 0:
        raise ValueError("returns is empty after dropping NaN")

    n = int(n_periods) if n_periods is not None else arr.size
    if n < 1:
        raise ValueError("n_periods must be >= 1")

    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block_size))
    # Sample block starts uniformly with replacement over [0, len(arr)).
    # Wrap-around (circular) sampling avoids edge bias.
    starts = rng.integers(0, arr.size, size=(n_paths, n_blocks))

    out = np.empty((n_paths, n_blocks * block_size), dtype=float)
    offsets = np.arange(block_size)
    for j in range(n_blocks):
        # idx shape: (n_paths, block_size); modulo handles circular wrap.
        idx = (starts[:, j : j + 1] + offsets[np.newaxis, :]) % arr.size
        out[:, j * block_size : (j + 1) * block_size] = arr[idx]
    out = out[:, :n]
    return pd.DataFrame(out.T, columns=range(n_paths))


def _max_drawdown_from_returns(returns: np.ndarray) -> float:
    """Max drawdown for a 1-D return array, expressed as a positive fraction."""
    if returns.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(abs(dd.min()))


def drawdown_bounds(
    returns: pd.Series,
    *,
    block_size: int = 20,
    n_paths: int = 2000,
    alpha: float = 0.05,  # noqa: ARG001 - reserved for symmetry with other VaR APIs
    seed: int | None = None,
) -> dict[str, float]:
    """Return median, 95th, and 99th percentile max-drawdown estimates.

    The mapping is monotone: ``p99_max_dd >= p95_max_dd >= p50_max_dd`` since
    higher percentiles select worse drawdowns.
    """
    paths = block_bootstrap(
        returns,
        block_size=block_size,
        n_paths=n_paths,
        seed=seed,
    )
    mdds = np.array([_max_drawdown_from_returns(paths[col].values) for col in paths.columns])
    return {
        "p50_max_dd": float(np.percentile(mdds, 50)),
        "p95_max_dd": float(np.percentile(mdds, 95)),
        "p99_max_dd": float(np.percentile(mdds, 99)),
    }
