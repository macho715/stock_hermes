#!/usr/bin/env python3
"""C Fast Upgrade Benchmark Runner — Phase 1 of plan.md.

Runs all5 upgrade candidates through full-period validation and
March-forward revalidation, then emits a benchmark CSV + summary + report.

Safety: live_trading_allowed=false, broker_execution_allowed=false always.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from algos import c_decision_focused_multi_period_optimizer as cfast  # noqa: E402
from algos.common import ensure_outdir, load_price_csv, write_json  # noqa: E402
from examples.run_cfast_validation import (  # noqa: E402
    CANDIDATE_IDS,
    CANDIDATE_PROFILES,
    build_cost_stress_frame,
    build_execution_controls,
    build_thresholds,
    cost_label,
    evaluate_policy,
    latest_weights_frame,
    load_validated_prices,
    make_c_args,
    parse_cost_bps_list,
    resolve_path,
    run_cfast_once,
    run_walk_forward,
    validate_latest_weights_schema,
)

# CANDIDATE_PROFILES and CANDIDATE_IDS are now defined in run_cfast_validation.py
# (single source of truth). They are imported above.

# ---------------------------------------------------------------------------
# Forward-month isolation
# ---------------------------------------------------------------------------

TRADING_DAYS_PER_MONTH = 21


def isolate_latest_month(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split prices into base (all but last month) and forward (last month only).

    Returns (base_prices, forward_prices) where forward contains only the
    final `TRADING_DAYS_PER_MONTH` rows.
    """
    if len(prices) <= TRADING_DAYS_PER_MONTH + 60:
        # Not enough history — use the last 21 rows as forward
        forward = prices.iloc[-TRADING_DAYS_PER_MONTH:]
        base = prices.iloc[:]
    else:
        forward = prices.iloc[-TRADING_DAYS_PER_MONTH:]
        base = prices.iloc[:-TRADING_DAYS_PER_MONTH]
    return base, forward


def compute_forward_metrics(
    base_prices: pd.DataFrame,
    forward_prices: pd.DataFrame,
    args: argparse.Namespace,
    cost_bps: float,
) -> Dict[str, float]:
    """Run backtest on base, then evaluate forward month return/MDD.

    Returns dict with forward_return, forward_mdd, forward_pass.
    """
    out_dir = Path("_unused_forward")
    c_args = make_c_args(args, outdir=out_dir, cost_bps=cost_bps)

    # Full-period backtest on base to get weights at the split boundary
    bt = cfast.run_backtest(base_prices, c_args, predictions=None)
    if not bt["weights"].empty:
        last_weights = bt["weights"].iloc[-1]
    else:
        last_weights = None

    # Forward-period net returns using the last known weights
    fwd_ret = forward_prices.pct_change(fill_method=None).fillna(0.0)
    if last_weights is not None:
        # Align forward returns to the last weights
        aligned = fwd_ret.reindex(columns=last_weights.index, fill_value=0.0)
        portfolio_ret = (aligned * last_weights).sum(axis=1)
    else:
        portfolio_ret = fwd_ret.mean(axis=1)

    forward_return = float(portfolio_ret.sum())
    nav = (1.0 + portfolio_ret).cumprod()
    peak = nav.cummax()
    dd = nav / peak - 1.0
    forward_mdd = float(dd.min())

    return {
        "forward_return": forward_return,
        "forward_mdd": forward_mdd,
        "forward_pass": forward_return >= -0.02 and forward_mdd >= -0.05,
    }


# ---------------------------------------------------------------------------
# Per-candidate run
# ---------------------------------------------------------------------------

FORWARD_RETURN_THRESHOLD = -0.02
FORWARD_MDD_THRESHOLD = -0.05


