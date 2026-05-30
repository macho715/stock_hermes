from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
from scipy.optimize import minimize

TRADING_DAYS = 252
EPS = 1e-12


def ensure_outdir(path: str | os.PathLike) -> Path:
    out = Path(path)
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_json(obj: Dict, path: str | os.PathLike) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)


def _json_default(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (pd.Timestamp,)):
        return x.isoformat()
    if isinstance(x, (np.ndarray,)):
        return x.tolist()
    raise TypeError(f"Object of type {type(x)} is not JSON serializable")


def load_price_csv(path: str | os.PathLike, date_col: str = "Date") -> pd.DataFrame:
    """Load a wide price CSV: Date + asset columns.

    The first column is used as date when `date_col` is absent.
    Non-numeric columns other than the date column are ignored.
    """
    df = pd.read_csv(path)
    if date_col in df.columns:
        idx = pd.to_datetime(df[date_col])
        df = df.drop(columns=[date_col])
    else:
        idx = pd.to_datetime(df.iloc[:, 0])
        df = df.iloc[:, 1:]
    df.index = idx
    df = df.sort_index()
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna(axis=1, how="all")
    df = df.ffill().dropna(how="all")
    # Drop assets with too few valid prices.
    min_valid = max(10, int(len(df) * 0.60))
    df = df.loc[:, df.notna().sum() >= min_valid].ffill().bfill()
    if df.empty:
        raise ValueError("가격 CSV에서 유효한 자산 가격 컬럼을 찾지 못했습니다.")
    return df


def load_wide_csv(path: str | os.PathLike, date_col: str = "Date") -> pd.DataFrame:
    df = pd.read_csv(path)
    if date_col in df.columns:
        idx = pd.to_datetime(df[date_col])
        df = df.drop(columns=[date_col])
    else:
        idx = pd.to_datetime(df.iloc[:, 0])
        df = df.iloc[:, 1:]
    df.index = idx
    df = df.sort_index()
    return df.apply(pd.to_numeric, errors="coerce")


def returns_from_prices(prices: pd.DataFrame) -> pd.DataFrame:
    r = prices.pct_change(fill_method=None)
    r = r.replace([np.inf, -np.inf], np.nan).dropna(how="all")
    return r.fillna(0.0)


def max_drawdown(ret: pd.Series) -> float:
    if ret.empty:
        return 0.0
    nav = (1.0 + ret.fillna(0.0)).cumprod()
    peak = nav.cummax()
    dd = nav / peak - 1.0
    return float(dd.min())


def annualized_metrics(ret: pd.Series, turnover: Optional[pd.Series] = None, cost: Optional[pd.Series] = None) -> Dict[str, float]:
    ret = ret.dropna()
    if len(ret) == 0:
        return {
            "periods": 0,
            "ann_return": 0.0,
            "ann_vol": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "hit_rate": 0.0,
            "avg_turnover": 0.0,
            "ann_cost_drag": 0.0,
        }
    ann_ret = float(ret.mean() * TRADING_DAYS)
    ann_vol = float(ret.std(ddof=0) * math.sqrt(TRADING_DAYS))
    sharpe = float(ann_ret / ann_vol) if ann_vol > EPS else 0.0
    mdd = max_drawdown(ret)
    calmar = float(ann_ret / abs(mdd)) if abs(mdd) > EPS else 0.0
    out = {
        "periods": int(len(ret)),
        "ann_return": ann_ret,
        "ann_vol": ann_vol,
        "sharpe": sharpe,
        "max_drawdown": mdd,
        "calmar": calmar,
        "hit_rate": float((ret > 0).mean()),
        "avg_turnover": float(turnover.reindex(ret.index).fillna(0).mean()) if turnover is not None else 0.0,
        "ann_cost_drag": float(cost.reindex(ret.index).fillna(0).mean() * TRADING_DAYS) if cost is not None else 0.0,
    }
    return out


def shrink_cov(cov: pd.DataFrame | np.ndarray, shrinkage: float = 0.30) -> pd.DataFrame:
    if isinstance(cov, pd.DataFrame):
        cols = cov.columns
        arr = cov.values.astype(float)
    else:
        cols = None
        arr = np.asarray(cov, dtype=float)
    shrinkage = float(np.clip(shrinkage, 0.0, 1.0))
    diag = np.diag(np.diag(arr))
    shrunk = (1.0 - shrinkage) * arr + shrinkage * diag
    shrunk = np.nan_to_num(shrunk, nan=0.0, posinf=0.0, neginf=0.0)
    # Ensure strictly positive diagonal.
    d = np.diag(shrunk).copy()
    median_var = np.nanmedian(d[d > EPS]) if np.any(d > EPS) else 1e-6
    d = np.where(d > EPS, d, median_var)
    np.fill_diagonal(shrunk, d)
    if cols is not None:
        return pd.DataFrame(shrunk, index=cols, columns=cols)
    return pd.DataFrame(shrunk)


