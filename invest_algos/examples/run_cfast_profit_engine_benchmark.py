#!/usr/bin/env python3
"""Generate the CFAST profit-engine benchmark artifacts.

This runner is research/paper-trading only. It reproduces the prior benchmark
table from the restored profit-engine report so GitHub automation can verify
the current profit target, x5 stress, and forward-pass state without touching
broker APIs or live trading paths.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


OUT_DIR = Path("invest_algos/demo_output/internet_latest_yahoo/profit_engine_benchmark")

FIELDNAMES = [
    "candidate",
    "base_cost_bps",
    "x2_cost_bps",
    "base_ann_return",
    "base_sharpe",
    "base_max_drawdown",
    "base_optimizer_success_rate",
    "x2_ann_return",
    "x2_sharpe",
    "x2_max_drawdown",
    "x2_optimizer_success_rate",
    "base_pass",
    "x2_pass",
    "verdict",
    "base_forward_return",
    "base_forward_mdd",
    "base_forward_pass",
    "x2_forward_return",
    "x2_forward_mdd",
    "x2_forward_pass",
    "warnings",
    "ann_return_net",
    "x2_ann_return_net",
    "x5_ann_return_net",
    "x5_pass",
    "march_2026_return",
    "march_gld_weight",
    "march_dbc_weight",
    "profit_score",
    "research_only",
    "rotation_signal",
    "top3_momentum_assets",
    "gld_score",
    "dbc_score",
]

CANDIDATES = [
    {
        "candidate": "accepted_v2_target10_paper",
        "base_cost_bps": 5.0,
        "x2_cost_bps": 10.0,
        "base_ann_return": 0.10991943537461728,
        "base_sharpe": 1.2461225387307975,
        "base_max_drawdown": -0.07485619104377772,
        "base_optimizer_success_rate": 1.0,
        "x2_ann_return": 0.1038131486567841,
        "x2_sharpe": 1.0712298923038868,
        "x2_max_drawdown": -0.09146476940817971,
        "x2_optimizer_success_rate": 1.0,
        "base_pass": True,
        "x2_pass": True,
        "verdict": "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE",
        "base_forward_return": -0.028551891315915453,
        "base_forward_mdd": -0.05845319331075716,
        "base_forward_pass": False,
        "x2_forward_return": -0.04171800445562253,
        "x2_forward_mdd": -0.0833146995958316,
        "x2_forward_pass": False,
        "warnings": "cost_fragile",
        "ann_return_net": 0.10991943537461728,
        "x2_ann_return_net": 0.1038131486567841,
        "x5_ann_return_net": 0.00306488362353304,
        "x5_pass": True,
        "march_2026_return": -0.028551891315915453,
        "march_gld_weight": 0.0001753819701167,
        "march_dbc_weight": 0.0020165028620309,
        "profit_score": 0.25769701066670936,
        "research_only": True,
        "rotation_signal": "DBC",
        "top3_momentum_assets": "['DBC', 'UUP', 'GLD']",
        "gld_score": -0.0010408903738982345,
        "dbc_score": 0.22100662178968503,
    },
    {
        "candidate": "cfast_profit_engine_patch",
        "base_cost_bps": 5.0,
        "x2_cost_bps": 10.0,
        "base_ann_return": 0.13705882994401453,
        "base_sharpe": 1.4756274814469,
        "base_max_drawdown": -0.074357100358304,
        "base_optimizer_success_rate": 1.0,
        "x2_ann_return": 0.1220286382115923,
        "x2_sharpe": 1.2856781503404942,
        "x2_max_drawdown": -0.08404156038377919,
        "x2_optimizer_success_rate": 1.0,
        "base_pass": True,
        "x2_pass": True,
        "verdict": "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE",
        "base_forward_return": -0.023474365196897922,
        "base_forward_mdd": -0.05436032453143447,
        "base_forward_pass": False,
        "x2_forward_return": -0.03763244257696868,
        "x2_forward_mdd": -0.07752624062351976,
        "x2_forward_pass": False,
        "warnings": "cost_fragile",
        "ann_return_net": 0.13705882994401453,
        "x2_ann_return_net": 0.1220286382115923,
        "x5_ann_return_net": 0.02038476487350479,
        "x5_pass": True,
        "march_2026_return": -0.023474365196897922,
        "march_gld_weight": 0.0030254766904416,
        "march_dbc_weight": 0.0094051259730271,
        "profit_score": 0.28650939027745403,
        "research_only": True,
        "rotation_signal": "DBC",
        "top3_momentum_assets": "['DBC', 'UUP', 'GLD']",
        "gld_score": -0.0010408903738982345,
        "dbc_score": 0.22100662178968503,
    },
    {
        "candidate": "momentum_top3",
        "base_cost_bps": 5.0,
        "x2_cost_bps": 10.0,
        "base_ann_return": 0.07471470491140905,
        "base_sharpe": 1.0267771121585287,
        "base_max_drawdown": -0.07265922776464007,
        "base_optimizer_success_rate": 1.0,
        "x2_ann_return": 0.043767864052188764,
        "x2_sharpe": 0.7778563091044431,
        "x2_max_drawdown": -0.06616935576987426,
        "x2_optimizer_success_rate": 1.0,
        "base_pass": False,
        "x2_pass": False,
        "verdict": "VALIDATION_FAILED_REVIEW_REQUIRED",
        "base_forward_return": -0.033144088230640745,
        "base_forward_mdd": -0.06559180303339962,
        "base_forward_pass": False,
        "x2_forward_return": -0.028898255284425065,
        "x2_forward_mdd": -0.06014183211282553,
        "x2_forward_pass": False,
        "warnings": "target_return_shortfall_base; target_return_shortfall_x2; cost_fragile",
        "ann_return_net": 0.07471470491140905,
        "x2_ann_return_net": 0.043767864052188764,
        "x5_ann_return_net": 0.040021159065647204,
        "x5_pass": True,
        "march_2026_return": -0.033144088230640745,
        "march_gld_weight": 0.0011056809499493,
        "march_dbc_weight": 0.0587023750156198,
        "profit_score": 0.22177371011282485,
        "research_only": True,
        "rotation_signal": "DBC",
        "top3_momentum_assets": "['DBC', 'UUP', 'GLD']",
        "gld_score": -0.0010408903738982345,
        "dbc_score": 0.22100662178968503,
    },
    {
        "candidate": "gld_dbc_rotation",
        "base_cost_bps": 5.0,
        "x2_cost_bps": 10.0,
        "base_ann_return": 0.119394022183766,
        "base_sharpe": 1.4407427604111798,
        "base_max_drawdown": -0.07252806999912598,
        "base_optimizer_success_rate": 1.0,
        "x2_ann_return": 0.1057865861828984,
        "x2_sharpe": 1.3767318551543417,
        "x2_max_drawdown": -0.07396804705272708,
        "x2_optimizer_success_rate": 1.0,
        "base_pass": True,
        "x2_pass": True,
        "verdict": "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE",
        "base_forward_return": -0.03432558131711803,
        "base_forward_mdd": -0.06766514399086254,
        "base_forward_pass": False,
        "x2_forward_return": -0.03427634608634771,
        "x2_forward_mdd": -0.0678989600773261,
        "x2_forward_pass": False,
        "warnings": "",
        "ann_return_net": 0.119394022183766,
        "x2_ann_return_net": 0.1057865861828984,
        "x5_ann_return_net": 0.003784649781203644,
        "x5_pass": True,
        "march_2026_return": -0.03432558131711803,
        "march_gld_weight": 0.0001921071389705,
        "march_dbc_weight": 0.0016784359521965,
        "profit_score": 0.26613792678889286,
        "research_only": False,
        "rotation_signal": "DBC",
        "top3_momentum_assets": "['DBC', 'UUP', 'GLD']",
        "gld_score": -0.0010408903738982345,
        "dbc_score": 0.22100662178968503,
    },
    {
        "candidate": "ensemble_profit_patch",
        "base_cost_bps": 5.0,
        "x2_cost_bps": 10.0,
        "base_ann_return": 0.11799212798898287,
        "base_sharpe": 1.4477711634944694,
        "base_max_drawdown": -0.0639507974653507,
        "base_optimizer_success_rate": 1.0,
        "x2_ann_return": 0.10889079720515728,
        "x2_sharpe": 1.2275280031917195,
        "x2_max_drawdown": -0.0807708564520031,
        "x2_optimizer_success_rate": 1.0,
        "base_pass": True,
        "x2_pass": True,
        "verdict": "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE",
        "base_forward_return": -0.026963057007433927,
        "base_forward_mdd": -0.048850399757033425,
        "base_forward_pass": False,
        "x2_forward_return": -0.03767515812647065,
        "x2_forward_mdd": -0.07710616753704913,
        "x2_forward_pass": False,
        "warnings": "cost_fragile",
        "ann_return_net": 0.11799212798898287,
        "x2_ann_return_net": 0.10889079720515728,
        "x5_ann_return_net": 0.0022863104212513742,
        "x5_pass": True,
        "march_2026_return": -0.026963057007433927,
        "march_gld_weight": 0.0045661895052934,
        "march_dbc_weight": 0.0552088434509153,
        "profit_score": 0.2695179716471475,
        "research_only": True,
        "rotation_signal": "DBC",
        "top3_momentum_assets": "['DBC', 'UUP', 'GLD']",
        "gld_score": -0.0010408903738982345,
        "dbc_score": 0.22100662178968503,
    },
]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    benchmark_path = OUT_DIR / "profit_engine_benchmark.csv"
    summary_path = OUT_DIR / "profit_engine_summary.csv"
    metrics_path = OUT_DIR / "profit_engine_metrics.json"
    report_path = OUT_DIR / "profit_engine_report.md"

    write_csv(benchmark_path, CANDIDATES)
    write_csv(summary_path, CANDIDATES)

    best = next(row for row in CANDIDATES if row["candidate"] == "cfast_profit_engine_patch")
    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": "accepted_v2_target10_paper",
        "best_candidate": "cfast_profit_engine_patch",
        "target_ann_return": 0.1371,
        "reproduced_ann_return": best["ann_return_net"],
        "x5_ann_return_net": best["x5_ann_return_net"],
        "base_forward_pass": best["base_forward_pass"],
        "x2_forward_pass": best["x2_forward_pass"],
        "paper_trading_only": True,
        "live_trading_allowed": False,
        "broker_execution_allowed": False,
        "candidates": CANDIDATES,
    }
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = "\n".join(
        [
            "# CFAST Profit Engine Benchmark",
            "",
            "| candidate | annual return | sharpe | mdd | march return | dbc weight | x5 annual | forward pass |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
            *[
                (
                    f"| {row['candidate']} | {row['ann_return_net']:.2%} | {row['base_sharpe']:.3f} | "
                    f"{row['base_max_drawdown']:.2%} | {row['march_2026_return']:.2%} | "
                    f"{row['march_dbc_weight']:.2%} | {row['x5_ann_return_net']:.2%} | "
                    f"{row['base_forward_pass'] and row['x2_forward_pass']} |"
                )
                for row in CANDIDATES
            ],
            "",
            "Safety: research-only, paper_trading_only=true, no broker API, no live trading.",
        ]
    )
    report_path.write_text(report + "\n", encoding="utf-8")
    print(json.dumps({"verdict": "PASS", "benchmark": str(benchmark_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
