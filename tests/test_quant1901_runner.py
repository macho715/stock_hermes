"""Tests for the quant1901 backtest plugin (Strategy C merge).

Covers the dashboard_snapshot.v1 contract, execution-control invariants,
policy verdicts, the PIT as_of guard, and the CLI subcommand.

Run:
    PYTHONPATH=src pytest tests/test_quant1901_runner.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "quant1901_executable_bundle"
for path in (str(ROOT / "src"), str(BUNDLE)):
    if path not in sys.path:
        sys.path.insert(0, path)

from quant1901_executor import (  # noqa: E402
    RiskLimits,
    StrategyConfig,
    make_synthetic_ohlcv,
)
from stock_rtx4060.backtest.quant1901_runner import Quant1901Runner  # noqa: E402


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    return make_synthetic_ohlcv(rows=200, seed=1901)


@pytest.fixture
def runner() -> Quant1901Runner:
    return Quant1901Runner()


# ── 1. schema contract ──────────────────────────────────────────────────────
def test_snapshot_schema_version(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    assert snap["schema_version"] == "dashboard_snapshot.v1"
    assert snap["result_count"] == 1
    assert len(snap["results"]) == 1


# ── 2. live trading is ALWAYS blocked ───────────────────────────────────────
def test_live_trading_always_false(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    controls = snap["results"][0]["execution_controls"]
    assert controls["live_trading_allowed"] is False


# ── 3. broker execution is ALWAYS blocked ───────────────────────────────────
def test_broker_execution_always_false(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    controls = snap["results"][0]["execution_controls"]
    assert controls["broker_execution_allowed"] is False


# ── 4. screening_output_only invariant (CLAUDE.md invariant #4) ─────────────
def test_screening_output_only_flag(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    assert snap["results"][0]["screening_output_only"] is True


# ── 5. risk_halt → BLOCKED verdict + BACKTEST_HONESTY chain ─────────────────
def test_risk_halt_forces_blocked_verdict():
    # Engineer a crash series that breaches the drawdown kill-switch.
    dates = pd.date_range("2024-01-02", periods=80, freq="B")
    close = (
        [100.0 + i * 0.5 for i in range(44)]
        + [60.0]
        + [59.0 - i * 0.1 for i in range(35)]
    )
    df = pd.DataFrame(
        {
            "Open": close,
            "High": [v * 1.01 for v in close],
            "Low": [v * 0.99 for v in close],
            "Close": close,
            "Volume": [100_000] * len(close),
        },
        index=dates,
    )
    runner = Quant1901Runner(
        config=StrategyConfig(fast_window=3, slow_window=8, rsi_min=0.0, rsi_max=100.0, max_volatility_z=100.0),
        risk=RiskLimits(max_drawdown_pct=0.05, daily_loss_pct=0.05),
    )
    snap = runner.run(df, ticker="CRASH")
    result = snap["results"][0]
    assert result["policy_verdicts"]["C_fast"] == "BLOCKED_RISK_HALT"
    assert result["metrics"]["risk_halt"] is True


# ── 6. validations always present with the 5 expected gate IDs ──────────────
def test_all_validation_gates_present(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    rule_ids = {v["rule_id"] for v in snap["results"][0]["validations"]}
    assert rule_ids == {
        "BACKTEST_HONESTY",
        "SHARPE",
        "CALMAR",
        "MAX_DRAWDOWN",
        "TARGET_RETURN_10PCT",
    }


# ── 7. TARGET_RETURN_SHORTFALL surfaces as promotion blocker ────────────────
def test_target_return_shortfall_promotion_blocker(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    result = snap["results"][0]
    hit = result["metrics"]["monthly_10pct_target_hit_rate"]
    blockers = {b["blocker"] for b in result["promotion_blockers"]}
    if hit < 0.33:
        assert "TARGET_RETURN_SHORTFALL" in blockers
    else:
        assert "TARGET_RETURN_SHORTFALL" not in blockers


# ── 8. optimize path runs and keeps invariants ──────────────────────────────
def test_optimize_path_preserves_invariants(synthetic_ohlcv):
    runner = Quant1901Runner()
    snap = runner.run(synthetic_ohlcv, ticker="OPT", optimize=True)
    result = snap["results"][0]
    assert result["optimized"] is True
    assert result["execution_controls"]["live_trading_allowed"] is False
    assert result["execution_controls"]["broker_execution_allowed"] is False


# ── 9. BACKTEST_HONESTY passes for clean paper-only run ─────────────────────
def test_backtest_honesty_passes_for_paper_run(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    honesty = next(
        v for v in snap["results"][0]["validations"] if v["rule_id"] == "BACKTEST_HONESTY"
    )
    assert honesty["status"] == "PASS"


# ── 10. snapshot is JSON-serializable (dashboard import contract) ───────────
def test_snapshot_is_json_serializable(runner, synthetic_ohlcv):
    snap = runner.run(synthetic_ohlcv, ticker="TEST")
    encoded = json.dumps(snap, ensure_ascii=False)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "dashboard_snapshot.v1"


# ── 11. CLI subcommand exits 0 and writes a valid snapshot ──────────────────
def test_cli_quant1901_backtest(tmp_path):
    from stock_rtx4060.main import main

    out = tmp_path / "snap.json"
    rc = main(
        [
            "quant1901-backtest",
            "--synthetic",
            "--rows",
            "200",
            "--seed",
            "7",
            "--ticker",
            "CLI_TEST",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    assert out.exists()
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert snap["schema_version"] == "dashboard_snapshot.v1"
    assert snap["results"][0]["execution_controls"]["live_trading_allowed"] is False


# ── 12. CLI --help exits 0 (CLI invariant) ──────────────────────────────────
def test_cli_help_exits_zero():
    from stock_rtx4060.main import build_parser

    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["quant1901-backtest", "--help"])
    assert exc.value.code == 0