def run_candidate(
    candidate: str,
    prices: pd.DataFrame,
    base_args: argparse.Namespace,
    outdir: Path,
    cost_bps_values: List[float],
) -> Dict:
    """Run one candidate through full-period + forward-month evaluation."""
    params = CANDIDATE_PROFILES[candidate]
    args = argparse.Namespace(
        prices=base_args.prices,
        lookback=params["lookback"],
        rebalance_days=params["rebalance_days"],
        horizon=params["horizon"],
        gamma=params["gamma"],
        forecast_decay=params["forecast_decay"],
        shrink_mu=params["shrink_mu"],
        shrinkage=params["shrinkage"],
        risk_aversion=params["risk_aversion"],
        turnover_penalty=params["turnover_penalty"],
        cvar_lambda=params["cvar_lambda"],
        turnover_budget=params["turnover_budget"],
        max_weight=params["max_weight"],
        target_vol=params["target_vol"],
        optimizer_maxiter=params["optimizer_maxiter"],
    )

    stress: Dict[str, Dict] = {}
    for position, cost_bps in enumerate(cost_bps_values):
        label = cost_label(position, cost_bps)
        stress[label] = run_cfast_once(
            prices, args, label, cost_bps,
            outdir / "runs" / f"{candidate}_{label}_{cost_bps:g}bps",
        )

    thresholds = build_thresholds(base_args.target_return_min)
    verdict, warnings = evaluate_policy(stress, thresholds)

    # Forward-month evaluation
    base_prices, forward_prices = isolate_latest_month(prices)
    forward_base = compute_forward_metrics(
        base_prices, forward_prices, args,
        cost_bps=float(cost_bps_values[0]),
    )
    forward_x2 = compute_forward_metrics(
        base_prices, forward_prices, args,
        cost_bps=float(cost_bps_values[1]),
    )

    return {
        "candidate": candidate,
        "verdict": verdict,
        "warnings": warnings,
        "stress": stress,
        "thresholds": thresholds,
        "forward_base": forward_base,
        "forward_x2": forward_x2,
    }


# ---------------------------------------------------------------------------
# Benchmark frame builders
# ---------------------------------------------------------------------------

def build_benchmark_row(result: Dict, cost_bps_values: List[float]) -> Dict:
    """Flatten one candidate result into a benchmark CSV row."""
    stress = result["stress"]
    base_metrics = stress["base"]["metrics"]
    x2_metrics = stress["x2"]["metrics"]
    thresholds = result["thresholds"]

    base_pass = (
        base_metrics["ann_return"] >= thresholds["base_min_ann_return"]
        and base_metrics["sharpe"] >= thresholds["base_min_sharpe"]
        and base_metrics["max_drawdown"] >= thresholds["base_min_max_drawdown"]
        and base_metrics["optimizer_success_rate"] >= thresholds["base_min_optimizer_success_rate"]
    )
    x2_pass = (
        x2_metrics["ann_return"] >= thresholds["x2_min_ann_return"]
        and x2_metrics["sharpe"] >= thresholds["x2_min_sharpe"]
        and x2_metrics["max_drawdown"] >= thresholds["x2_min_max_drawdown"]
        and x2_metrics["optimizer_success_rate"] >= thresholds["x2_min_optimizer_success_rate"]
    )

    return {
        "candidate": result["candidate"],
        "base_cost_bps": cost_bps_values[0],
        "x2_cost_bps": cost_bps_values[1],
        "base_ann_return": base_metrics["ann_return"],
        "base_sharpe": base_metrics["sharpe"],
        "base_max_drawdown": base_metrics["max_drawdown"],
        "base_optimizer_success_rate": base_metrics["optimizer_success_rate"],
        "x2_ann_return": x2_metrics["ann_return"],
        "x2_sharpe": x2_metrics["sharpe"],
        "x2_max_drawdown": x2_metrics["max_drawdown"],
        "x2_optimizer_success_rate": x2_metrics["optimizer_success_rate"],
        "base_pass": base_pass,
        "x2_pass": x2_pass,
        "verdict": result["verdict"],
        "base_forward_return": result["forward_base"]["forward_return"],
        "base_forward_mdd": result["forward_base"]["forward_mdd"],
        "base_forward_pass": result["forward_base"]["forward_pass"],
        "x2_forward_return": result["forward_x2"]["forward_return"],
        "x2_forward_mdd": result["forward_x2"]["forward_mdd"],
        "x2_forward_pass": result["forward_x2"]["forward_pass"],
        "warnings": "; ".join(result["warnings"]),
    }


def build_summary_row(result: Dict, cost_bps_values: List[float]) -> Dict:
    """One-row summary per candidate for upgrade_candidate_summary.csv."""
    stress = result["stress"]
    base_metrics = stress["base"]["metrics"]
    x2_metrics = stress["x2"]["metrics"]
    thresholds = result["thresholds"]

    base_pass = (
        base_metrics["ann_return"] >= thresholds["base_min_ann_return"]
        and base_metrics["sharpe"] >= thresholds["base_min_sharpe"]
        and base_metrics["max_drawdown"] >= thresholds["base_min_max_drawdown"]
        and base_metrics["optimizer_success_rate"] >= thresholds["base_min_optimizer_success_rate"]
    )
    x2_pass = (
        x2_metrics["ann_return"] >= thresholds["x2_min_ann_return"]
        and x2_metrics["sharpe"] >= thresholds["x2_min_sharpe"]
        and x2_metrics["max_drawdown"] >= thresholds["base_min_max_drawdown"]
        and x2_metrics["optimizer_success_rate"] >= thresholds["x2_min_optimizer_success_rate"]
    )
    both_pass = base_pass and x2_pass
    forward_pass = (
        result["forward_base"]["forward_pass"] and result["forward_x2"]["forward_pass"]
    )

    return {
        "candidate": result["candidate"],
        "verdict": result["verdict"],
        "base_pass": base_pass,
        "x2_pass": x2_pass,
        "full_period_pass": both_pass,
        "forward_month_pass": forward_pass,
        "promotion_ready": both_pass and forward_pass,
        "base_ann_return": base_metrics["ann_return"],
        "x2_ann_return": x2_metrics["ann_return"],
        "base_sharpe": base_metrics["sharpe"],
        "x2_sharpe": x2_metrics["sharpe"],
        "base_max_drawdown": base_metrics["max_drawdown"],
        "x2_max_drawdown": x2_metrics["max_drawdown"],
        "warnings": "; ".join(result["warnings"]),
    }


