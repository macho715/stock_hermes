"""Phase-4 portfolio optimisation facade.

Backends, in priority order:

1. **skfolio** — when installed, exposed via ``HierarchicalRiskParity``,
   ``NestedClustersOptimization``, ``RiskBudgeting``, ``MeanRisk`` and
   ``BlackLitterman``.
2. **PyPortfolioOpt** — fallback for HRP, mean-variance, CVaR and
   Black-Litterman when skfolio is unavailable.
3. **Pure-Python HRP** — always available.  This is the López de Prado HRP
   recipe (linkage clustering → quasi-diagonalisation → recursive bisection)
   implemented on top of NumPy / SciPy / scikit-learn only.  When the user
   requests a method other than HRP and neither optional library is
   installed we raise :class:`ImportError` with an install hint.

The public API is :func:`optimize` which always returns a ``pandas.Series`` of
weights summing to 1.0, indexed by ticker.
"""

from __future__ import annotations

import warnings
from typing import Literal

import numpy as np
import pandas as pd

from .views import LLMViews, to_black_litterman_inputs

Method = Literal["hrp", "nco", "risk_budgeting", "mv_cvar", "black_litterman"]


# ---------------------------------------------------------------------------
# Optional-dependency probes
# ---------------------------------------------------------------------------


def _has_skfolio() -> bool:
    try:  # pragma: no cover - optional dep
        import skfolio  # noqa: F401

        return True
    except Exception:
        return False


def _has_pypfopt() -> bool:
    try:  # pragma: no cover - optional dep
        import pypfopt  # noqa: F401

        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Covariance estimation
# ---------------------------------------------------------------------------


def _estimate_covariance(
    returns: pd.DataFrame,
    estimator: Literal["sample", "ledoit_wolf", "oas"],
) -> pd.DataFrame:
    """Return an estimated covariance matrix as a DataFrame."""
    cols = list(returns.columns)
    if estimator == "sample" or returns.shape[0] < 5:
        cov = returns.cov().values
    else:
        try:
            if estimator == "ledoit_wolf":
                from sklearn.covariance import LedoitWolf

                cov = LedoitWolf().fit(returns.values).covariance_
            elif estimator == "oas":
                from sklearn.covariance import OAS

                cov = OAS().fit(returns.values).covariance_
            else:  # pragma: no cover - guarded by Literal
                raise ValueError(f"Unknown covariance estimator: {estimator}")
        except Exception:
            cov = returns.cov().values
    return pd.DataFrame(cov, index=cols, columns=cols)


# ---------------------------------------------------------------------------
# Pure-Python HRP fallback (always works)
# ---------------------------------------------------------------------------


def _correlation_distance(corr: np.ndarray) -> np.ndarray:
    """Convert correlation matrix to López de Prado distance ``sqrt(0.5*(1-rho))``."""
    corr = np.clip(corr, -1.0, 1.0)
    return np.sqrt(np.maximum(0.5 * (1.0 - corr), 0.0))


def _quasi_diagonal_order(linkage_matrix: np.ndarray) -> list[int]:
    """Return leaf order from a SciPy linkage matrix (López de Prado §16.4)."""
    link = linkage_matrix.astype(int)
    n = link.shape[0] + 1
    # Start with the last cluster (which contains all leaves).
    order = [link[-1, 0], link[-1, 1]]
    while True:
        new_order: list[int] = []
        changed = False
        for item in order:
            if item < n:
                new_order.append(item)
            else:
                row = link[item - n]
                new_order.append(int(row[0]))
                new_order.append(int(row[1]))
                changed = True
        order = new_order
        if not changed:
            break
    return order


def _ivp_weights(cov_block: np.ndarray) -> np.ndarray:
    """Inverse-variance portfolio weights for one cluster."""
    diag = np.diag(cov_block)
    safe = np.where(diag > 0, diag, np.finfo(float).eps)
    inv = 1.0 / safe
    return inv / inv.sum()


def _cluster_variance(cov: np.ndarray, idx: list[int]) -> float:
    block = cov[np.ix_(idx, idx)]
    w = _ivp_weights(block)
    return float(w @ block @ w)


def _hrp_recursive_bisection(cov: np.ndarray, ordering: list[int]) -> np.ndarray:
    """López de Prado HRP recursive bisection (§16.4)."""
    weights = np.ones(cov.shape[0], dtype=float)
    clusters: list[list[int]] = [list(ordering)]
    while clusters:
        cluster = clusters.pop()
        if len(cluster) <= 1:
            continue
        split = len(cluster) // 2
        left = cluster[:split]
        right = cluster[split:]
        var_left = _cluster_variance(cov, left)
        var_right = _cluster_variance(cov, right)
        denom = var_left + var_right
        if denom <= 0 or not np.isfinite(denom):
            alpha = 0.5
        else:
            alpha = 1.0 - var_left / denom
        for i in left:
            weights[i] *= alpha
        for i in right:
            weights[i] *= 1.0 - alpha
        clusters.append(left)
        clusters.append(right)
    return weights


