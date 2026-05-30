#!/usr/bin/env python3
"""
A. Regime-aware HRP/HMV-CVT

Reference implementation for a production-oriented core allocator:
1) infer market regime probabilities with a Gaussian Mixture regime model,
2) blend regime-conditioned mean/covariance estimates,
3) build robust HRP / HMV initial weights,
4) solve a cost-aware conditional volatility targeting allocation,
5) emit weights, orders, regime probabilities, and backtest metrics.

Input CSV format:
    Date, SPY, QQQ, TLT, GLD, ...

Run:
    python algos/a_regime_hrp_hmv_cvt.py --prices data/prices.csv --outdir output/a
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

# Allow both `python -m algos...` and direct file execution.
THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from algos.common import (  # noqa: E402
    EPS,
    TRADING_DAYS,
    annualized_metrics,
    annualized_vol,
    apply_turnover_cap,
    cap_and_normalize,
    ensure_outdir,
    hrp_weights,
    load_price_csv,
    min_variance_weights,
    realized_portfolio_return,
    returns_from_prices,
    shrink_cov,
    transaction_cost,
    write_json,
)


CASH = "__CASH__"
POLICY_VERDICT = "HOLD_DIAGNOSTIC_ONLY"


@dataclass
class RegimeMoment:
    probabilities: pd.Series
    expected_return: pd.Series
    covariance: pd.DataFrame
    regime_vol: float
    target_vol: float
    latest_regime: int


@dataclass
class AllocationResult:
    weights: pd.Series
    regime_probabilities: pd.Series
    target_vol: float
    realized_vol_estimate: float
    optimizer_success: bool
    optimizer_message: str


def allocation_diagnostics(weights: pd.Series) -> Dict[str, object]:
    """Summarize latest exposure without changing the A policy verdict."""
    clean = weights.astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    cash_weight = float(clean.get(CASH, 0.0))
    risky = clean.drop(labels=[CASH], errors="ignore")
    gross_risky_exposure = float(risky.abs().sum())
    return {
        "cash_weight": cash_weight,
        "gross_risky_exposure": gross_risky_exposure,
        "cash_collapse_warning": bool(cash_weight >= 0.95 or gross_risky_exposure <= 0.05),
        "policy_verdict": POLICY_VERDICT,
    }


def build_regime_features(returns: pd.DataFrame, extra_features: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Create point-in-time regime features from returns.

    Features are intentionally simple and interpretable:
    - cross-asset average return momentum
    - realized volatility at two horizons
    - drawdown proxy
    - cross-sectional dispersion
    """
    market = returns.mean(axis=1)
    nav = (1.0 + market).cumprod()
    drawdown_63 = nav / nav.rolling(63, min_periods=20).max() - 1.0
    feat = pd.DataFrame(index=returns.index)
    feat["mkt_ret_5"] = market.rolling(5, min_periods=3).mean()
    feat["mkt_ret_21"] = market.rolling(21, min_periods=10).mean()
    feat["vol_21"] = market.rolling(21, min_periods=10).std(ddof=0) * math.sqrt(TRADING_DAYS)
    feat["vol_63"] = market.rolling(63, min_periods=20).std(ddof=0) * math.sqrt(TRADING_DAYS)
    feat["drawdown_63"] = drawdown_63
    feat["dispersion_21"] = returns.std(axis=1).rolling(21, min_periods=10).mean()
    if extra_features is not None and not extra_features.empty:
        aligned = extra_features.reindex(feat.index).ffill()
        for c in aligned.columns:
            feat[f"x_{c}"] = pd.to_numeric(aligned[c], errors="coerce")
    feat = feat.replace([np.inf, -np.inf], np.nan).dropna()
    return feat


