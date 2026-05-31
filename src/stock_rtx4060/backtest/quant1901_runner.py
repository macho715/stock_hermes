"""Quant1901 backtest plugin for the stock_rtx4060 backtest infrastructure.

Wraps quant1901_executor.run_backtest() and converts the result into
dashboard_snapshot.v1 format, including policy verdicts and validation gates.

Execution controls: paper/backtest only. Live trading is blocked.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Allow quant1901_executor to be imported from the bundle path when running
# tests directly. Callers can also insert the bundle path before importing.
_BUNDLE_PATH = Path(__file__).parents[3] / "quant1901_executable_bundle"
if _BUNDLE_PATH.exists() and str(_BUNDLE_PATH) not in sys.path:
    sys.path.insert(0, str(_BUNDLE_PATH))

from quant1901_executor import (  # noqa: E402
    RiskLimits,
    StrategyConfig,
    BacktestResult,
    run_backtest,
)

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Policy decision (2026-05-31):
# Real-data test on 005930.KS (2y, yfinance) returned BLOCKED_RISK_HALT
# (var_limit breached, sharpe=-0.07, calmar=-0.05, halt_reason=var_limit).
# This is CORRECT behavior — 005930.KS experienced a sustained downtrend in
# 2024-2026 and the VaR kill-switch fired legitimately.
# Do NOT lower thresholds to force a PASS on a declining market.
# Thresholds are intentionally conservative for paper-trading candidate selection.
# ---------------------------------------------------------------------------
MIN_SHARPE = 0.5
MIN_CALMAR = 0.3
MAX_DRAWDOWN_ABS_PCT = 15.0          # e.g. 15 means max −15 %
MIN_TOTAL_RETURN_PCT = 0.0
TARGET_MONTHLY_10PCT_HIT_RATE = 0.33  # at least 1-in-3 months hit 10 %

# Policy verdict labels
CONDITIONAL_PASS = "CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE"
NOT_PASS = "NOT_PASS"
BLOCKED = "BLOCKED_RISK_HALT"


def _make_validation(
    rule_id: str,
    status: str,           # PASS | WARN | FAIL | BLOCK
    message: str,
    severity: str = "INFO",
) -> dict[str, str]:
    return {
        "rule_id": rule_id,
        "status": status,
        "severity": severity,
        "message": message,
    }


def _validate_metrics(m: dict[str, Any]) -> tuple[list[dict[str, str]], bool]:
    """Run all validation gates against backtest metrics.

    Returns (validations_list, all_pass_bool).
    """
    validations: list[dict[str, str]] = []
    all_pass = True

    # 1. BACKTEST_HONESTY — execution guard must confirm paper-only mode
    honesty_ok = (
        m.get("mode") == "paper_backtest_only"
        and not m.get("execution_guard", {}).get("live_orders_enabled", True)
    )
    validations.append(
        _make_validation(
            "BACKTEST_HONESTY",
            "PASS" if honesty_ok else "FAIL",
            "Execution guard confirms paper/backtest-only mode"
            if honesty_ok
            else "Execution guard not in paper-only mode — live order risk detected",
            severity="CRITICAL" if not honesty_ok else "INFO",
        )
    )
    if not honesty_ok:
        all_pass = False

    # 2. SHARPE — annualised Sharpe >= threshold
    sharpe = float(m.get("sharpe", 0.0))
    sharpe_ok = sharpe >= MIN_SHARPE
    validations.append(
        _make_validation(
            "SHARPE",
            "PASS" if sharpe_ok else "WARN",
            f"Sharpe {sharpe:.4f} >= {MIN_SHARPE}" if sharpe_ok else f"Sharpe {sharpe:.4f} < {MIN_SHARPE}",
            severity="WARN" if not sharpe_ok else "INFO",
        )
    )
    if not sharpe_ok:
        all_pass = False

    # 3. CALMAR — Calmar ratio >= threshold
    calmar = float(m.get("calmar", 0.0))
    calmar_ok = calmar >= MIN_CALMAR
    validations.append(
        _make_validation(
            "CALMAR",
            "PASS" if calmar_ok else "WARN",
            f"Calmar {calmar:.4f} >= {MIN_CALMAR}" if calmar_ok else f"Calmar {calmar:.4f} < {MIN_CALMAR}",
            severity="WARN" if not calmar_ok else "INFO",
        )
    )
    if not calmar_ok:
        all_pass = False

    # 4. MAX_DRAWDOWN — absolute drawdown must stay within limit
    dd_pct = abs(float(m.get("max_drawdown_pct", 0.0)))
    dd_ok = dd_pct <= MAX_DRAWDOWN_ABS_PCT
    validations.append(
        _make_validation(
            "MAX_DRAWDOWN",
            "PASS" if dd_ok else "FAIL",
            f"Max drawdown {dd_pct:.2f}% <= {MAX_DRAWDOWN_ABS_PCT}%"
            if dd_ok
            else f"Max drawdown {dd_pct:.2f}% exceeds limit {MAX_DRAWDOWN_ABS_PCT}%",
            severity="HIGH" if not dd_ok else "INFO",
        )
    )
    if not dd_ok:
        all_pass = False

    # 5. TARGET_RETURN_10PCT — monthly 10 % hit rate as promotion gate
    hit_rate = float(m.get("monthly_10pct_target_hit_rate", 0.0))
    target_ok = hit_rate >= TARGET_MONTHLY_10PCT_HIT_RATE
    validations.append(
        _make_validation(
            "TARGET_RETURN_10PCT",
            "PASS" if target_ok else "WARN",
            f"Monthly 10% hit rate {hit_rate:.2%} >= {TARGET_MONTHLY_10PCT_HIT_RATE:.0%}"
            if target_ok
            else (
                f"TARGET_RETURN_SHORTFALL: monthly 10% hit rate {hit_rate:.2%} "
                f"< {TARGET_MONTHLY_10PCT_HIT_RATE:.0%} — promotion blocked"
            ),
            severity="WARN" if not target_ok else "INFO",
        )
    )
    # TARGET_RETURN_SHORTFALL is a promotion_blocker (WARN severity) but
    # does not flip all_pass to False by itself; it surfaces as a condition.

    return validations, all_pass


def _choose_verdict(m: dict[str, Any], all_pass: bool) -> str:
    if m.get("risk_halt"):
        return BLOCKED
    if all_pass:
        return CONDITIONAL_PASS
    return NOT_PASS


def _to_snapshot(
    result: BacktestResult,
    ticker: str,
    optimized: bool,
) -> dict[str, Any]:
    """Convert a BacktestResult into dashboard_snapshot.v1 format."""
    m = result.metrics
    validations, all_pass = _validate_metrics(m)
    verdict = _choose_verdict(m, all_pass)

    hit_rate = float(m.get("monthly_10pct_target_hit_rate", 0.0))
    promotion_blockers = []
    if hit_rate < TARGET_MONTHLY_10PCT_HIT_RATE:
        promotion_blockers.append(
            {
                "blocker": "TARGET_RETURN_SHORTFALL",
                "detail": (
                    f"monthly_10pct_target_hit_rate={hit_rate:.2%} "
                    f"< required {TARGET_MONTHLY_10PCT_HIT_RATE:.0%}"
                ),
            }
        )

    result_item: dict[str, Any] = {
        "ticker": ticker,
        "track": "quant1901",
        "backtest_source": "quant1901_executor",
        "optimized": optimized,
        # Execution controls — always locked to paper/backtest
        "execution_controls": {
            "live_trading_allowed": False,
            "broker_execution_allowed": False,
            "mode": "paper_backtest_only",
            "execution_lag": m.get("execution_guard", {}).get("execution_lag", "next_bar"),
        },
        # Core metrics (surfaced for dashboard display)
        "metrics": {
            "total_return_pct": m.get("total_return_pct"),
            "annualized_return_pct": m.get("annualized_return_pct"),
            "max_drawdown_pct": m.get("max_drawdown_pct"),
            "volatility_pct": m.get("volatility_pct"),
            "sharpe": m.get("sharpe"),
            "calmar": m.get("calmar"),
            "var_5_pct": m.get("var_5_pct"),
            "trades": m.get("trades"),
            "monthly_10pct_target_hit_rate": hit_rate,
            "risk_halt": m.get("risk_halt"),
            "halt_reason": m.get("halt_reason"),
        },
        # Validation gates
        "validations": validations,
        # Policy verdicts
        "policy_verdicts": {
            "C_fast": verdict,
        },
        # Promotion blockers (subset of validations with blocking semantics)
        "promotion_blockers": promotion_blockers,
        # Screening flag required by dashboard_bridge schema
        "screening_output_only": True,
    }

    snapshot: dict[str, Any] = {
        "schema_version": "dashboard_snapshot.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "quant1901_runner",
        "mode": "report_only",
        "disclaimer": (
            "backtest/paper-trading output only; "
            "manual approval required; "
            "no broker order execution; "
            "not financial advice"
        ),
        "result_count": 1,
        "results": [result_item],
    }
    return snapshot


class Quant1901Runner:
    """Integrate quant1901 with the stock_rtx4060 backtest infrastructure.

    Usage::

        runner = Quant1901Runner()
        snapshot = runner.run(ohlcv_df, ticker="005930.KS")
        # snapshot["schema_version"] == "dashboard_snapshot.v1"
        # snapshot["results"][0]["execution_controls"]["live_trading_allowed"] == False
    """

    def __init__(
        self,
        config: StrategyConfig | None = None,
        risk: RiskLimits | None = None,
    ) -> None:
        self.config = config or StrategyConfig()
        self.risk = risk or RiskLimits()

    def run(
        self,
        ohlcv: pd.DataFrame,
        ticker: str,
        *,
        optimize: bool = False,
    ) -> dict[str, Any]:
        """Run backtest and return a dashboard_snapshot.v1-compatible dict.

        Parameters
        ----------
        ohlcv:
            OHLCV DataFrame with columns Open, High, Low, Close, Volume and a
            DatetimeIndex. Use ``make_synthetic_ohlcv`` for smoke tests.
        ticker:
            Ticker symbol used for labelling results (e.g. "005930.KS").
        optimize:
            When True, triggers quant1901_executor's grid search to find the
            best StrategyConfig before backtesting. Currently a thin wrapper;
            the optimised config is stored on ``self.config`` after the call.

        Returns
        -------
        dict
            dashboard_snapshot.v1 payload ready for ``json.dumps``.
        """
        if optimize:
            from quant1901_executor import optimize_parameters  # noqa: PLC0415

            best_config, _ = optimize_parameters(
                ohlcv,
                self.risk,
                fast_grid=[5, 8, 10, 12, 15],
                slow_grid=[20, 30, 40, 60],
                base_config=self.config,
            )
            self.config = best_config

        result: BacktestResult = run_backtest(ohlcv, self.config, self.risk)
        return _to_snapshot(result, ticker=ticker, optimized=optimize)
