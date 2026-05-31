#!/usr/bin/env python3
"""Run C fast validation and dry-run reports.

This runner only creates research / paper-trading validation artifacts. It does
not connect to brokers, place orders, or enable live trading.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algos import c_decision_focused_multi_period_optimizer as cfast  # noqa: E402
from algos.common import ensure_outdir, load_price_csv, write_json  # noqa: E402

# ---------------------------------------------------------------------------
# Candidate profiles — single source of truth shared with run_cfast_upgrade_benchmark
# ---------------------------------------------------------------------------

CANDIDATE_PROFILES: Dict[str, Dict[str, object]] = {
    "baseline_default": dict(
        lookback=252, rebalance_days=20, horizon=2, target_vol=0.10,
        max_weight=0.25, turnover_budget=0.20, cvar_lambda=0.0,
        optimizer_maxiter=1000, gamma=0.97, forecast_decay=0.90,
        shrink_mu=0.50, shrinkage=0.35, risk_aversion=5.0,
        turnover_penalty=25.0,
    ),
    "vol_cap_relaxed": dict(
        lookback=252, rebalance_days=20, horizon=2, target_vol=0.15,
        max_weight=0.30, turnover_budget=0.25, cvar_lambda=0.0,
        optimizer_maxiter=1000, gamma=0.97, forecast_decay=0.90,
        shrink_mu=0.50, shrinkage=0.35, risk_aversion=4.0,
        turnover_penalty=20.0,
    ),
    "accepted_v2_target10_paper": dict(
        lookback=252, rebalance_days=20, horizon=2, target_vol=0.14,
        max_weight=0.45, turnover_budget=0.25, cvar_lambda=0.0,
        optimizer_maxiter=1000, gamma=0.97, forecast_decay=0.85,
        shrink_mu=0.50, shrinkage=0.35, risk_aversion=5.5,
        turnover_penalty=25.0,
    ),
    "defensive_v2": dict(
        lookback=252, rebalance_days=20, horizon=2, target_vol=0.08,
        max_weight=0.20, turnover_budget=0.15, cvar_lambda=0.0,
        optimizer_maxiter=1000, gamma=0.97, forecast_decay=0.80,
        shrink_mu=0.60, shrinkage=0.40, risk_aversion=8.0,
        turnover_penalty=30.0,
    ),
    "cost_conservative": dict(
        lookback=252, rebalance_days=20, horizon=2, target_vol=0.10,
        max_weight=0.25, turnover_budget=0.15, cvar_lambda=0.0,
        optimizer_maxiter=1000, gamma=0.97, forecast_decay=0.90,
        shrink_mu=0.50, shrinkage=0.35, risk_aversion=6.0,
        turnover_penalty=35.0,
    ),
}

CANDIDATE_IDS: List[str] = list(CANDIDATE_PROFILES.keys())


def apply_candidate_profile(args: argparse.Namespace, candidate: str) -> argparse.Namespace:
    """Override args with all params from a named candidate profile.

    This is the canonical way to reproduce benchmark results from the CLI:
    every key in CANDIDATE_PROFILES maps 1-to-1 to an attribute on args,
    ensuring identical optimizer config between benchmark and validation runs.
    """
    if candidate not in CANDIDATE_PROFILES:
        raise ValueError(
            f"Unknown candidate '{candidate}'. "
            f"Valid choices: {', '.join(CANDIDATE_IDS)}"
        )
    profile = CANDIDATE_PROFILES[candidate]
    # Use vars() copy so we don't mutate the original Namespace in-place
    merged = vars(args).copy()
    merged.update(profile)
    return argparse.Namespace(**merged)


A_VERDICT = "HOLD_DIAGNOSTIC_ONLY"
B_VERDICT = "REJECT_RETRAIN"
C_PASS = "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE"
C_FAIL = "VALIDATION_FAILED_REVIEW_REQUIRED"
CASH = "__CASH__"
PAPER_TRADING_ONLY = "PAPER_TRADING_DRY_RUN_ONLY"
PROMOTION_BLOCKED_VALIDATION = "BLOCKED_BY_VALIDATION_FAILED"
PROMOTION_BLOCKED_COST = "BLOCKED_BY_X5_COST_FRAGILITY"
PROMOTION_BLOCKED_TARGET_RETURN = "BLOCKED_BY_TARGET_RETURN_SHORTFALL"
PROMOTION_REVIEW_READY = "READY_FOR_PAPER_TRADING_REVIEW"
PROMOTION_NOT_APPLICABLE = "NOT_APPLICABLE_VALIDATION_FAILED"

DEFAULT_TARGET_RETURN_MIN = 0.10
DEFAULT_THRESHOLDS = {
    "base_min_ann_return": DEFAULT_TARGET_RETURN_MIN,
    "x2_min_ann_return": DEFAULT_TARGET_RETURN_MIN,
    "base_min_sharpe": 1.0,
    "x2_min_sharpe": 1.0,
    "base_min_max_drawdown": -0.10,
    "x2_min_max_drawdown": -0.10,
    "base_min_optimizer_success_rate": 0.90,
    "x2_min_optimizer_success_rate": 0.90,
    "x5_min_sharpe_warning": 1.0,
}


def build_thresholds(target_return_min: float) -> Dict[str, float]:
    """Build validation thresholds for annualized net-return target gating."""
    if target_return_min < 0:
        raise ValueError("--target-return-min must be non-negative")
    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds["base_min_ann_return"] = float(target_return_min)
    thresholds["x2_min_ann_return"] = float(target_return_min)
    return thresholds


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    if p.exists():
        return p
    return ROOT / p


def parse_cost_bps_list(text: str) -> List[float]:
    values = [float(x.strip()) for x in text.split(",") if x.strip()]
    if len(values) < 2:
        raise ValueError("--cost-bps-list must include at least base and x2 costs")
    if any(v < 0 for v in values):
        raise ValueError("--cost-bps-list values must be non-negative")
    return values


def validate_price_frame(raw: pd.DataFrame, min_rows: int) -> None:
    if "Date" not in raw.columns:
        raise ValueError("price CSV must include a Date column")
    dates = pd.to_datetime(raw["Date"], errors="raise")
    if dates.duplicated().any():
        raise ValueError("price CSV Date column must not contain duplicates")
    if not dates.is_monotonic_increasing:
        raise ValueError("price CSV Date column must be strictly increasing")
    asset_cols = [c for c in raw.columns if c != "Date"]
    if not asset_cols:
        raise ValueError("price CSV must include at least one asset column")
    if len(raw) < min_rows:
        raise ValueError(f"price CSV has {len(raw)} rows; at least {min_rows} rows are required")
    numeric = raw[asset_cols].apply(pd.to_numeric, errors="coerce")
    if numeric.dropna(axis=1, how="all").empty:
        raise ValueError("price CSV must include numeric asset prices")


def load_validated_prices(path: str | Path, min_rows: int) -> pd.DataFrame:
    resolved = resolve_path(path)
    raw = pd.read_csv(resolved)
    validate_price_frame(raw, min_rows=min_rows)
    return load_price_csv(resolved)


def validate_latest_weights_schema(weights: pd.DataFrame, tolerance: float = 1e-6) -> None:
    required = {"Asset", "Weight"}
    missing = required - set(weights.columns)
    if missing:
        raise ValueError(f"latest_weights missing columns: {sorted(missing)}")
    if CASH not in set(weights["Asset"].astype(str)):
        raise ValueError("latest_weights must include __CASH__")
    total = float(pd.to_numeric(weights["Weight"], errors="raise").sum())
    if not math.isclose(total, 1.0, rel_tol=tolerance, abs_tol=tolerance):
        raise ValueError(f"latest_weights must sum to 1.0, got {total}")


def make_c_args(args: argparse.Namespace, outdir: Path, cost_bps: float) -> argparse.Namespace:
    return argparse.Namespace(
        prices=str(args.prices),
        predictions=None,
        prev_weights=None,
        outdir=str(outdir),
        lookback=args.lookback,
        rebalance_days=args.rebalance_days,
        horizon=args.horizon,
        gamma=args.gamma,
        forecast_decay=args.forecast_decay,
        shrink_mu=args.shrink_mu,
        shrinkage=args.shrinkage,
        risk_aversion=args.risk_aversion,
        turnover_penalty=args.turnover_penalty,
        cvar_lambda=args.cvar_lambda,
        cost_bps=cost_bps,
        turnover_budget=args.turnover_budget,
        max_weight=args.max_weight,
        target_vol=args.target_vol,
        optimizer_maxiter=args.optimizer_maxiter,
        no_cash=False,
        tune=False,
        tune_risk_grid="3,5,8",
        tune_turnover_grid="10,25,50",
    )


def latest_weights_frame(weights: pd.Series) -> pd.DataFrame:
    frame = weights.rename("Weight").reset_index().rename(columns={"index": "Asset"})
    validate_latest_weights_schema(frame)
    return frame


def run_cfast_once(prices: pd.DataFrame, args: argparse.Namespace, label: str, cost_bps: float, run_dir: Path) -> Dict[str, object]:
    ensure_outdir(run_dir)
    c_args = make_c_args(args, outdir=run_dir, cost_bps=cost_bps)
    bt = cfast.run_backtest(prices, c_args, predictions=None)
    latest = cfast.latest_plan(prices, c_args, predictions=None)

    bt["net_returns"].to_csv(run_dir / "backtest_net_returns.csv", index_label="Date")
    bt["gross_returns"].to_csv(run_dir / "backtest_gross_returns.csv", index_label="Date")
    bt["costs"].to_csv(run_dir / "transaction_costs.csv", index_label="Date")
    bt["turnover"].to_csv(run_dir / "turnover.csv", index_label="Date")
    bt["weights"].to_csv(run_dir / "weights_history.csv", index_label="Date")
    bt["plans"].to_csv(run_dir / "plans_history.csv", index=False)
    bt["orders"].to_csv(run_dir / "orders.csv", index=False)
    bt["diagnostics"].to_csv(run_dir / "optimizer_diagnostics.csv", index=False)
    latest.plan.to_csv(run_dir / "latest_multi_period_plan.csv", index_label="Horizon")
    weights = latest_weights_frame(latest.first_step)
    weights.to_csv(run_dir / "latest_weights.csv", index=False)
    write_json(bt["metrics"], run_dir / "metrics.json")

    summary = {
        "label": label,
        "algorithm": "C Decision-focused Multi-period Optimizer",
        "latest_date": str(prices.index[-1].date()),
        "latest_optimizer_success": latest.success,
        "latest_optimizer_message": latest.message,
        "latest_objective_value": latest.objective_value,
        "cost_bps": cost_bps,
        "settings": {
            "lookback": args.lookback,
            "rebalance_days": args.rebalance_days,
            "horizon": args.horizon,
            "target_vol": args.target_vol,
            "max_weight": args.max_weight,
            "turnover_budget": args.turnover_budget,
            "cvar_lambda": args.cvar_lambda,
            "optimizer_maxiter": args.optimizer_maxiter,
        },
        "metrics": bt["metrics"],
        "output_dir": str(run_dir),
    }
    write_json(summary, run_dir / "summary.json")
    return summary


def run_walk_forward(prices: pd.DataFrame, args: argparse.Namespace, cost_bps: float) -> List[Dict[str, object]]:
    splitter = TimeSeriesSplit(n_splits=args.splits, gap=args.gap, test_size=args.test_size)
    rows: List[Dict[str, object]] = []
    for fold, (train_idx, test_idx) in enumerate(splitter.split(prices), start=1):
        start = max(0, int(test_idx[0]) - args.lookback)
        fold_prices = prices.iloc[start : int(test_idx[-1]) + 1]
        if len(fold_prices) <= max(args.lookback, 80):
            continue
        c_args = make_c_args(args, outdir=Path("_unused"), cost_bps=cost_bps)
        bt = cfast.run_backtest(fold_prices, c_args, predictions=None)
        metrics = bt["metrics"]
        rows.append({
            "fold": fold,
            "train_end": str(prices.index[int(train_idx[-1])].date()),
            "test_start": str(prices.index[int(test_idx[0])].date()),
            "test_end": str(prices.index[int(test_idx[-1])].date()),
            "ann_return": metrics["ann_return"],
            "ann_vol": metrics["ann_vol"],
            "sharpe": metrics["sharpe"],
            "max_drawdown": metrics["max_drawdown"],
            "optimizer_success_rate": metrics["optimizer_success_rate"],
            "fallback_rate": metrics.get("fallback_rate", 0.0),
        })
    return rows


def cost_label(position: int, cost_bps: float) -> str:
    if position == 0:
        return "base"
    if position == 1:
        return "x2"
    if position == 2:
        return "x5"
    return f"cost_{cost_bps:g}bps"


def _append_target_return_warnings(
    metrics: Dict[str, float],
    label: str,
    thresholds: Dict[str, float],
    warnings: List[str],
) -> None:
    key = f"{label}_min_ann_return"
    if key in thresholds and metrics["ann_return"] < thresholds[key]:
        warnings.append(f"target_return_shortfall_{label}")


def evaluate_policy(
    stress: Dict[str, Dict[str, object]],
    thresholds: Optional[Dict[str, float]] = None,
) -> tuple[str, List[str]]:
    thresholds = thresholds or build_thresholds(DEFAULT_TARGET_RETURN_MIN)
    warnings: List[str] = []
    base = stress["base"]["metrics"]
    x2 = stress["x2"]["metrics"]
    x5 = stress.get("x5", {}).get("metrics")

    _append_target_return_warnings(base, "base", thresholds, warnings)
    _append_target_return_warnings(x2, "x2", thresholds, warnings)

    passes = (
        base["ann_return"] >= thresholds["base_min_ann_return"]
        and x2["ann_return"] >= thresholds["x2_min_ann_return"]
        and base["sharpe"] >= thresholds["base_min_sharpe"]
        and x2["sharpe"] >= thresholds["x2_min_sharpe"]
        and base["max_drawdown"] >= thresholds["base_min_max_drawdown"]
        and x2["max_drawdown"] >= thresholds["x2_min_max_drawdown"]
        and base["optimizer_success_rate"] >= thresholds["base_min_optimizer_success_rate"]
        and x2["optimizer_success_rate"] >= thresholds["x2_min_optimizer_success_rate"]
    )
    if x5 and x5["sharpe"] < thresholds["x5_min_sharpe_warning"]:
        warnings.append("cost_fragile")
    return (C_PASS if passes else C_FAIL), warnings


def build_execution_controls(c_verdict: str, warnings: List[str]) -> Dict[str, object]:
    """Separate paper-trading permission from live/promotion eligibility."""
    blockers: List[str] = []
    if any(w.startswith("target_return_shortfall") for w in warnings):
        blockers.append(PROMOTION_BLOCKED_TARGET_RETURN)
    if "cost_fragile" in warnings:
        blockers.append(PROMOTION_BLOCKED_COST)

    if c_verdict != C_PASS:
        return {
            "execution_mode": "VALIDATION_FAILED_NO_TRADING",
            "promotion_status": (
                PROMOTION_BLOCKED_TARGET_RETURN
                if PROMOTION_BLOCKED_TARGET_RETURN in blockers
                else PROMOTION_NOT_APPLICABLE
            ),
            "promotion_blockers": [PROMOTION_BLOCKED_VALIDATION, *blockers],
            "live_trading_allowed": False,
            "broker_execution_allowed": False,
        }
    return {
        "execution_mode": PAPER_TRADING_ONLY,
        "promotion_status": (
            PROMOTION_BLOCKED_TARGET_RETURN
            if PROMOTION_BLOCKED_TARGET_RETURN in blockers
            else (PROMOTION_BLOCKED_COST if blockers else PROMOTION_REVIEW_READY)
        ),
        "promotion_blockers": blockers,
        "live_trading_allowed": False,
        "broker_execution_allowed": False,
    }


def build_cost_stress_frame(stress: Dict[str, Dict[str, object]], thresholds: Dict[str, float]) -> pd.DataFrame:
    rows = []
    for label, summary in stress.items():
        metrics = summary["metrics"]
        target_key = f"{label}_min_ann_return"
        target_min = thresholds.get(target_key)
        target_pass = None if target_min is None else metrics["ann_return"] >= target_min
        rows.append({
            "label": label,
            "cost_bps": summary["cost_bps"],
            "ann_return": metrics["ann_return"],
            "target_return_min": target_min,
            "target_return_pass": target_pass,
            "ann_vol": metrics["ann_vol"],
            "sharpe": metrics["sharpe"],
            "max_drawdown": metrics["max_drawdown"],
            "calmar": metrics["calmar"],
            "hit_rate": metrics["hit_rate"],
            "avg_turnover": metrics["avg_turnover"],
            "ann_cost_drag": metrics["ann_cost_drag"],
            "optimizer_success_rate": metrics["optimizer_success_rate"],
            "fallback_rate": metrics.get("fallback_rate", 0.0),
        })
    return pd.DataFrame(rows)


def frame_records(frame: pd.DataFrame) -> List[Dict[str, object]]:
    """Convert pandas records without leaking NaN into JSON outputs."""
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def build_report(summary: Dict[str, object]) -> str:
    rows = []
    for item in summary["c_fast_cost_stress"]:
        target_min = item.get("target_return_min")
        target_pass = item.get("target_return_pass")
        target_min_text = "info" if target_min is None else f"{target_min:.2%}"
        target_pass_text = "info" if target_pass is None else str(bool(target_pass))
        rows.append(
            f"| {item['label']} | {item['cost_bps']:.2f} | {item['sharpe']:.2f} | "
            f"{item['ann_return']:.2%} | {target_min_text} | {target_pass_text} | "
            f"{item['max_drawdown']:.2%} | "
            f"{item['optimizer_success_rate']:.2%} | {item.get('fallback_rate', 0.0):.2%} |"
        )
    warnings = ", ".join(summary["warnings"]) if summary["warnings"] else "none"
    controls = summary["execution_controls"]
    blockers = ", ".join(controls["promotion_blockers"]) if controls["promotion_blockers"] else "none"
    fwd = summary.get("forward_month_gate", {})
    fwd_pass = fwd.get("forward_pass", "N/A")
    return "\n".join([
        "# C Fast Validation Report",
        "",
        "No broker execution. No live trading. Dry-run validation only.",
        "",
        "## Verdicts",
        "",
        f"- A: `{summary['policy_verdicts']['A']}`",
        f"- B: `{summary['policy_verdicts']['B']}`",
        f"- C fast: `{summary['policy_verdicts']['C_fast']}`",
        f"- target_return_metric: `{summary['return_policy']['target_return_metric']}`",
        f"- target_return_min: `{summary['return_policy']['target_return_min']:.2%}`",
        f"- warnings: `{warnings}`",
        f"- execution_mode: `{controls['execution_mode']}`",
        f"- promotion_status: `{controls['promotion_status']}`",
        f"- promotion_blockers: `{blockers}`",
        "",
        "## Forward-Month Gate",
        "",
        f"- forward_pass: `{fwd_pass}`",
        f"- forward_return: `{fwd.get('forward_return', 'N/A'):.2%}`",
        f"- forward_mdd: `{fwd.get('forward_mdd', 'N/A'):.2%}`",
        "",
        "## Cost Stress",
        "",
        "| Label | Cost bps | Sharpe | Ann Return | Target Return Min | Target Return Pass | MDD | Optimizer Success | Fallback Rate |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|",
        *rows,
        "",
        "## Data",
        "",
        f"- rows: {summary['data_metadata']['rows']}",
        f"- first_date: {summary['data_metadata']['first_date']}",
        f"- last_date: {summary['data_metadata']['last_date']}",
        f"- columns: {', '.join(summary['data_metadata']['columns'])}",
        "",
    ])


# ---------------------------------------------------------------------------
# Forward-Month Gate
# ---------------------------------------------------------------------------

FORWARD_RETURN_THRESHOLD = -0.02
FORWARD_MDD_THRESHOLD = -0.05


def evaluate_forward_month(
    base_metrics: Dict[str, float],
    forward_metrics: Dict[str, float],
    cost_label: str,
) -> Dict[str, object]:
    """Evaluate forward-month gate before promotion decision.

    Thresholds (plan.md):
      base latest_month_return >= -2.00%
      x2  latest_month_return >= -2.00%
      base latest_month_mdd    >= -5.00%
      x2  latest_month_mdd      >= -5.00%
    """
    warnings: List[str] = []
    fwd_ret = forward_metrics.get("forward_return", 0.0)
    fwd_mdd = forward_metrics.get("forward_mdd", 0.0)

    if fwd_ret < FORWARD_RETURN_THRESHOLD:
        warnings.append(f"forward_month_return_below_threshold_{cost_label}")
    if fwd_mdd < FORWARD_MDD_THRESHOLD:
        warnings.append(f"forward_month_mdd_below_threshold_{cost_label}")

    forward_pass = (
        fwd_ret >= FORWARD_RETURN_THRESHOLD and fwd_mdd >= FORWARD_MDD_THRESHOLD
    )
    return {
        "forward_pass": forward_pass,
        "warnings": warnings,
        "forward_return": fwd_ret,
        "forward_mdd": fwd_mdd,
    }


# ---------------------------------------------------------------------------
# Regime Diagnostics
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_MONTH = 21


def _momentum(series: pd.Series, window: int) -> float:
    if len(series) < window:
        return 0.0
    return float((series.iloc[-1] / series.iloc[-window]) - 1.0)


def _drawdown_state(series: pd.Series) -> str:
    """Classify drawdown state as normal / mild / severe."""
    ret = series.pct_change(fill_method=None).fillna(0.0)
    nav = (1.0 + ret).cumprod()
    peak = nav.cummax()
    dd = nav / peak - 1.0
    mdd = float(dd.min())
    if mdd >= -0.05:
        return "normal"
    elif mdd >= -0.15:
        return "mild"
    else:
        return "severe"


def compute_regime_diagnostics(
    prices: pd.DataFrame, latest_weights: Optional[pd.DataFrame] = None
) -> Dict[str, object]:
    """Compute regime diagnostics: GLD/DBC momentum, relative strength, drawdown state.

    Output fields (plan.md):
      - GLD trailing momentum (1-month, 3-month)
      - DBC trailing momentum (1-month, 3-month)
      - GLD vs DBC relative strength ratio
      - Equity drawdown state (SPY, QQQ, IWM)
      - Bond drawdown state (TLT, IEF)
      - Latest risky exposure by sleeve (weights-based, plan.md Step 2 fix)
    """
    MOMENTUM_1M = TRADING_DAYS_PER_MONTH
    MOMENTUM_3M = 3 * TRADING_DAYS_PER_MONTH

    gld_1m = 0.0
    gld_3m = 0.0
    dbc_1m = 0.0
    dbc_3m = 0.0
    gld_dbc_rs = 1.0

    if "GLD" in prices.columns and len(prices) >= MOMENTUM_3M:
        gld_1m = _momentum(prices["GLD"], MOMENTUM_1M)
        gld_3m = _momentum(prices["GLD"], MOMENTUM_3M)
    if "DBC" in prices.columns and len(prices) >= MOMENTUM_3M:
        dbc_1m = _momentum(prices["DBC"], MOMENTUM_1M)
        dbc_3m = _momentum(prices["DBC"], MOMENTUM_3M)
    if "GLD" in prices.columns and "DBC" in prices.columns and len(prices) >= MOMENTUM_1M:
        gld_ret = _momentum(prices["GLD"], MOMENTUM_1M)
        dbc_ret = _momentum(prices["DBC"], MOMENTUM_1M)
        if abs(dbc_ret) > 1e-12:
            gld_dbc_rs = gld_ret / dbc_ret
        else:
            gld_dbc_rs = 1.0 if abs(gld_ret) <= 1e-12 else float("inf")

    equity_cols = [c for c in ["SPY", "QQQ", "IWM"] if c in prices.columns]
    bond_cols = [c for c in ["TLT", "IEF"] if c in prices.columns]

    equity_state = "normal"
    if equity_cols:
        combined = prices[equity_cols].mean(axis=1)
        equity_state = _drawdown_state(combined)

    bond_state = "normal"
    if bond_cols:
        combined = prices[bond_cols].mean(axis=1)
        bond_state = _drawdown_state(combined)

    # Fix: weights-based sleeve exposure (plan.md Step 2)
    if latest_weights is not None:
        wt_map = dict(zip(latest_weights["Asset"].astype(str), latest_weights["Weight"]))
        metal_exposure = float(wt_map.get("GLD", 0.0))
        commodity_exposure = float(wt_map.get("DBC", 0.0))
    else:
        metal_exposure = 0.0
        commodity_exposure = 0.0

    return {
        "gld_1m_momentum": gld_1m,
        "gld_3m_momentum": gld_3m,
        "dbc_1m_momentum": dbc_1m,
        "dbc_3m_momentum": dbc_3m,
        "gld_dbc_relative_strength": gld_dbc_rs,
        "equity_drawdown_state": equity_state,
        "bond_drawdown_state": bond_state,
        "latest_risky_exposure_by_sleeve": {
            "metal": metal_exposure,
            "commodity": commodity_exposure,
        },
    }


# ---------------------------------------------------------------------------
# Sleeve-Level Cap Warnings
# ---------------------------------------------------------------------------

SLEEVE_WEIGHT_THRESHOLD = 0.20
SLEEVE_RETURN_THRESHOLD = -0.05
GLD_HARD_WEIGHT_CAP = 0.15   # plan.md: GLD <= 15%
DBC_WEIGHT_FLOOR   = 0.05   # plan.md: DBC >= 5%


def check_sleeve_cap_warnings(
    latest_weights: pd.DataFrame,
    latest_asset_returns: pd.Series,
) -> List[str]:
    """Check sleeve-level cap warnings per plan.md rule:

    if GLD_average_weight > 0.20 and GLD_latest_month_return < -0.05:
        warnings.append("metal_sleeve_forward_loss")
    if DBC_average_weight > 0.20 and DBC_latest_month_return < -0.05:
        warnings.append("commodity_sleeve_forward_loss")
    plus GLD hard cap <= 15% and DBC floor >= 5% (plan.md Step 2).
    """
    warnings: List[str] = []
    wt_map = dict(zip(latest_weights["Asset"].astype(str), latest_weights["Weight"]))

    gld_weight = wt_map.get("GLD", 0.0)
    dbc_weight = wt_map.get("DBC", 0.0)

    gld_ret = float(latest_asset_returns.get("GLD", 0.0))
    dbc_ret = float(latest_asset_returns.get("DBC", 0.0))

    if gld_weight > SLEEVE_WEIGHT_THRESHOLD and gld_ret < SLEEVE_RETURN_THRESHOLD:
        warnings.append("metal_sleeve_forward_loss")
    if dbc_weight > SLEEVE_WEIGHT_THRESHOLD and dbc_ret < SLEEVE_RETURN_THRESHOLD:
        warnings.append("commodity_sleeve_forward_loss")
    if gld_weight > GLD_HARD_WEIGHT_CAP:          # Step 2: GLD weight hard cap
        warnings.append("gld_weight_cap_breach")
    if dbc_weight < DBC_WEIGHT_FLOOR:             # Step 2: DBC weight floor
        warnings.append("dbc_weight_floor_breach")

    return warnings


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="C fast validation runner")
    p.add_argument("--prices", default="examples/data/internet_latest_yahoo_prices.csv")
    p.add_argument("--outdir", default="demo_output/internet_latest_yahoo/cfast_validation")
    p.add_argument("--cost-bps-list", default="5,10,25")
    p.add_argument("--splits", type=int, default=4)
    p.add_argument("--gap", type=int, default=5)
    p.add_argument("--test-size", type=int, default=126)
    p.add_argument("--lookback", type=int, default=252)
    p.add_argument("--rebalance-days", type=int, default=20)
    p.add_argument("--horizon", type=int, default=2)
    p.add_argument("--target-vol", type=float, default=0.10)
    p.add_argument("--max-weight", type=float, default=0.25)
    p.add_argument("--turnover-budget", type=float, default=0.20)
    p.add_argument("--cvar-lambda", type=float, default=0.0)
    p.add_argument("--target-return-min", type=float, default=DEFAULT_TARGET_RETURN_MIN)
    p.add_argument("--optimizer-maxiter", type=int, default=1000)
    p.add_argument("--gamma", type=float, default=0.97)
    p.add_argument("--forecast-decay", type=float, default=0.90)
    p.add_argument("--shrink-mu", type=float, default=0.50)
    p.add_argument("--shrinkage", type=float, default=0.35)
    p.add_argument("--risk-aversion", type=float, default=5.0)
    p.add_argument("--turnover-penalty", type=float, default=25.0)
    p.add_argument(
        "--candidate",
        default=None,
        choices=CANDIDATE_IDS,
        help=(
            "Load a named candidate profile from CANDIDATE_PROFILES and override "
            "all optimizer params. Reproduces benchmark results exactly. "
            f"Choices: {', '.join(CANDIDATE_IDS)}"
        ),
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    # Apply candidate profile BEFORE resolving paths so all optimizer params
    # are set identically to the benchmark runner. This is the fix for the
    # CLI-vs-benchmark gap: profiles define all 14 optimizer keys atomically.
    if args.candidate is not None:
        args = apply_candidate_profile(args, args.candidate)
    args.prices = resolve_path(args.prices)
    outdir = ensure_outdir(resolve_path(args.outdir))
    cost_bps_values = parse_cost_bps_list(args.cost_bps_list)
    thresholds = build_thresholds(args.target_return_min)
    min_rows = max(args.lookback + args.test_size + args.gap + 2, args.splits * args.test_size + args.gap + 1)
    prices = load_validated_prices(args.prices, min_rows=min_rows)

    stress: Dict[str, Dict[str, object]] = {}
    for position, cost_bps in enumerate(cost_bps_values):
        label = cost_label(position, cost_bps)
        stress[label] = run_cfast_once(prices, args, label, cost_bps, outdir / "runs" / f"{label}_{cost_bps:g}bps")
    if "base" not in stress or "x2" not in stress:
        raise ValueError("cost stress must produce at least base and x2 runs")

    c_verdict, warnings = evaluate_policy(stress, thresholds)
    execution_controls = build_execution_controls(c_verdict, warnings)
    if "base" in stress:
        walk_forward = run_walk_forward(prices, args, cost_bps=float(stress["base"]["cost_bps"]))
    else:
        walk_forward = []

    cost_stress = build_cost_stress_frame(stress, thresholds)
    cost_stress.to_csv(outdir / "cost_stress_summary.csv", index=False)

    latest_weights = pd.read_csv(Path(stress["base"]["output_dir"]) / "latest_weights.csv")
    validate_latest_weights_schema(latest_weights)
    latest_weights.to_csv(outdir / "latest_weights.csv", index=False)

    # Phase 2 additions: regime diagnostics + sleeve cap warnings
    regime_diagnostics = compute_regime_diagnostics(prices, latest_weights=latest_weights)

    latest_asset_returns = prices.pct_change(
        periods=TRADING_DAYS_PER_MONTH, fill_method=None
    ).iloc[-1].fillna(0.0)
    sleeve_warnings = check_sleeve_cap_warnings(latest_weights, latest_asset_returns)
    warnings = warnings + sleeve_warnings

    # Forward-month gate (plan.md Step 1)
    _fwd_ret = float(
        (prices.iloc[-1] / prices.iloc[-1 - TRADING_DAYS_PER_MONTH] - 1.0).mean()
        if len(prices) > TRADING_DAYS_PER_MONTH else 0.0
    )
    _fwd_mdd = float(
        (prices.iloc[-TRADING_DAYS_PER_MONTH:].pct_change(fill_method=None)
         .fillna(0.0).cumsum().rolling(TRADING_DAYS_PER_MONTH)
         .apply(lambda x: x[-1] - x.max()).min().iloc[-1])
        if len(prices) > TRADING_DAYS_PER_MONTH else 0.0
    )
    forward_month_gate = evaluate_forward_month(
        base_metrics=stress["base"]["metrics"],
        forward_metrics={"forward_return": _fwd_ret, "forward_mdd": _fwd_mdd},
        cost_label="base",
    )

    summary = {
        "data_metadata": {
            "source_path": str(args.prices),
            "rows": int(len(prices)),
            "first_date": str(prices.index.min().date()),
            "last_date": str(prices.index.max().date()),
            "columns": list(prices.columns),
        },
        "policy_verdicts": {
            "A": A_VERDICT,
            "B": B_VERDICT,
            "C_fast": c_verdict,
        },
        "return_policy": {
            "target_return_metric": "annualized_net_return",
            "target_return_min": float(args.target_return_min),
            "note": "This is a validation gate, not an assured outcome claim.",
        },
        "execution_controls": execution_controls,
        "thresholds": thresholds,
        "c_fast_cost_stress": frame_records(cost_stress),
        "latest_weights": frame_records(latest_weights),
        "walk_forward": walk_forward,
        "warnings": warnings,
        "regime_diagnostics": regime_diagnostics,
        "forward_month_gate": forward_month_gate,
    }
    write_json(summary, outdir / "validation_summary.json")
    (outdir / "validation_report.md").write_text(build_report(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