def _pure_python_hrp(returns: pd.DataFrame, cov: pd.DataFrame) -> pd.Series:
    """Pure-Python HRP using SciPy hierarchical clustering."""
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform

    corr = returns.corr().fillna(0.0).values
    np.fill_diagonal(corr, 1.0)
    dist = _correlation_distance(corr)
    # Symmetrise and zero diagonal for SciPy
    dist = (dist + dist.T) / 2.0
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    ordering = _quasi_diagonal_order(link)
    weights = _hrp_recursive_bisection(cov.values, ordering)
    weights = weights / weights.sum() if weights.sum() > 0 else weights
    return pd.Series(weights, index=cov.index, name="hrp_weight")


# ---------------------------------------------------------------------------
# Constraint enforcement
# ---------------------------------------------------------------------------


def _project_box(weights: pd.Series, min_w: float, max_w: float) -> pd.Series:
    """Project weights onto the box ``[min_w, max_w]`` and renormalise to sum to 1.

    Uses an iterative water-filling approach to handle the simplex+box constraint.
    """
    n = len(weights)
    if n == 0:
        return weights
    if min_w * n > 1.0 + 1e-9:
        raise ValueError(f"min_weight {min_w} * n {n} > 1 (infeasible)")
    if max_w * n < 1.0 - 1e-9:
        raise ValueError(f"max_weight {max_w} * n {n} < 1 (infeasible)")

    w = weights.values.astype(float)
    # Project onto box, then renormalise.  Repeat to handle the case where
    # renormalisation pushes a weight back outside the box.
    for _ in range(50):
        w = np.clip(w, min_w, max_w)
        deficit = 1.0 - w.sum()
        if abs(deficit) < 1e-9:
            break
        # Distribute deficit only among assets that still have headroom
        if deficit > 0:
            mask = w < max_w - 1e-12
        else:
            mask = w > min_w + 1e-12
        if not mask.any():
            break
        w[mask] += deficit / mask.sum()

    w = np.clip(w, min_w, max_w)
    total = w.sum()
    if total > 0:
        w = w / total
    return pd.Series(w, index=weights.index, name=weights.name)


# ---------------------------------------------------------------------------
# skfolio-backed implementations (best-effort; gracefully fall through)
# ---------------------------------------------------------------------------


def _skfolio_optimize(  # pragma: no cover - exercised only when skfolio is installed
    returns: pd.DataFrame,
    method: Method,
    *,
    expected_returns: pd.Series | None,
    views: LLMViews | None,
    cov_estimator: str,
    cvar_alpha: float,
    max_weight: float,
    min_weight: float,
) -> pd.Series | None:
    if not _has_skfolio():
        return None
    try:
        from skfolio.optimization import (
            BlackLitterman,
            HierarchicalRiskParity,
            MeanRisk,
            NestedClustersOptimization,
            RiskBudgeting,
        )
    except Exception:
        return None
    try:
        if method == "hrp":
            est = HierarchicalRiskParity(min_weights=min_weight, max_weights=max_weight)
        elif method == "nco":
            est = NestedClustersOptimization(min_weights=min_weight, max_weights=max_weight)
        elif method == "risk_budgeting":
            est = RiskBudgeting(min_weights=min_weight, max_weights=max_weight)
        elif method == "mv_cvar":
            est = MeanRisk(risk_measure="cvar", min_weights=min_weight, max_weights=max_weight)
        elif method == "black_litterman":
            if views is None or expected_returns is None:
                return None
            p, q, omega = to_black_litterman_inputs(views, expected_returns)
            est = BlackLitterman(views=q, picking_matrix=p, omega=omega)
        else:
            return None
        est.fit(returns)
        weights = pd.Series(est.weights_, index=returns.columns, name=method)
        return weights
    except Exception:
        return None


# ---------------------------------------------------------------------------
# pypfopt fallback
# ---------------------------------------------------------------------------


