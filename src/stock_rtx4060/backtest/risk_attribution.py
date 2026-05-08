"""Risk attribution: rolling factor regressions and Brinson decomposition.

Pure NumPy / SciPy — no statsmodels dependency required.  ``scipy`` is used
for the OLS solve when present; otherwise ``numpy.linalg.lstsq`` is the
fallback.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:  # scipy is in requirements.in; gate defensively.
    from scipy.linalg import lstsq as _scipy_lstsq

    _HAS_SCIPY = True
except Exception:  # pragma: no cover - safety net
    _scipy_lstsq = None  # type: ignore[assignment]
    _HAS_SCIPY = False


def _ols(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    """Return (beta, r_squared) for ``y = x · beta`` via OLS.

    ``x`` should already include an intercept column when desired.
    """
    if _HAS_SCIPY:
        beta, _residues, _rank, _sv = _scipy_lstsq(x, y, lapack_driver="gelsd")
    else:
        beta, _residues, _rank, _sv = np.linalg.lstsq(x, y, rcond=None)
    fitted = x @ beta
    ss_res = float(np.sum((y - fitted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 0.0
    return beta, float(r2)


def factor_exposure_regression(
    returns: pd.Series,
    factor_returns: pd.DataFrame,
    *,
    window: int = 60,
) -> pd.DataFrame:
    """Rolling OLS of ``returns`` on ``factor_returns`` (intercept added).

    Parameters
    ----------
    returns:
        Strategy or asset return series.
    factor_returns:
        DataFrame whose columns are the explanatory factor returns.  Index
        is aligned to ``returns`` via inner join.
    window:
        Rolling window length in observations.  Must be ``>= 2 + n_factors``
        so the OLS system is overdetermined.

    Returns
    -------
    DataFrame indexed by date with columns:

    - ``alpha`` — intercept coefficient
    - one column per input factor name — slope coefficients
    - ``r_squared`` — in-sample R² of the rolling fit
    """
    if not isinstance(returns, pd.Series):
        raise TypeError("returns must be a pandas Series")
    if not isinstance(factor_returns, pd.DataFrame):
        raise TypeError("factor_returns must be a pandas DataFrame")

    aligned = pd.concat([returns.rename("__y__"), factor_returns], axis=1, join="inner").dropna()
    if aligned.empty:
        raise ValueError("returns and factor_returns share no overlapping observations")

    factor_names = list(factor_returns.columns)
    n_factors = len(factor_names)
    if window < n_factors + 2:
        raise ValueError(f"window={window} too small for {n_factors} factors")
    if len(aligned) < window:
        raise ValueError(f"only {len(aligned)} aligned observations; need >= {window}")

    y_all = aligned["__y__"].to_numpy(dtype=float)
    x_all = aligned[factor_names].to_numpy(dtype=float)
    n = len(aligned)

    out_alpha = np.full(n, np.nan)
    out_betas = np.full((n, n_factors), np.nan)
    out_r2 = np.full(n, np.nan)

    for end in range(window, n + 1):
        start = end - window
        y = y_all[start:end]
        x = x_all[start:end]
        x_with_intercept = np.column_stack([np.ones(window), x])
        try:
            beta, r2 = _ols(y, x_with_intercept)
        except np.linalg.LinAlgError:
            continue
        i = end - 1
        out_alpha[i] = beta[0]
        out_betas[i, :] = beta[1:]
        out_r2[i] = r2

    cols = {"alpha": out_alpha}
    for j, name in enumerate(factor_names):
        cols[name] = out_betas[:, j]
    cols["r_squared"] = out_r2
    return pd.DataFrame(cols, index=aligned.index)


def brinson_attribution(
    portfolio_weights: pd.DataFrame,
    benchmark_weights: pd.DataFrame,
    portfolio_returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
) -> pd.DataFrame:
    """Brinson-Fachler attribution (allocation / selection / interaction).

    Each row corresponds to a date and each column-block to a sector.
    For sector ``i`` on a single period the effects are::

        allocation_i  = (w_p_i - w_b_i) · (r_b_i - r_b_total)
        selection_i   = w_b_i · (r_p_i - r_b_i)
        interaction_i = (w_p_i - w_b_i) · (r_p_i - r_b_i)

    where ``r_b_total = Σ_j w_b_j · r_b_j``.  Summing the three effects
    across sectors gives the active return ``r_p_total - r_b_total``.

    Parameters
    ----------
    portfolio_weights, benchmark_weights:
        DataFrames with sectors as columns and dates as index.  Each row
        should sum to ~1 but is not enforced.
    portfolio_returns, benchmark_returns:
        DataFrames of *sector* returns with the same shape as the weights.

    Returns
    -------
    DataFrame indexed by date with multi-index columns
    ``(sector, effect)`` where ``effect ∈ {allocation, selection, interaction}``,
    plus three roll-up columns ``total_allocation``, ``total_selection``,
    ``total_interaction``, and ``active_return``.
    """
    frames = {
        "portfolio_weights": portfolio_weights,
        "benchmark_weights": benchmark_weights,
        "portfolio_returns": portfolio_returns,
        "benchmark_returns": benchmark_returns,
    }
    for name, df in frames.items():
        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"{name} must be a pandas DataFrame")

    sectors = sorted(set(portfolio_weights.columns) & set(benchmark_weights.columns))
    if not sectors:
        raise ValueError("portfolio_weights and benchmark_weights share no sectors")
    sectors = [c for c in sectors if c in portfolio_returns.columns and c in benchmark_returns.columns]
    if not sectors:
        raise ValueError("returns frames do not cover the shared sectors")

    idx = portfolio_weights.index.intersection(benchmark_weights.index)
    idx = idx.intersection(portfolio_returns.index).intersection(benchmark_returns.index)
    if len(idx) == 0:
        raise ValueError("inputs share no overlapping dates")

    pw = portfolio_weights.loc[idx, sectors].astype(float)
    bw = benchmark_weights.loc[idx, sectors].astype(float)
    pr = portfolio_returns.loc[idx, sectors].astype(float)
    br = benchmark_returns.loc[idx, sectors].astype(float)

    benchmark_total = (bw * br).sum(axis=1)
    portfolio_total = (pw * pr).sum(axis=1)

    allocation = (pw - bw).multiply(br.sub(benchmark_total, axis=0))
    selection = bw * (pr - br)
    interaction = (pw - bw) * (pr - br)

    out = (
        pd.concat(
            {
                "allocation": allocation,
                "selection": selection,
                "interaction": interaction,
            },
            axis=1,
        )
        .swaplevel(axis=1)
        .sort_index(axis=1)
    )

    out[("__total__", "total_allocation")] = allocation.sum(axis=1)
    out[("__total__", "total_selection")] = selection.sum(axis=1)
    out[("__total__", "total_interaction")] = interaction.sum(axis=1)
    out[("__total__", "active_return")] = portfolio_total - benchmark_total
    return out