def fit_regime_moments(
    returns_window: pd.DataFrame,
    feature_window: pd.DataFrame,
    n_regimes: int,
    shrinkage: float,
    base_target_vol: float,
    conditional_vol: bool = True,
    random_state: int = 42,
) -> RegimeMoment:
    """Fit a GMM regime model and estimate probability-weighted moments."""
    common_idx = returns_window.index.intersection(feature_window.index)
    rw = returns_window.loc[common_idx].dropna(how="all").fillna(0.0)
    fw = feature_window.loc[common_idx].dropna()
    common_idx = rw.index.intersection(fw.index)
    rw = rw.loc[common_idx]
    fw = fw.loc[common_idx]
    if len(fw) < max(30, n_regimes * 10):
        raise ValueError("Regime 학습 표본이 부족합니다. lookback 또는 데이터 기간을 늘리십시오.")

    scaler = StandardScaler()
    x = scaler.fit_transform(fw.values)
    k = int(min(max(1, n_regimes), max(1, len(fw) // 20)))
    if k <= 1:
        probs = pd.Series([1.0], index=[0], name=fw.index[-1])
        mu = rw.mean()
        cov = shrink_cov(rw.cov(), shrinkage)
        market_vol = annualized_vol(rw.mean(axis=1))
        return RegimeMoment(probs, mu, cov, market_vol, base_target_vol, 0)

    gmm = GaussianMixture(n_components=k, covariance_type="full", random_state=random_state, reg_covar=1e-5, n_init=5)
    gmm.fit(x)
    labels = pd.Series(gmm.predict(x), index=fw.index)
    last_prob = pd.Series(gmm.predict_proba(x[-1:].reshape(1, -1))[0], index=range(k))

    mus = []
    covs = []
    vols = []
    for s in range(k):
        idx = labels[labels == s].index
        # Guardrail: if a regime has too few observations, use the full window.
        sub = rw.loc[idx] if len(idx) >= max(10, len(rw.columns) + 2) else rw
        mu_s = sub.mean()
        cov_s = shrink_cov(sub.cov(), shrinkage)
        mus.append(mu_s)
        covs.append(cov_s)
        vols.append(annualized_vol(sub.mean(axis=1)))

    mu_hat = sum(float(last_prob.iloc[s]) * mus[s] for s in range(k))
    cov_hat = pd.DataFrame(0.0, index=rw.columns, columns=rw.columns)
    for s in range(k):
        diff = (mus[s] - mu_hat).values.reshape(-1, 1)
        cov_hat += float(last_prob.iloc[s]) * (covs[s] + pd.DataFrame(diff @ diff.T, index=rw.columns, columns=rw.columns))
    cov_hat = shrink_cov(cov_hat, shrinkage)

    vols_arr = np.asarray(vols, dtype=float)
    expected_regime_vol = float(np.dot(last_prob.values, vols_arr))
    target_vol = base_target_vol
    if conditional_vol and len(vols_arr) > 1:
        q25, q75 = np.quantile(vols_arr, [0.25, 0.75])
        if expected_regime_vol >= q75:
            target_vol = base_target_vol * 0.75
        elif expected_regime_vol <= q25:
            target_vol = base_target_vol * 1.10
    latest_regime = int(last_prob.idxmax())
    last_prob.index = [f"regime_{i}" for i in last_prob.index]
    return RegimeMoment(last_prob, mu_hat, cov_hat, expected_regime_vol, target_vol, latest_regime)


def cvar_penalty(sample_returns: pd.DataFrame, weights: np.ndarray, alpha: float = 0.95) -> float:
    pr = sample_returns.values @ weights
    if len(pr) < 20:
        return 0.0
    q = np.quantile(pr, 1.0 - alpha)
    tail = pr[pr <= q]
    if len(tail) == 0:
        return 0.0
    return float(-tail.mean())


def solve_cost_aware_allocation(
    mu: pd.Series,
    cov: pd.DataFrame,
    returns_window: pd.DataFrame,
    prev_weights: pd.Series,
    target_vol: float,
    max_weight: float,
    risk_aversion: float,
    turnover_penalty: float,
    cvar_lambda: float,
    hmv_blend: float,
    cost_bps: float,
    turnover_cap: float,
    allow_cash: bool,
) -> AllocationResult:
    assets = list(mu.index)
    n = len(assets)
    cov = cov.loc[assets, assets]
    prev_risky = prev_weights.reindex(assets).fillna(0.0)

    w_hrp = hrp_weights(cov)
    w_mv = min_variance_weights(cov, max_weight=max_weight, long_only=True)
    blend = float(np.clip(hmv_blend, 0.0, 1.0))
    w0_risky = cap_and_normalize((1.0 - blend) * w_hrp + blend * w_mv, max_weight=max_weight, long_only=True)

    # Add cash to make conditional volatility targeting always feasible.
    opt_assets = assets + ([CASH] if allow_cash else [])
    prev = prev_weights.reindex(opt_assets).fillna(0.0)
    if allow_cash and prev.abs().sum() <= EPS:
        prev.loc[CASH] = 1.0
    if allow_cash:
        cash0 = max(0.0, 1.0 - float(w0_risky.sum()))
        x0 = np.r_[w0_risky.values, cash0]
    else:
        x0 = w0_risky.values

    # Scale initial risky allocation if volatility exceeds target.
    risky_vol0 = math.sqrt(max(float(w0_risky.values @ cov.values @ w0_risky.values), 0.0)) * math.sqrt(TRADING_DAYS)
    if allow_cash and risky_vol0 > target_vol > EPS:
        scale = target_vol / risky_vol0
        x0[:n] *= scale
        x0[-1] = 1.0 - x0[:n].sum()

    bounds = [(0.0, max_weight) for _ in range(n)] + ([(0.0, 1.0)] if allow_cash else [])

    def unpack(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        risky = np.asarray(x[:n], dtype=float)
        return risky, np.asarray(x, dtype=float)

    def obj(x: np.ndarray) -> float:
        risky, allw = unpack(x)
        ret_term = float(mu.values @ risky) * TRADING_DAYS
        risk_term = float(risky @ cov.values @ risky) * TRADING_DAYS
        delta = np.abs(allw - prev.values)
        tc_term = float(delta.sum() * cost_bps / 10000.0)
        cvar = cvar_penalty(returns_window[assets], risky, alpha=0.95) * TRADING_DAYS
        utility = ret_term - risk_aversion * risk_term - turnover_penalty * tc_term - cvar_lambda * cvar
        return -utility

    def budget_con(x: np.ndarray) -> float:
        return float(np.sum(x) - 1.0)

    def vol_con(x: np.ndarray) -> float:
        risky = np.asarray(x[:n], dtype=float)
        vol = math.sqrt(max(float(risky @ cov.values @ risky), 0.0)) * math.sqrt(TRADING_DAYS)
        return float(target_vol - vol)

    constraints = [
        {"type": "eq", "fun": budget_con},
        {"type": "ineq", "fun": vol_con},
    ]

    res = minimize(
        obj,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 700, "ftol": 1e-9, "disp": False},
    )
    if res.success and np.all(np.isfinite(res.x)):
        raw = pd.Series(res.x, index=opt_assets)
        success = True
        msg = res.message
    else:
        raw = pd.Series(x0, index=opt_assets)
        success = False
        msg = str(res.message)

    raw = apply_turnover_cap(raw, prev, turnover_cap)
    # Re-normalize after turnover scaling. If allow_cash, cash absorbs residual.
    if allow_cash:
        raw[assets] = raw[assets].clip(lower=0.0, upper=max_weight)
        raw[CASH] = max(0.0, 1.0 - raw[assets].sum())
        if raw.sum() > EPS:
            raw = raw / raw.sum()
    else:
        raw = cap_and_normalize(raw, max_weight=max_weight, long_only=True)
    risky = raw.reindex(assets).fillna(0.0).values
    realized_vol = math.sqrt(max(float(risky @ cov.values @ risky), 0.0)) * math.sqrt(TRADING_DAYS)
    return AllocationResult(raw, pd.Series(dtype=float), target_vol, realized_vol, success, msg)


def compute_allocation(
    returns_window: pd.DataFrame,
    feature_window: pd.DataFrame,
    prev_weights: pd.Series,
    args: argparse.Namespace,
) -> AllocationResult:
    moment = fit_regime_moments(
        returns_window=returns_window,
        feature_window=feature_window,
        n_regimes=args.n_regimes,
        shrinkage=args.shrinkage,
        base_target_vol=args.target_vol,
        conditional_vol=not args.disable_conditional_vol,
        random_state=args.random_state,
    )
    alloc = solve_cost_aware_allocation(
        mu=moment.expected_return,
        cov=moment.covariance,
        returns_window=returns_window,
        prev_weights=prev_weights,
        target_vol=moment.target_vol,
        max_weight=args.max_weight,
        risk_aversion=args.risk_aversion,
        turnover_penalty=args.turnover_penalty,
        cvar_lambda=args.cvar_lambda,
        hmv_blend=args.hmv_blend,
        cost_bps=args.cost_bps,
        turnover_cap=args.turnover_cap,
        allow_cash=not args.no_cash,
    )
    alloc.regime_probabilities = moment.probabilities
    alloc.target_vol = moment.target_vol
    return alloc


def run_backtest(prices: pd.DataFrame, args: argparse.Namespace, extra_features: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame | pd.Series | Dict]:
    returns = returns_from_prices(prices)
    features = build_regime_features(returns, extra_features=extra_features)
    assets = list(returns.columns)
    opt_assets = assets + ([] if args.no_cash else [CASH])
    current_w = pd.Series(0.0, index=opt_assets)
    if not args.no_cash:
        current_w[CASH] = 1.0
    else:
        current_w[assets] = 1.0 / len(assets)

    net_returns = []
    gross_returns = []
    costs = []
    turnovers = []
    weights_history = []
    regime_rows = []
    order_rows = []

    start_i = max(args.lookback, 80)
    for i in range(start_i, len(returns)):
        date = returns.index[i]
        cost_today = 0.0
        turnover_today = 0.0
        should_rebalance = ((i - start_i) % args.rebalance_days == 0)
        if should_rebalance:
            window = returns.iloc[i - args.lookback : i]
            fwin = features.loc[features.index.intersection(window.index)]
            if len(fwin) >= max(30, args.n_regimes * 10):
                prev_w = current_w.copy()
                alloc = compute_allocation(window, fwin, current_w, args)
                current_w = alloc.weights.reindex(opt_assets).fillna(0.0)
                cost_today = transaction_cost(prev_w, current_w, args.cost_bps)
                turnover_today = float((current_w.reindex(opt_assets).fillna(0.0) - prev_w.reindex(opt_assets).fillna(0.0)).abs().sum())
                weights_history.append(current_w.rename(date))
                regime_rows.append(pd.concat([
                    alloc.regime_probabilities,
                    pd.Series({
                        "target_vol": alloc.target_vol,
                        "realized_vol_estimate": alloc.realized_vol_estimate,
                        "optimizer_success": float(alloc.optimizer_success),
                    }),
                ]).rename(date))
                delta = (current_w - prev_w).reindex(opt_assets).fillna(0.0)
                for asset, d in delta.items():
                    if abs(d) > 1e-8:
                        order_rows.append({
                            "Date": date,
                            "Asset": asset,
                            "prev_weight": float(prev_w.reindex(opt_assets).fillna(0.0).loc[asset]),
                            "target_weight": float(current_w.loc[asset]),
                            "delta_weight": float(d),
                            "estimated_cost": float(abs(d) * args.cost_bps / 10000.0),
                        })
        risky_w = current_w.reindex(assets).fillna(0.0)
        gross_ret = realized_portfolio_return(risky_w, returns.iloc[i])
        net_ret = gross_ret - cost_today
        gross_returns.append((date, gross_ret))
        net_returns.append((date, net_ret))
        costs.append((date, cost_today))
        turnovers.append((date, turnover_today))

    net = pd.Series(dict(net_returns), name="net_return").sort_index()
    gross = pd.Series(dict(gross_returns), name="gross_return").sort_index()
    cost = pd.Series(dict(costs), name="transaction_cost").sort_index()
    turnover = pd.Series(dict(turnovers), name="turnover").sort_index()
    weights = pd.DataFrame(weights_history).sort_index() if weights_history else pd.DataFrame(columns=opt_assets)
    regimes = pd.DataFrame(regime_rows).sort_index() if regime_rows else pd.DataFrame()
    orders = pd.DataFrame(order_rows)
    metrics = annualized_metrics(net, turnover=turnover, cost=cost)
    metrics.update({
        "gross_ann_return": annualized_metrics(gross)["ann_return"],
        "rebalance_days": int(args.rebalance_days),
        "lookback": int(args.lookback),
        "n_assets": int(len(assets)),
    })
    return {
        "net_returns": net,
        "gross_returns": gross,
        "costs": cost,
        "turnover": turnover,
        "weights": weights,
        "regimes": regimes,
        "orders": orders,
        "metrics": metrics,
    }


def latest_allocation(prices: pd.DataFrame, args: argparse.Namespace, extra_features: Optional[pd.DataFrame] = None) -> AllocationResult:
    returns = returns_from_prices(prices)
    features = build_regime_features(returns, extra_features=extra_features)
    window = returns.iloc[-args.lookback :]
    fwin = features.loc[features.index.intersection(window.index)]
    assets = list(returns.columns)
    opt_assets = assets + ([] if args.no_cash else [CASH])
    prev = pd.Series(0.0, index=opt_assets)
    if args.prev_weights:
        prev_df = pd.read_csv(args.prev_weights)
        if {"Asset", "Weight"}.issubset(prev_df.columns):
            prev = pd.Series(prev_df["Weight"].values, index=prev_df["Asset"].astype(str)).reindex(opt_assets).fillna(0.0)
    elif not args.no_cash:
        prev[CASH] = 1.0
    else:
        prev[assets] = 1.0 / len(assets)
    return compute_allocation(window, fwin, prev, args)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="A Regime-aware HRP/HMV-CVT allocator")
    p.add_argument("--prices", required=True, help="Wide price CSV. Columns: Date + assets")
    p.add_argument("--features", default=None, help="Optional wide exogenous regime feature CSV. Columns: Date + features")
    p.add_argument("--prev-weights", default=None, help="Optional CSV with Asset,Weight for latest allocation")
    p.add_argument("--outdir", default="output/a_regime_hrp_hmv_cvt")
    p.add_argument("--lookback", type=int, default=252)
    p.add_argument("--rebalance-days", type=int, default=5)
    p.add_argument("--n-regimes", type=int, default=3)
    p.add_argument("--target-vol", type=float, default=0.10)
    p.add_argument("--max-weight", type=float, default=0.25)
    p.add_argument("--shrinkage", type=float, default=0.35)
    p.add_argument("--hmv-blend", type=float, default=0.30, help="Blend HRP with constrained min-variance, 0=HRP, 1=HMV")
    p.add_argument("--risk-aversion", type=float, default=5.0)
    p.add_argument("--turnover-penalty", type=float, default=25.0)
    p.add_argument("--cvar-lambda", type=float, default=0.5)
    p.add_argument("--cost-bps", type=float, default=5.0)
    p.add_argument("--turnover-cap", type=float, default=0.25)
    p.add_argument("--disable-conditional-vol", action="store_true")
    p.add_argument("--no-cash", action="store_true", help="Force fully invested long-only weights; vol target may be infeasible")
    p.add_argument("--random-state", type=int, default=42)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    outdir = ensure_outdir(args.outdir)
    prices = load_price_csv(args.prices)
    extra_features = None
    if args.features:
        from algos.common import load_wide_csv
        extra_features = load_wide_csv(args.features)

    bt = run_backtest(prices, args, extra_features=extra_features)
    latest = latest_allocation(prices, args, extra_features=extra_features)

    bt["net_returns"].to_csv(outdir / "backtest_net_returns.csv", index_label="Date")
    bt["gross_returns"].to_csv(outdir / "backtest_gross_returns.csv", index_label="Date")
    bt["costs"].to_csv(outdir / "transaction_costs.csv", index_label="Date")
    bt["turnover"].to_csv(outdir / "turnover.csv", index_label="Date")
    bt["weights"].to_csv(outdir / "weights_history.csv", index_label="Date")
    bt["regimes"].to_csv(outdir / "regime_probabilities.csv", index_label="Date")
    bt["orders"].to_csv(outdir / "orders.csv", index=False)
    latest.weights.rename("Weight").reset_index().rename(columns={"index": "Asset"}).to_csv(outdir / "latest_weights.csv", index=False)
    latest.regime_probabilities.rename("Probability").reset_index().rename(columns={"index": "Regime"}).to_csv(outdir / "latest_regime_probabilities.csv", index=False)
    write_json(bt["metrics"], outdir / "metrics.json")

    summary = {
        "algorithm": "A Regime-aware HRP/HMV-CVT",
        "latest_date": str(prices.index[-1].date()),
        "latest_target_vol": latest.target_vol,
        "latest_realized_vol_estimate": latest.realized_vol_estimate,
        "optimizer_success": latest.optimizer_success,
        "optimizer_message": latest.optimizer_message,
        **allocation_diagnostics(latest.weights),
        "metrics": bt["metrics"],
    }
    write_json(summary, outdir / "summary.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