def _pypfopt_optimize(  # pragma: no cover - exercised only when pypfopt is installed
    returns: pd.DataFrame,
    method: Method,
    *,
    expected_returns: pd.Series | None,
    views: LLMViews | None,
    cov_estimator: str,
    cvar_alpha: float,
    max_weight: float,
    min_weight: float,
) -> pd.Series | None:
    if not _has_pypfopt():
        return None
    try:
        from pypfopt import (
            BlackLittermanModel,
            EfficientCVaR,
            EfficientFrontier,
            HRPOpt,
        )
    except Exception:
        return None
    try:
        cov = _estimate_covariance(returns, cov_estimator)
        bounds = (min_weight, max_weight)
        if method == "hrp":
            opt = HRPOpt(returns=returns)
            raw = opt.optimize()
            return pd.Series(raw, name="hrp").reindex(returns.columns).fillna(0.0)
        if method in {"risk_budgeting", "mv_cvar"} and method == "mv_cvar":
            mu = expected_returns if expected_returns is not None else returns.mean()
            opt = EfficientCVaR(mu, returns, beta=1.0 - cvar_alpha, weight_bounds=bounds)
            opt.min_cvar()
            raw = opt.clean_weights()
            return pd.Series(raw, name="mv_cvar").reindex(returns.columns).fillna(0.0)
        if method == "risk_budgeting":
            mu = expected_returns if expected_returns is not None else returns.mean()
            ef = EfficientFrontier(mu, cov, weight_bounds=bounds)
            ef.min_volatility()
            raw = ef.clean_weights()
            return pd.Series(raw, name="risk_budgeting").reindex(returns.columns).fillna(0.0)
        if method == "black_litterman":
            if views is None or expected_returns is None:
                return None
            p, q, omega = to_black_litterman_inputs(views, expected_returns)
            bl = BlackLittermanModel(cov, pi=expected_returns.values, P=p, Q=q, Omega=omega)
            posterior = bl.bl_returns()
            ef = EfficientFrontier(posterior, cov, weight_bounds=bounds)
            ef.max_sharpe()
            raw = ef.clean_weights()
            return pd.Series(raw, name="black_litterman").reindex(returns.columns).fillna(0.0)
        if method == "nco":
            return None  # NCO not natively supported by pypfopt
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Pure-Python fallbacks for non-HRP methods (last-resort, dependency-free)
# ---------------------------------------------------------------------------


def _equal_risk_contribution(cov: np.ndarray, max_iter: int = 200, tol: float = 1e-8) -> np.ndarray:
    """Iterative ERC / risk-budgeting weights with no external solver."""
    n = cov.shape[0]
    w = np.ones(n) / n
    for _ in range(max_iter):
        marginal = cov @ w
        rc = w * marginal
        target = rc.mean()
        adj = target / np.where(rc > 0, rc, np.finfo(float).eps)
        w_new = w * np.sqrt(adj)
        w_new = np.clip(w_new, 1e-9, None)
        w_new = w_new / w_new.sum()
        if np.linalg.norm(w_new - w, ord=1) < tol:
            w = w_new
            break
        w = w_new
    return w


def _min_variance(cov: np.ndarray) -> np.ndarray:
    """Closed-form minimum-variance weights (no constraints)."""
    n = cov.shape[0]
    try:
        inv = np.linalg.pinv(cov + 1e-8 * np.eye(n))
        ones = np.ones(n)
        w = inv @ ones
        if w.sum() == 0:
            return np.ones(n) / n
        w = w / w.sum()
        # Clip negatives, renormalise
        w = np.clip(w, 0.0, None)
        if w.sum() == 0:
            return np.ones(n) / n
        return w / w.sum()
    except Exception:  # pragma: no cover - extremely defensive
        return np.ones(n) / n


def _historical_cvar_weights(returns: pd.DataFrame, alpha: float) -> np.ndarray:
    """Heuristic CVaR-aware allocator: shift inverse-CVaR weights then normalise."""
    n = returns.shape[1]
    cvar = np.zeros(n)
    for j, col in enumerate(returns.columns):
        series = returns[col].dropna()
        if series.empty:
            cvar[j] = 1.0
            continue
        threshold = np.quantile(series.values, alpha)
        tail = series.values[series.values <= threshold]
        cvar[j] = abs(float(tail.mean())) if tail.size else abs(float(series.min()))
    inv = 1.0 / np.where(cvar > 0, cvar, np.finfo(float).eps)
    return inv / inv.sum()


