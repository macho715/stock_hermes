#!/usr/bin/env python3
"""
C. Decision-focused Multi-period Optimizer

Reference implementation for a model-predictive, decision-focused allocator:
1) estimate or load a multi-period return forecast path,
2) solve an H-step portfolio utility optimization with risk and turnover costs,
3) execute only the first-step target weight, then replan on the next rebalance,
4) tune and report on portfolio utility, not prediction MSE.

Input CSV format:
    Date, SPY, QQQ, TLT, GLD, ...

Run:
    python algos/c_decision_focused_multi_period_optimizer.py --prices data/prices.csv --outdir output/c
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize

THIS_DIR = Path(__file__).resolve().parent
ROOT_DIR = THIS_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from algos.common import (  # noqa: E402
    EPS,
    TRADING_DAYS,
    annualized_metrics,
    apply_turnover_cap,
    ensure_outdir,
    hrp_weights,
    load_price_csv,
    load_wide_csv,
    realized_portfolio_return,
    returns_from_prices,
    shrink_cov,
    transaction_cost,
    write_json,
)

CASH = "__CASH__"


@dataclass
class MultiPeriodPlan:
    plan: pd.DataFrame
    first_step: pd.Series
    objective_value: float
    success: bool
    message: str
    expected_step_utility: float
    fallback_used: bool
    fallback_reason: str
    optimizer_iterations: int


def _fill_to_budget_with_cap(risky: pd.Series, max_weight: float) -> pd.Series:
    """Return a long-only row that respects max_weight and sums to one when feasible."""
    row = risky.clip(lower=0.0, upper=max_weight).astype(float)
    capacity = max_weight - row
    remaining = 1.0 - float(row.sum())
    while remaining > 1e-10 and float(capacity.clip(lower=0.0).sum()) > EPS:
        room = capacity.clip(lower=0.0)
        add = room / max(float(room.sum()), EPS) * remaining
        add = pd.Series(np.minimum(add.values, room.values), index=row.index)
        row += add
        capacity = max_weight - row
        remaining = 1.0 - float(row.sum())
    total = float(row.sum())
    if total > EPS and abs(total - 1.0) > 1e-8:
        row = row / total
    return row


def _clip_initial_path(x0: np.ndarray, horizon: int, opt_assets: Sequence[str], assets: Sequence[str], max_weight: float, allow_cash: bool) -> np.ndarray:
    """Clip the optimizer starting point into the explicit bounds before scipy runs."""
    frame = pd.DataFrame(np.asarray(x0, dtype=float).reshape(horizon, len(opt_assets)), columns=opt_assets)
    for idx in frame.index:
        risky = frame.loc[idx, assets].clip(lower=0.0, upper=max_weight)
        if allow_cash:
            if float(risky.sum()) > 1.0:
                risky = risky / max(float(risky.sum()), EPS)
            frame.loc[idx, assets] = risky
            frame.loc[idx, CASH] = max(0.0, 1.0 - float(risky.sum()))
        else:
            frame.loc[idx, assets] = _fill_to_budget_with_cap(risky, max_weight)
    return frame.values.reshape(-1)


def estimate_forecast_path(
    returns_window: pd.DataFrame,
    horizon: int,
    rebalance_days: int,
    forecast_decay: float,
    shrink_mu: float,
    prediction_row: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Return H x N expected return path for rebalance-step returns.

    If prediction_row is provided, it is interpreted as one rebalance-step forecast.
    Otherwise an EWMA mean return forecast is used as a replaceable baseline.
    """
    assets = list(returns_window.columns)
    if prediction_row is not None:
        base = prediction_row.reindex(assets).fillna(0.0).astype(float)
    else:
        ewm_mu_daily = returns_window.ewm(span=min(60, max(10, len(returns_window) // 3)), min_periods=10).mean().iloc[-1]
        hist_mu_daily = returns_window.tail(min(252, len(returns_window))).mean()
        base_daily = (1.0 - shrink_mu) * ewm_mu_daily + shrink_mu * hist_mu_daily
        base = base_daily * rebalance_days
    rows = []
    for h in range(horizon):
        rows.append(base * (forecast_decay ** h))
    return pd.DataFrame(rows, index=[f"h{h+1}" for h in range(horizon)], columns=assets)


def empirical_cvar(returns_window: pd.DataFrame, weights: np.ndarray, alpha: float = 0.95) -> float:
    if returns_window.empty:
        return 0.0
    pr = returns_window.values @ weights
    if len(pr) < 20:
        return 0.0
    q = np.quantile(pr, 1.0 - alpha)
    tail = pr[pr <= q]
    if len(tail) == 0:
        return 0.0
    return float(-tail.mean())


def solve_multi_period_plan(
    mu_path: pd.DataFrame,
    cov_step: pd.DataFrame,
    returns_window: pd.DataFrame,
    prev_weights: pd.Series,
    horizon: int,
    gamma: float,
    risk_aversion: float,
    turnover_penalty: float,
    cvar_lambda: float,
    cost_bps: float,
    max_weight: float,
    turnover_budget: float,
    target_vol: float,
    rebalance_days: int,
    allow_cash: bool = True,
    optimizer_maxiter: int = 1000,
) -> MultiPeriodPlan:
    assets = list(mu_path.columns)
    n = len(assets)
    opt_assets = assets + ([CASH] if allow_cash else [])
    m = len(opt_assets)
    cov_step = cov_step.loc[assets, assets]
    prev = prev_weights.reindex(opt_assets).fillna(0.0)
    if prev.abs().sum() <= EPS:
        if allow_cash:
            prev[CASH] = 1.0
        else:
            prev[assets] = 1.0 / n
    # Initial path: HRP risky allocation scaled to target vol, with cash residual.
    try:
        w_hrp = hrp_weights(cov_step)
    except Exception:
        w_hrp = pd.Series(1.0 / n, index=assets)
    annual_factor = math.sqrt(TRADING_DAYS / max(float(rebalance_days), 1.0))
    risky0 = w_hrp.clip(lower=0.0)
    if risky0.sum() > EPS:
        risky0 = risky0 / risky0.sum()
    if allow_cash:
        x_row = pd.Series(0.0, index=opt_assets)
        x_row[assets] = risky0.values
        # Conservative initial scaling if the step variance implies high annual vol.
        annual_vol0 = math.sqrt(max(float(risky0.values @ cov_step.values @ risky0.values), 0.0)) * annual_factor
        if target_vol > EPS and annual_vol0 > target_vol:
            scale = target_vol / annual_vol0
            x_row[assets] *= scale
        x_row[CASH] = max(0.0, 1.0 - x_row[assets].sum())
        x0 = np.tile(x_row.values, horizon)
    else:
        x0 = np.tile(risky0.values, horizon)
        m = n
        opt_assets = assets

    bounds = []
    for _ in range(horizon):
        bounds.extend([(0.0, max_weight) for _ in range(n)])
        if allow_cash:
            bounds.append((0.0, 1.0))

    x0 = _clip_initial_path(x0, horizon, opt_assets, assets, max_weight, allow_cash)

    def mat(x: np.ndarray) -> np.ndarray:
        return np.asarray(x, dtype=float).reshape(horizon, m)

    def risky(row: np.ndarray) -> np.ndarray:
        return row[:n]

    def objective(x: np.ndarray) -> float:
        # Penalty-form MPC objective. This is materially faster than a hard-
        # constrained non-smooth SLSQP solve and is adequate for research /
        # paper-trading dry-runs. Hard limits should still be enforced by a
        # separate pre-trade risk engine before live execution.
        wmat = mat(x)
        total_utility = 0.0
        penalty = 0.0
        prev_row = prev.values
        budget_penalty = 250.0
        turnover_violation_penalty = 25.0
        vol_violation_penalty = 25.0
        smooth_eps = 1e-8
        for h in range(horizon):
            row = wmat[h]
            wr = risky(row)
            mu = mu_path.iloc[h].values
            expected_ret = float(mu @ wr)
            risk = float(wr @ cov_step.values @ wr)
            delta = np.sqrt((row - prev_row) ** 2 + smooth_eps)
            turnover = float(delta.sum())
            tc = turnover * cost_bps / 10000.0
            cvar = empirical_cvar(returns_window[assets], wr, alpha=0.95) if cvar_lambda != 0 else 0.0
            utility = expected_ret - risk_aversion * risk - turnover_penalty * tc - cvar_lambda * cvar
            total_utility += (gamma ** h) * utility

            row_sum = float(row.sum())
            penalty += budget_penalty * (row_sum - 1.0) ** 2
            excess_turnover = max(0.0, turnover - turnover_budget)
            penalty += turnover_violation_penalty * excess_turnover ** 2
            annual_vol = math.sqrt(max(float(wr @ cov_step.values @ wr), 0.0)) * annual_factor
            excess_vol = max(0.0, annual_vol - target_vol)
            penalty += vol_violation_penalty * excess_vol ** 2
            prev_row = row
        return -float(total_utility) + float(penalty)

    res = minimize(
        objective,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": int(optimizer_maxiter), "ftol": 1e-9},
    )
    optimizer_iterations = int(getattr(res, "nit", 0) or 0)
    if res.success and np.all(np.isfinite(res.x)):
        arr = mat(res.x)
        success = True
        msg = str(res.message)
        obj = float(-res.fun)
        fallback_used = False
        fallback_reason = ""
    else:
        arr = mat(x0)
        success = False
        msg = str(res.message)
        obj = float(-objective(x0))
        fallback_used = True
        fallback_reason = f"optimizer_failure: {msg}"

    plan = pd.DataFrame(arr, index=[f"h{h+1}" for h in range(horizon)], columns=opt_assets)
    # Clean tiny weights and ensure budget after numerical noise.
    plan = plan.where(plan.abs() > 1e-10, 0.0)
    for idx in plan.index:
        if allow_cash:
            risky_row = plan.loc[idx, assets].clip(lower=0.0, upper=max_weight)
            if risky_row.sum() > 1.0:
                risky_row = risky_row / max(float(risky_row.sum()), EPS)
            plan.loc[idx, assets] = risky_row
            plan.loc[idx, CASH] = max(0.0, 1.0 - float(risky_row.sum()))
        else:
            row = plan.loc[idx].clip(lower=0.0, upper=max_weight)
            s = float(row.sum())
            if s > EPS:
                plan.loc[idx] = row / s
    first = plan.iloc[0].copy()
    expected_step_utility = obj / sum(gamma ** h for h in range(horizon))
    return MultiPeriodPlan(plan, first, obj, success, msg, expected_step_utility, fallback_used, fallback_reason, optimizer_iterations)


def get_prediction_row(predictions: Optional[pd.DataFrame], date: pd.Timestamp, assets: Sequence[str]) -> Optional[pd.Series]:
    if predictions is None or predictions.empty:
        return None
    eligible = predictions.loc[predictions.index <= date]
    if eligible.empty:
        return None
    return eligible.iloc[-1].reindex(assets).fillna(0.0)


def run_backtest(prices: pd.DataFrame, args: argparse.Namespace, predictions: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    returns = returns_from_prices(prices)
    assets = list(returns.columns)
    opt_assets = assets + ([] if args.no_cash else [CASH])
    current_w = pd.Series(0.0, index=opt_assets)
    if args.no_cash:
        current_w[assets] = 1.0 / len(assets)
    else:
        current_w[CASH] = 1.0

    weights_history = []
    plan_rows = []
    order_rows = []
    net_returns = []
    gross_returns = []
    costs = []
    turnovers = []
    diagnostics = []

    start_i = max(args.lookback, 80)
    next_rebalance_i = start_i
    for i in range(start_i, len(returns)):
        date = returns.index[i]
        cost_today = 0.0
        turnover_today = 0.0
        if i == next_rebalance_i:
            window = returns.iloc[i - args.lookback : i]
            cov_step = shrink_cov(window.cov() * args.rebalance_days, args.shrinkage)
            pred_row = get_prediction_row(predictions, date, assets)
            mu_path = estimate_forecast_path(
                window,
                horizon=args.horizon,
                rebalance_days=args.rebalance_days,
                forecast_decay=args.forecast_decay,
                shrink_mu=args.shrink_mu,
                prediction_row=pred_row,
            )
            prev_w = current_w.copy()
            plan = solve_multi_period_plan(
                mu_path=mu_path,
                cov_step=cov_step,
                returns_window=window,
                prev_weights=current_w,
                horizon=args.horizon,
                gamma=args.gamma,
                risk_aversion=args.risk_aversion,
                turnover_penalty=args.turnover_penalty,
                cvar_lambda=args.cvar_lambda,
                cost_bps=args.cost_bps,
                max_weight=args.max_weight,
                turnover_budget=args.turnover_budget,
                target_vol=args.target_vol,
                rebalance_days=args.rebalance_days,
                allow_cash=not args.no_cash,
                optimizer_maxiter=getattr(args, "optimizer_maxiter", 1000),
            )
            target = plan.first_step.reindex(opt_assets).fillna(0.0)
            target = apply_turnover_cap(target, current_w, args.turnover_budget)
            current_w = target
            cost_today = transaction_cost(prev_w, current_w, args.cost_bps)
            turnover_today = float((current_w.reindex(opt_assets).fillna(0.0) - prev_w.reindex(opt_assets).fillna(0.0)).abs().sum())
            weights_history.append(current_w.rename(date))
            pr = plan.plan.copy()
            pr.insert(0, "Horizon", pr.index)
            pr.insert(0, "Date", date)
            plan_rows.append(pr.reset_index(drop=True))
            for asset, d in (current_w.reindex(opt_assets).fillna(0.0) - prev_w.reindex(opt_assets).fillna(0.0)).items():
                if abs(d) > 1e-8:
                    order_rows.append({
                        "Date": date,
                        "Asset": asset,
                        "prev_weight": float(prev_w.reindex(opt_assets).fillna(0.0).loc[asset]),
                        "target_weight": float(current_w.loc[asset]),
                        "delta_weight": float(d),
                        "estimated_cost": float(abs(d) * args.cost_bps / 10000.0),
                    })
            diagnostics.append({
                "Date": date,
                "objective_value": plan.objective_value,
                "expected_step_utility": plan.expected_step_utility,
                "optimizer_success": float(plan.success),
                "fallback_used": float(plan.fallback_used),
                "fallback_reason": plan.fallback_reason,
                "optimizer_iterations": int(plan.optimizer_iterations),
                "turnover": turnover_today,
                "cost": cost_today,
                "message": plan.message,
            })
            next_rebalance_i += args.rebalance_days

        gross = realized_portfolio_return(current_w.drop(labels=[CASH], errors="ignore"), returns.iloc[i])
        net = gross - cost_today
        gross_returns.append((date, gross))
        net_returns.append((date, net))
        costs.append((date, cost_today))
        turnovers.append((date, turnover_today))

    net = pd.Series(dict(net_returns), name="net_return").sort_index()
    gross = pd.Series(dict(gross_returns), name="gross_return").sort_index()
    cost = pd.Series(dict(costs), name="transaction_cost").sort_index()
    turnover = pd.Series(dict(turnovers), name="turnover").sort_index()
    weights = pd.DataFrame(weights_history).sort_index() if weights_history else pd.DataFrame()
    plans = pd.concat(plan_rows, ignore_index=True) if plan_rows else pd.DataFrame()
    orders = pd.DataFrame(order_rows)
    diag = pd.DataFrame(diagnostics).sort_values("Date") if diagnostics else pd.DataFrame()
    metrics = annualized_metrics(net, turnover=turnover, cost=cost)
    metrics.update({
        "gross_ann_return": annualized_metrics(gross)["ann_return"],
        "horizon": int(args.horizon),
        "rebalance_days": int(args.rebalance_days),
        "risk_aversion": float(args.risk_aversion),
        "turnover_penalty": float(args.turnover_penalty),
        "optimizer_success_rate": float(diag["optimizer_success"].mean()) if not diag.empty else 0.0,
        "fallback_rate": float(diag["fallback_used"].mean()) if not diag.empty else 0.0,
        "avg_expected_step_utility": float(diag["expected_step_utility"].mean()) if not diag.empty else 0.0,
    })
    return {
        "net_returns": net,
        "gross_returns": gross,
        "costs": cost,
        "turnover": turnover,
        "weights": weights,
        "plans": plans,
        "orders": orders,
        "diagnostics": diag,
        "metrics": metrics,
    }


def tune_by_portfolio_utility(prices: pd.DataFrame, args: argparse.Namespace, predictions: Optional[pd.DataFrame]) -> Tuple[float, float, pd.DataFrame]:
    """Small grid search that selects parameters by realized portfolio utility.

    This is a practical decision-focused selection layer: it does not optimize
    forecast MSE; it scores net return, volatility, drawdown, and turnover cost.
    """
    risk_grid = [float(x) for x in args.tune_risk_grid.split(",")]
    turnover_grid = [float(x) for x in args.tune_turnover_grid.split(",")]
    rows = []
    best_score = -np.inf
    best = (args.risk_aversion, args.turnover_penalty)
    for risk_aversion, turnover_penalty in itertools.product(risk_grid, turnover_grid):
        local_args = argparse.Namespace(**vars(args))
        local_args.risk_aversion = risk_aversion
        local_args.turnover_penalty = turnover_penalty
        bt = run_backtest(prices, local_args, predictions=predictions)
        m = bt["metrics"]
        score = float(m["ann_return"] - 0.50 * abs(m["max_drawdown"]) - 0.10 * m["avg_turnover"] - m["ann_cost_drag"])
        rows.append({
            "risk_aversion": risk_aversion,
            "turnover_penalty": turnover_penalty,
            "decision_score": score,
            **m,
        })
        if score > best_score:
            best_score = score
            best = (risk_aversion, turnover_penalty)
    return best[0], best[1], pd.DataFrame(rows).sort_values("decision_score", ascending=False)


def latest_plan(prices: pd.DataFrame, args: argparse.Namespace, predictions: Optional[pd.DataFrame]) -> MultiPeriodPlan:
    returns = returns_from_prices(prices)
    assets = list(returns.columns)
    window = returns.iloc[-args.lookback :]
    cov_step = shrink_cov(window.cov() * args.rebalance_days, args.shrinkage)
    pred_row = get_prediction_row(predictions, returns.index[-1], assets)
    mu_path = estimate_forecast_path(
        window,
        horizon=args.horizon,
        rebalance_days=args.rebalance_days,
        forecast_decay=args.forecast_decay,
        shrink_mu=args.shrink_mu,
        prediction_row=pred_row,
    )
    opt_assets = assets + ([] if args.no_cash else [CASH])
    prev = pd.Series(0.0, index=opt_assets)
    if args.prev_weights:
        df = pd.read_csv(args.prev_weights)
        if {"Asset", "Weight"}.issubset(df.columns):
            prev = pd.Series(df["Weight"].values, index=df["Asset"].astype(str)).reindex(opt_assets).fillna(0.0)
    elif args.no_cash:
        prev[assets] = 1.0 / len(assets)
    else:
        prev[CASH] = 1.0
    return solve_multi_period_plan(
        mu_path=mu_path,
        cov_step=cov_step,
        returns_window=window,
        prev_weights=prev,
        horizon=args.horizon,
        gamma=args.gamma,
        risk_aversion=args.risk_aversion,
        turnover_penalty=args.turnover_penalty,
        cvar_lambda=args.cvar_lambda,
        cost_bps=args.cost_bps,
        max_weight=args.max_weight,
        turnover_budget=args.turnover_budget,
        target_vol=args.target_vol,
        rebalance_days=args.rebalance_days,
        allow_cash=not args.no_cash,
        optimizer_maxiter=getattr(args, "optimizer_maxiter", 1000),
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="C Decision-focused Multi-period Optimizer")
    p.add_argument("--prices", required=True, help="Wide price CSV. Columns: Date + assets")
    p.add_argument("--predictions", default=None, help="Optional wide one-step expected return forecast CSV. Date + assets")
    p.add_argument("--prev-weights", default=None, help="Optional CSV with Asset,Weight for latest plan")
    p.add_argument("--outdir", default="output/c_decision_focused_mpo")
    p.add_argument("--lookback", type=int, default=252)
    p.add_argument("--rebalance-days", type=int, default=5)
    p.add_argument("--horizon", type=int, default=4)
    p.add_argument("--gamma", type=float, default=0.97)
    p.add_argument("--forecast-decay", type=float, default=0.90)
    p.add_argument("--shrink-mu", type=float, default=0.50)
    p.add_argument("--shrinkage", type=float, default=0.35)
    p.add_argument("--risk-aversion", type=float, default=5.0)
    p.add_argument("--turnover-penalty", type=float, default=25.0)
    p.add_argument("--cvar-lambda", type=float, default=0.50)
    p.add_argument("--cost-bps", type=float, default=5.0)
    p.add_argument("--turnover-budget", type=float, default=0.20)
    p.add_argument("--max-weight", type=float, default=0.25)
    p.add_argument("--target-vol", type=float, default=0.10)
    p.add_argument("--optimizer-maxiter", type=int, default=1000, help="Maximum L-BFGS-B iterations for each rebalance solve")
    p.add_argument("--no-cash", action="store_true")
    p.add_argument("--tune", action="store_true", help="Select risk/turnover penalties by realized portfolio utility")
    p.add_argument("--tune-risk-grid", default="3,5,8")
    p.add_argument("--tune-turnover-grid", default="10,25,50")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    outdir = ensure_outdir(args.outdir)
    prices = load_price_csv(args.prices)
    predictions = load_wide_csv(args.predictions) if args.predictions else None

    tuning_table = None
    if args.tune:
        best_risk, best_turnover, tuning_table = tune_by_portfolio_utility(prices, args, predictions)
        args.risk_aversion = best_risk
        args.turnover_penalty = best_turnover
        tuning_table.to_csv(outdir / "decision_focused_tuning.csv", index=False)

    bt = run_backtest(prices, args, predictions=predictions)
    latest = latest_plan(prices, args, predictions=predictions)

    bt["net_returns"].to_csv(outdir / "backtest_net_returns.csv", index_label="Date")
    bt["gross_returns"].to_csv(outdir / "backtest_gross_returns.csv", index_label="Date")
    bt["costs"].to_csv(outdir / "transaction_costs.csv", index_label="Date")
    bt["turnover"].to_csv(outdir / "turnover.csv", index_label="Date")
    bt["weights"].to_csv(outdir / "weights_history.csv", index_label="Date")
    bt["plans"].to_csv(outdir / "plans_history.csv", index=False)
    bt["orders"].to_csv(outdir / "orders.csv", index=False)
    bt["diagnostics"].to_csv(outdir / "optimizer_diagnostics.csv", index=False)
    latest.plan.to_csv(outdir / "latest_multi_period_plan.csv", index_label="Horizon")
    latest.first_step.rename("Weight").reset_index().rename(columns={"index": "Asset"}).to_csv(outdir / "latest_weights.csv", index=False)
    write_json(bt["metrics"], outdir / "metrics.json")

    summary = {
        "algorithm": "C Decision-focused Multi-period Optimizer",
        "latest_date": str(prices.index[-1].date()),
        "latest_optimizer_success": latest.success,
        "latest_optimizer_message": latest.message,
        "latest_fallback_used": latest.fallback_used,
        "latest_fallback_reason": latest.fallback_reason,
        "latest_optimizer_iterations": latest.optimizer_iterations,
        "latest_objective_value": latest.objective_value,
        "selected_risk_aversion": args.risk_aversion,
        "selected_turnover_penalty": args.turnover_penalty,
        "metrics": bt["metrics"],
    }
    write_json(summary, outdir / "summary.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
