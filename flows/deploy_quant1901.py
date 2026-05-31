"""Prefect deployment configuration for quant1901_daily_flow.

Registers the Quant1901 daily auxiliary backtest as a Prefect scheduled flow.
Requires Prefect to be installed (`pip install prefect`).
Falls back to a direct-execution guide if Prefect is not available.

Usage:
    # Register with Prefect server
    PYTHONPATH=src python flows/deploy_quant1901.py

    # Run directly (no Prefect required)
    PYTHONPATH=src python -c "from flows.quant1901_daily import quant1901_daily_flow; quant1901_daily_flow()"

Environment variables (see .env.example):
    QUANT1901_UNIVERSE    : comma-separated tickers (default: 005930.KS,000660.KS,035420.KS)
    QUANT1901_PERIOD      : lookback period (default: 2y)
    QUANT1901_OPTIMIZE    : true/false — EMA grid search (default: false, slow)
    QUANT1901_OUTPUT_DIR  : output directory (default: reports/quant1901/daily)
    PREFECT_API_URL       : Prefect server URL (optional, defaults to local ephemeral)

Safety invariants (unchanged from quant1901_runner):
    - paper/backtest only — no broker orders
    - live_trading_allowed = False always
    - broker_execution_allowed = False always
    - individual ticker failures do not abort the flow
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src/ is on path when running from repo root
_ROOT = Path(__file__).resolve().parents[1]
for _p in (str(_ROOT / "src"), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flows.quant1901_daily import (  # noqa: E402
    QUANT1901_FLOW_CRON,
    QUANT1901_FLOW_TIMEZONE,
    quant1901_daily_flow,
)


def _build_flow_params() -> dict:
    """Resolve deployment parameters from environment variables."""
    raw_universe = os.environ.get("QUANT1901_UNIVERSE", "")
    universe = (
        [t.strip().upper() for t in raw_universe.split(",") if t.strip()]
        if raw_universe
        else None  # None → resolved from env var at runtime
    )
    return {
        "universe": universe,
        "period": os.environ.get("QUANT1901_PERIOD", "2y"),
        "optimize": os.environ.get("QUANT1901_OPTIMIZE", "false").lower() in ("true", "1", "yes"),
        "dry_run": True,  # always paper-only in scheduled runs
        "output_dir": os.environ.get("QUANT1901_OUTPUT_DIR", "reports/quant1901/daily"),
    }


def deploy_with_prefect() -> None:
    """Register the flow with Prefect using the new v2/v3 deployment API."""
    try:
        # Prefect 3.x API
        from prefect.deployments import Deployment  # noqa: PLC0415
        from prefect.server.schemas.schedules import CronSchedule  # noqa: PLC0415

        params = _build_flow_params()
        deployment = Deployment.build_from_flow(
            flow=quant1901_daily_flow,
            name="quant1901-daily-krx",
            schedule=CronSchedule(cron=QUANT1901_FLOW_CRON, timezone=QUANT1901_FLOW_TIMEZONE),
            parameters=params,
            tags=["quant1901", "krx", "paper-only", "auxiliary"],
            description=(
                "Daily Quant1901 auxiliary backtest for KRX tickers. "
                "Paper/backtest only — no broker orders."
            ),
        )
        deployment_id = deployment.apply()
        print(f"✓ Deployed: quant1901-daily-krx")
        print(f"  Schedule:  {QUANT1901_FLOW_CRON} ({QUANT1901_FLOW_TIMEZONE})")
        print(f"  Params:    {params}")
        print(f"  ID:        {deployment_id}")

    except ImportError:
        print("⚠ Prefect not installed — cannot register deployment.")
        print("  Install: pip install prefect")
        print()
        _print_direct_run_guide()


def _print_direct_run_guide() -> None:
    """Print instructions for running the flow without a Prefect server."""
    params = _build_flow_params()
    print("Direct execution (no Prefect required):")
    print()
    print("  python -c \"")
    print("    from flows.quant1901_daily import quant1901_daily_flow")
    print(f"    result = quant1901_daily_flow(")
    for k, v in params.items():
        print(f"        {k}={v!r},")
    print("    )")
    print("    print(result)")
    print("  \"")
    print()
    print("Or via CLI:")
    print("  PYTHONPATH=src python -m stock_rtx4060.main quant1901-backtest \\")
    print("    --ticker 005930.KS --period 2y --optimize")


if __name__ == "__main__":
    print(f"Quant1901 Prefect deployment")
    print(f"  Flow:     quant1901_daily_flow")
    print(f"  Schedule: {QUANT1901_FLOW_CRON} ({QUANT1901_FLOW_TIMEZONE})")
    print()
    deploy_with_prefect()