def cov_to_corr(cov: pd.DataFrame) -> pd.DataFrame:
    std = np.sqrt(np.maximum(np.diag(cov.values), EPS))
    corr = cov.values / np.outer(std, std)
    corr = np.clip(np.nan_to_num(corr, nan=0.0), -0.999, 0.999)
    np.fill_diagonal(corr, 1.0)
    return pd.DataFrame(corr, index=cov.index, columns=cov.columns)


def _get_quasi_diag(link: np.ndarray) -> List[int]:
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    num_items = link[-1, 3]
    while sort_ix.max() >= num_items:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        df0 = sort_ix[sort_ix >= num_items]
        i = df0.index
        j = df0.values - int(num_items)
        sort_ix[i] = link[j, 0]
        df1 = pd.Series(link[j, 1], index=i + 1)
        sort_ix = pd.concat([sort_ix, df1]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()


def inverse_variance_weights(cov: pd.DataFrame) -> pd.Series:
    diag = np.diag(cov.values)
    inv_diag = 1.0 / np.maximum(diag, EPS)
    w = inv_diag / inv_diag.sum()
    return pd.Series(w, index=cov.index)


def cluster_variance(cov: pd.DataFrame, cluster_items: Sequence[str]) -> float:
    sub = cov.loc[cluster_items, cluster_items]
    w = inverse_variance_weights(sub).values.reshape(-1, 1)
    return float((w.T @ sub.values @ w).item())


def hrp_weights(cov: pd.DataFrame) -> pd.Series:
    """Hierarchical Risk Parity weights using recursive bisection."""
    cov = shrink_cov(cov, 0.0)
    assets = list(cov.columns)
    if len(assets) == 1:
        return pd.Series([1.0], index=assets)
    corr = cov_to_corr(cov)
    dist = np.sqrt(np.maximum(0.0, 0.5 * (1.0 - corr.values)))
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    link = linkage(condensed, method="single")
    sort_ix = _get_quasi_diag(link)
    sorted_assets = [assets[i] for i in sort_ix]
    weights = pd.Series(1.0, index=sorted_assets)
    clusters = [sorted_assets]
    while clusters:
        next_clusters = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            split = len(cluster) // 2
            left = cluster[:split]
            right = cluster[split:]
            var_left = cluster_variance(cov, left)
            var_right = cluster_variance(cov, right)
            alpha = 1.0 - var_left / max(var_left + var_right, EPS)
            weights[left] *= alpha
            weights[right] *= 1.0 - alpha
            next_clusters.extend([left, right])
        clusters = next_clusters
    weights = weights.reindex(assets).fillna(0.0)
    return weights / max(weights.sum(), EPS)


def min_variance_weights(cov: pd.DataFrame, max_weight: float = 1.0, long_only: bool = True) -> pd.Series:
    assets = list(cov.columns)
    n = len(assets)
    if n == 1:
        return pd.Series([1.0], index=assets)
    x0 = np.repeat(1.0 / n, n)
    bounds = [(0.0 if long_only else -max_weight, max_weight) for _ in range(n)]
    cons = ({"type": "eq", "fun": lambda w: np.sum(w) - 1.0},)

    def obj(w):
        return float(w @ cov.values @ w)

    res = minimize(obj, x0, method="SLSQP", bounds=bounds, constraints=cons, options={"maxiter": 500, "ftol": 1e-10})
    if not res.success:
        return pd.Series(x0, index=assets)
    w = pd.Series(res.x, index=assets)
    return cap_and_normalize(w, max_weight=max_weight, long_only=long_only)


def cap_and_normalize(w: pd.Series, max_weight: float = 1.0, long_only: bool = True, target_sum: float = 1.0) -> pd.Series:
    w = w.astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if long_only:
        w = w.clip(lower=0.0)
        if w.sum() <= EPS:
            w[:] = 1.0 / len(w)
        # Iteratively cap and redistribute excess.
        w = w / w.sum() * target_sum
        for _ in range(20):
            over = w > max_weight
            if not over.any():
                break
            excess = float((w[over] - max_weight).sum())
            w[over] = max_weight
            under = ~over
            if under.sum() == 0 or excess <= EPS:
                break
            room = max_weight - w[under]
            if room.sum() <= EPS:
                break
            w[under] += excess * room / room.sum()
        total = w.sum()
        if total > EPS:
            w = w / total * target_sum
        return w
    # Long/short: cap gross exposure.
    w = w.clip(lower=-max_weight, upper=max_weight)
    gross = w.abs().sum()
    if gross > target_sum and gross > EPS:
        w = w / gross * target_sum
    return w


def apply_turnover_cap(target: pd.Series, prev: pd.Series, cap: float) -> pd.Series:
    target, prev = target.align(prev, join="outer", fill_value=0.0)
    turnover = float((target - prev).abs().sum())
    if cap is None or cap <= 0 or turnover <= cap + EPS:
        return target
    scale = cap / max(turnover, EPS)
    return prev + scale * (target - prev)


def transaction_cost(prev: pd.Series, target: pd.Series, cost_bps: float | pd.Series = 5.0) -> float:
    target, prev = target.align(prev, join="outer", fill_value=0.0)
    delta = (target - prev).abs()
    if isinstance(cost_bps, pd.Series):
        c = cost_bps.reindex(delta.index).fillna(float(cost_bps.mean()) if len(cost_bps) else 5.0) / 10000.0
        return float((delta * c).sum())
    return float(delta.sum() * float(cost_bps) / 10000.0)


def realized_portfolio_return(prev_w: pd.Series, row_ret: pd.Series) -> float:
    prev_w, row_ret = prev_w.align(row_ret, join="inner")
    if len(prev_w) == 0:
        return 0.0
    return float((prev_w * row_ret).sum())


def annualized_vol(ret: pd.Series | np.ndarray) -> float:
    arr = np.asarray(ret, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float(np.nanstd(arr, ddof=0) * math.sqrt(TRADING_DAYS))


def make_demo_prices(n_days: int = 900, seed: int = 42) -> pd.DataFrame:
    """Generate deterministic synthetic ETF-like prices for smoke tests and demos."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    assets = ["SPY", "QQQ", "IWM", "TLT", "IEF", "GLD", "DBC", "UUP"]
    n = len(assets)
    # Three latent regimes: normal, risk-off, inflation shock.
    regime = np.zeros(n_days, dtype=int)
    for t in range(1, n_days):
        if rng.random() < 0.015:
            regime[t] = rng.integers(0, 3)
        else:
            regime[t] = regime[t - 1]
    mu = np.array([
        [0.00035, 0.00045, 0.00040, 0.00010, 0.00008, 0.00015, 0.00012, 0.00002],
        [-0.00055, -0.00070, -0.00080, 0.00045, 0.00030, 0.00035, -0.00020, 0.00025],
        [0.00005, -0.00005, 0.00000, -0.00035, -0.00020, 0.00045, 0.00065, 0.00025],
    ])
    vols = np.array([
        [0.010, 0.012, 0.014, 0.009, 0.006, 0.010, 0.012, 0.005],
        [0.020, 0.024, 0.026, 0.014, 0.010, 0.016, 0.018, 0.008],
        [0.015, 0.017, 0.020, 0.013, 0.009, 0.017, 0.022, 0.007],
    ])
    base_corr = np.full((n, n), 0.20)
    np.fill_diagonal(base_corr, 1.0)
    # Bonds negatively correlated with equities.
    for i in [0, 1, 2]:
        for j in [3, 4]:
            base_corr[i, j] = base_corr[j, i] = -0.25
    # Commodities and gold moderate correlation.
    base_corr[5, 6] = base_corr[6, 5] = 0.30
    chol = np.linalg.cholesky(base_corr + np.eye(n) * 1e-6)
    rets = np.zeros((n_days, n))
    for t in range(n_days):
        s = regime[t]
        z = rng.standard_normal(n) @ chol.T
        rets[t] = mu[s] + vols[s] * z
    prices = 100.0 * pd.DataFrame(1.0 + rets, index=dates, columns=assets).cumprod()
    return prices


def save_demo_prices(path: str | os.PathLike, n_days: int = 900, seed: int = 42) -> Path:
    prices = make_demo_prices(n_days=n_days, seed=seed)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    prices.reset_index(names="Date").to_csv(out, index=False)
    return out