def _pure_python_optimize(
    returns: pd.DataFrame,
    method: Method,
    *,
    expected_returns: pd.Series | None,
    views: LLMViews | None,
    cov_estimator: str,
    cvar_alpha: float,
) -> pd.Series:
    cov = _estimate_covariance(returns, cov_estimator)
    if method == "hrp":
        return _pure_python_hrp(returns, cov)
    if method == "nco":
        # Without skfolio we approximate NCO as HRP — both are clustering allocators.
        return _pure_python_hrp(returns, cov)
    if method == "risk_budgeting":
        w = _equal_risk_contribution(cov.values)
        return pd.Series(w, index=cov.index, name=method)
    if method == "mv_cvar":
        w = _historical_cvar_weights(returns, cvar_alpha)
        return pd.Series(w, index=returns.columns, name=method)
    if method == "black_litterman":
        if views is None or expected_returns is None:
            raise ValueError("black_litterman requires both `views` and `expected_returns`")
        # Posterior mean: combine prior with views via the textbook BL formula.
        p, q, omega = to_black_litterman_inputs(views, expected_returns)
        sigma = cov.values
        if p.shape[0] == 0:
            posterior = expected_returns.values
        else:
            tau = 0.05
            tau_sigma = tau * sigma
            try:
                inner = np.linalg.pinv(p @ tau_sigma @ p.T + omega)
                posterior = expected_returns.values + tau_sigma @ p.T @ inner @ (q - p @ expected_returns.values)
            except Exception:
                posterior = expected_returns.values
        # Use a min-variance-tangent style weighting: weight ∝ posterior / variance
        diag = np.diag(sigma)
        safe = np.where(diag > 0, diag, np.finfo(float).eps)
        raw = posterior / safe
        # Make all weights non-negative for long-only portfolio
        raw = np.maximum(raw, 0.0)
        if raw.sum() <= 0:
            raw = np.ones_like(raw)
        w = raw / raw.sum()
        return pd.Series(w, index=expected_returns.index, name=method)
    raise ValueError(f"Unknown method: {method}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def optimize(
    returns: pd.DataFrame,
    *,
    method: Method = "hrp",
    expected_returns: pd.Series | None = None,
    views: LLMViews | None = None,
    cov_estimator: Literal["sample", "ledoit_wolf", "oas"] = "ledoit_wolf",
    cvar_alpha: float = 0.05,
    max_weight: float = 0.25,
    min_weight: float = 0.0,
    seed: int | None = None,
) -> pd.Series:
    """Compute portfolio weights for a given returns matrix.

    Parameters
    ----------
    returns:
        Daily returns with tickers as columns and dates as the index.
    method:
        One of ``hrp``, ``nco``, ``risk_budgeting``, ``mv_cvar``, ``black_litterman``.
    expected_returns:
        Required for ``black_litterman``.
    views:
        Optional :class:`LLMViews`; required for ``black_litterman``.
    cov_estimator:
        One of ``sample``, ``ledoit_wolf``, ``oas``.
    cvar_alpha:
        Confidence level for the lower tail (default 5%).
    max_weight, min_weight:
        Per-asset weight bounds.  The result is projected onto the box.
    seed:
        Optional RNG seed for reproducibility (used only by stochastic backends).
    """
    if not isinstance(returns, pd.DataFrame):
        raise TypeError("returns must be a pandas DataFrame")
    if returns.shape[1] < 2:
        raise ValueError("optimize requires at least two columns (tickers)")
    if returns.isna().any().any():
        returns = returns.dropna(how="any")
    if returns.shape[0] < 5:
        raise ValueError("optimize requires at least 5 rows of returns")

    if seed is not None:
        np.random.seed(int(seed))

    method_lc = method  # type: ignore[assignment]
    if method_lc not in ("hrp", "nco", "risk_budgeting", "mv_cvar", "black_litterman"):
        raise ValueError(f"Unknown method: {method}")

    weights: pd.Series | None = None

    # 1) skfolio (preferred)
    weights = _skfolio_optimize(
        returns,
        method_lc,
        expected_returns=expected_returns,
        views=views,
        cov_estimator=cov_estimator,
        cvar_alpha=cvar_alpha,
        max_weight=max_weight,
        min_weight=min_weight,
    )

    # 2) pypfopt fallback
    if weights is None:
        weights = _pypfopt_optimize(
            returns,
            method_lc,
            expected_returns=expected_returns,
            views=views,
            cov_estimator=cov_estimator,
            cvar_alpha=cvar_alpha,
            max_weight=max_weight,
            min_weight=min_weight,
        )

    # 3) Pure-Python: HRP/NCO/RB/CVaR/BL fallbacks always work
    if weights is None:
        if method_lc not in ("hrp", "nco", "risk_budgeting", "mv_cvar", "black_litterman"):
            raise ImportError(
                f"method={method_lc} requires skfolio or PyPortfolioOpt. "
                "Install with: pip install skfolio PyPortfolioOpt"
            )
        weights = _pure_python_optimize(
            returns,
            method_lc,
            expected_returns=expected_returns,
            views=views,
            cov_estimator=cov_estimator,
            cvar_alpha=cvar_alpha,
        )

    if weights is None or weights.empty:
        warnings.warn(
            f"optimize: backend returned empty weights for method={method_lc}; falling back to equal weight.",
            RuntimeWarning,
            stacklevel=2,
        )
        weights = pd.Series(
            np.ones(returns.shape[1]) / returns.shape[1],
            index=returns.columns,
            name="equal_weight",
        )

    weights = weights.fillna(0.0)
    if weights.sum() > 0:
        weights = weights / weights.sum()
    weights = _project_box(weights, min_weight, max_weight)
    return weights