def build_report(benchmark_df: pd.DataFrame, summary_df: pd.DataFrame) -> str:
    """Generate markdown report from benchmark and summary DataFrames."""
    lines = [
        "# C Fast Upgrade Benchmark Report",
        "",
        "Safety: live_trading_allowed=false, broker_execution_allowed=false.",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Full Period Pass | Forward Month Pass | Promotion Ready |",
        "|---|:---:|:---:|:---:|",
    ]
    for _, row in summary_df.iterrows():
        lines.append(
            f"| {row['candidate']} | {row['full_period_pass']} | "
            f"{row['forward_month_pass']} | {row['promotion_ready']} |"
        )

    lines.extend(["", "## Full Benchmark", ""])
    cols = [
        "candidate", "base_ann_return", "base_sharpe", "base_max_drawdown",
        "x2_ann_return", "x2_sharpe", "x2_max_drawdown",
        "base_forward_return", "base_forward_mdd", "base_forward_pass",
        "x2_forward_return", "x2_forward_mdd", "x2_forward_pass",
    ]
    available = [c for c in cols if c in benchmark_df.columns]
    lines.append("| " + " | ".join(available) + " |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for _, row in benchmark_df.iterrows():
        cells = []
        for c in available:
            val = row[c]
            if isinstance(val, float):
                cells.append(f"{val:.4f}")
            else:
                cells.append(str(val))
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="C Fast Upgrade Benchmark Runner")
    p.add_argument(
        "--prices",
        default="examples/data/internet_latest_yahoo_prices_2024_01_to_2026_03.csv",
    )
    p.add_argument("--outdir", default="demo_output/internet_latest_yahoo/cfast_upgrade_benchmark")
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
    p.add_argument("--target-return-min", type=float, default=0.10)
    p.add_argument("--optimizer-maxiter", type=int, default=1000)
    p.add_argument("--gamma", type=float, default=0.97)
    p.add_argument("--forecast-decay", type=float, default=0.90)
    p.add_argument("--shrink-mu", type=float, default=0.50)
    p.add_argument("--shrinkage", type=float, default=0.35)
    p.add_argument("--risk-aversion", type=float, default=5.0)
    p.add_argument("--turnover-penalty", type=float, default=25.0)
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    args.prices = resolve_path(args.prices)
    outdir = ensure_outdir(resolve_path(args.outdir))
    cost_bps_values = parse_cost_bps_list(args.cost_bps_list)
    min_rows = max(
        args.lookback + args.test_size + args.gap + 2,
        args.splits * args.test_size + args.gap + 1,
    )
    prices = load_validated_prices(args.prices, min_rows=min_rows)

    results: List[Dict] = []
    for candidate in CANDIDATE_IDS:
        result = run_candidate(
            candidate, prices, args, outdir / "runs" / candidate,
            cost_bps_values,
        )
        results.append(result)

    benchmark_rows = [build_benchmark_row(r, cost_bps_values) for r in results]
    summary_rows = [build_summary_row(r, cost_bps_values) for r in results]

    benchmark_df = pd.DataFrame(benchmark_rows)
    summary_df = pd.DataFrame(summary_rows)

    benchmark_df.to_csv(outdir / "upgrade_candidate_benchmark.csv", index=False)
    summary_df.to_csv(outdir / "upgrade_candidate_summary.csv", index=False)

    report = build_report(benchmark_df, summary_df)
    (outdir / "upgrade_candidate_report.md").write_text(report, encoding="utf-8")

    print(f"Benchmark complete → {outdir}")
    print(summary_df[["candidate", "full_period_pass", "forward_month_pass", "promotion_ready"]].to_string(index=False))


if __name__ == "__main__":
    main()
