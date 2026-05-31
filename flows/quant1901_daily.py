"""Daily Quant1901 auxiliary backtest flow.

Runs after the main daily_krx flow.  Executes the quant1901 paper/backtest
strategy on each ticker in the universe and logs results to MLflow + saves
dashboard_snapshot.v1 JSON files.

Schedule (Prefect deployment): cron ``"00 17 * * 1-5"`` Asia/Seoul — 30 min
after daily_krx (16:30 KST).

Safety contract (unchanged from quant1901_runner):
- Paper/backtest only — no broker orders are placed.
- ``execution_controls.live_trading_allowed = False`` always.
- ``execution_controls.broker_execution_allowed = False`` always.
- Quant1901 failures do NOT fail the overall flow; individual errors are logged.
- Quant1901 results NEVER upgrade a RED/AMBER recommendation to GREEN.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .utils import flow, get_run_logger, with_retries

logger = logging.getLogger("flows.quant1901_daily")

# Default universe — overridable via env var (comma-separated, with .KS/.KQ suffix)
_DEFAULT_UNIVERSE_ENV = "QUANT1901_UNIVERSE"
_DEFAULT_TICKERS = ["005930.KS", "000660.KS", "035420.KS"]

QUANT1901_FLOW_CRON = "00 17 * * 1-5"
QUANT1901_FLOW_TIMEZONE = "Asia/Seoul"


def _resolve_universe() -> list[str]:
    raw = os.environ.get(_DEFAULT_UNIVERSE_ENV)
    if raw:
        return [t.strip().upper() for t in raw.split(",") if t.strip()]
    return _DEFAULT_TICKERS


def _mlflow_log_safe(run_name: str, metrics: dict[str, Any], params: dict[str, Any]) -> None:
    """Log to MLflow if available; silently skip if not installed or server unreachable."""
    try:
        import mlflow  # noqa: PLC0415

        with mlflow.start_run(run_name=run_name):
            mlflow.log_metrics(
                {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float)) and v is not None}
            )
            mlflow.log_params({k: str(v) for k, v in params.items()})
    except Exception as exc:  # noqa: BLE001
        logger.warning("MLflow logging skipped for %s: %s", run_name, exc)


@flow(name="quant1901-daily")
def quant1901_daily_flow(
    universe: list[str] | None = None,
    period: str = "2y",
    optimize: bool = False,
    dry_run: bool = True,
    output_dir: str = "reports/quant1901/daily",
) -> dict[str, Any]:
    """Run quant1901 auxiliary backtests for each ticker and persist results.

    Parameters
    ----------
    universe:
        Tickers to process. Falls back to ``QUANT1901_UNIVERSE`` env var or
        the built-in default list.
    period:
        Lookback period passed to ``load_ohlcv_with_provider`` (e.g. "2y").
    optimize:
        When True, runs EMA grid search via ``optimize_parameters`` before the
        final backtest.  Increases runtime significantly.
    dry_run:
        When True (default), all execution is paper/backtest only.  Setting to
        False does NOT enable live trading — the quant1901 runner always keeps
        ``live_trading_allowed=False``.
    output_dir:
        Root directory for snapshot JSON files.

    Returns
    -------
    dict
        Summary with per-ticker status, verdicts, and output paths.
    """
    run_logger = get_run_logger()
    tickers: list[str] = universe or _resolve_universe()
    run_ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    run_logger.info(
        "quant1901_daily_flow starting — %d tickers, period=%s, optimize=%s, dry_run=%s",
        len(tickers),
        period,
        optimize,
        dry_run,
    )

    summary: dict[str, Any] = {
        "run_ts": run_ts,
        "universe": tickers,
        "period": period,
        "optimize": optimize,
        "dry_run": dry_run,
        "results": {},
    }

    # Lazy imports — deferred to keep the module importable even when stock_rtx4060
    # is not on sys.path at import time (e.g. in a minimal test environment).
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from stock_rtx4060.data_providers import load_ohlcv_with_provider  # noqa: PLC0415
    from stock_rtx4060.backtest.quant1901_runner import Quant1901Runner  # noqa: PLC0415

    for ticker in tickers:
        ticker_result: dict[str, Any] = {"status": "SKIPPED", "verdict": None, "output_path": None, "error": None}
        try:
            # --- load OHLCV via existing data provider stack ---

            provider_result = load_ohlcv_with_provider(ticker, period, command="quant1901-daily")
            df = provider_result.frame
            run_logger.info("%s: loaded %d rows from %s", ticker, len(df), provider_result.source)

            # --- run quant1901 backtest ---
            runner = Quant1901Runner()
            snap = runner.run(df, ticker=ticker, optimize=optimize)
            result_item = snap["results"][0]
            verdict = result_item["policy_verdicts"]["C_fast"]
            metrics = result_item.get("metrics") or {}

            # --- persist snapshot ---
            safe_ticker = ticker.replace(".", "_")
            out_path = Path(output_dir) / safe_ticker / f"snapshot_{run_ts}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

            # --- MLflow logging (non-blocking) ---
            _mlflow_log_safe(
                run_name=f"quant1901_{safe_ticker}_{run_ts}",
                metrics=metrics,
                params={
                    "ticker": ticker,
                    "period": period,
                    "optimize": str(optimize),
                    "verdict": verdict,
                    "source": provider_result.source,
                },
            )

            ticker_result = {
                "status": "OK",
                "verdict": verdict,
                "output_path": str(out_path),
                "error": None,
                "live_trading_allowed": result_item["execution_controls"]["live_trading_allowed"],
                "broker_execution_allowed": result_item["execution_controls"]["broker_execution_allowed"],
            }
            run_logger.info("%s: %s → %s", ticker, verdict, out_path)

        except Exception as exc:  # noqa: BLE001 — individual failures must not abort the flow
            ticker_result = {
                "status": "ERROR",
                "verdict": None,
                "output_path": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            run_logger.error("%s: FAILED — %s", ticker, exc)

        summary["results"][ticker] = ticker_result

    ok_count = sum(1 for v in summary["results"].values() if v["status"] == "OK")
    run_logger.info(
        "quant1901_daily_flow done — %d/%d OK",
        ok_count,
        len(tickers),
    )
    return summary
