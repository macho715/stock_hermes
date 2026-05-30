from pathlib import Path
import json
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from algos.common import make_demo_prices  # noqa: E402
from examples.run_cfast_validation import (  # noqa: E402
    C_FAIL,
    PROMOTION_BLOCKED_COST,
    PROMOTION_BLOCKED_TARGET_RETURN,
    build_execution_controls,
    build_thresholds,
    evaluate_policy,
    main,
)


def test_cfast_validation_runner_writes_required_outputs(tmp_path):
    prices_path = tmp_path / "prices.csv"
    outdir = tmp_path / "validation"
    prices = make_demo_prices(n_days=105, seed=7)
    prices.reset_index(names="Date").to_csv(prices_path, index=False)

    main([
        "--prices", str(prices_path),
        "--outdir", str(outdir),
        "--cost-bps-list", "5,10",
        "--splits", "2",
        "--gap", "1",
        "--test-size", "10",
        "--lookback", "80",
        "--rebalance-days", "20",
        "--horizon", "1",
    ])

    expected = [
        "validation_summary.json",
        "validation_report.md",
        "latest_weights.csv",
        "cost_stress_summary.csv",
    ]
    for name in expected:
        assert (outdir / name).exists()

    summary = json.loads((outdir / "validation_summary.json").read_text(encoding="utf-8"))
    assert set(summary) >= {
        "data_metadata",
        "policy_verdicts",
        "thresholds",
        "execution_controls",
        "c_fast_cost_stress",
        "latest_weights",
        "warnings",
    }
    assert summary["policy_verdicts"]["A"] == "HOLD_DIAGNOSTIC_ONLY"
    assert summary["policy_verdicts"]["B"] == "REJECT_RETRAIN"
    assert summary["execution_controls"]["broker_execution_allowed"] is False
    assert summary["execution_controls"]["live_trading_allowed"] is False
    assert "fallback_rate" in summary["c_fast_cost_stress"][0]
    assert summary["return_policy"]["target_return_metric"] == "annualized_net_return"
    assert summary["thresholds"]["base_min_ann_return"] == 0.10
    assert "target_return_pass" in summary["c_fast_cost_stress"][0]
    if len(summary["c_fast_cost_stress"]) > 2:
        assert summary["c_fast_cost_stress"][2]["target_return_min"] is None

    diagnostics = pd.read_csv(outdir / "runs" / "base_5bps" / "optimizer_diagnostics.csv")
    assert {"fallback_used", "fallback_reason", "optimizer_iterations"} <= set(diagnostics.columns)


def test_cost_fragile_blocks_promotion_but_keeps_paper_trading_mode():
    controls = build_execution_controls(
        "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE",
        ["cost_fragile"],
    )

    assert controls["execution_mode"] == "PAPER_TRADING_DRY_RUN_ONLY"
    assert controls["promotion_status"] == PROMOTION_BLOCKED_COST
    assert controls["promotion_blockers"] == [PROMOTION_BLOCKED_COST]
    assert controls["broker_execution_allowed"] is False
    assert controls["live_trading_allowed"] is False


def test_target_return_shortfall_blocks_promotion():
    def metrics(ann_return: float):
        return {
            "ann_return": ann_return,
            "ann_vol": 0.05,
            "sharpe": 1.25,
            "max_drawdown": -0.05,
            "calmar": 2.0,
            "hit_rate": 0.55,
            "avg_turnover": 0.01,
            "ann_cost_drag": 0.001,
            "optimizer_success_rate": 0.95,
            "fallback_rate": 0.0,
        }

    stress = {
        "base": {"metrics": metrics(0.101)},
        "x2": {"metrics": metrics(0.062)},
        "x5": {"metrics": metrics(0.030)},
    }

    verdict, warnings = evaluate_policy(stress, build_thresholds(0.10))
    controls = build_execution_controls(verdict, warnings)

    assert verdict == C_FAIL
    assert "target_return_shortfall_x2" in warnings
    assert controls["promotion_status"] == PROMOTION_BLOCKED_TARGET_RETURN
    assert PROMOTION_BLOCKED_TARGET_RETURN in controls["promotion_blockers"]
    assert controls["broker_execution_allowed"] is False
    assert controls["live_trading_allowed"] is False
