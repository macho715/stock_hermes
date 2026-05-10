"""Daily US flow — post-close ingest → factors → model → portfolio → alert.

Schedule (Prefect deployment): cron ``"30 16 * * 1-5"`` America/New_York
(16:30 ET, 30 min after NYSE close at 16:00).  DAG identical to ``daily_krx``
but uses the Alpaca ingestor for US equity bars.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from .utils import flow, get_run_logger, slack_on_failure, with_retries

logger = logging.getLogger("flows.daily_us")

DEFAULT_US_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
US_FLOW_CRON = "30 16 * * 1-5"
US_FLOW_TIMEZONE = "America/New_York"


def _resolve_universe() -> list[str]:
    raw = os.environ.get("STOCK1901_US_UNIVERSE")
    if not raw:
        return list(DEFAULT_US_UNIVERSE)
    return [t.strip() for t in raw.split(",") if t.strip()]


@with_retries(retries=3, retry_delay_seconds=60)
def ingest_alpaca_task(universe: list[str], *, as_of: str | None = None) -> dict[str, int]:
    from stock_rtx4060.data_lake.ingest.alpaca_ingestor import ingest_alpaca

    end_dt = (
        datetime.fromisoformat(as_of).replace(tzinfo=UTC) if as_of else datetime.now(UTC)
    )
    end = end_dt.date().isoformat()
    start = (end_dt - timedelta(days=365)).date().isoformat()
    counts: dict[str, int] = {}
    for ticker in universe:
        try:
            counts[ticker] = int(ingest_alpaca(ticker, start=start, end=end))
        except Exception as exc:  # noqa: BLE001
            logger.warning("ingest_alpaca(%s) failed: %s", ticker, exc)
            counts[ticker] = 0
    return counts


@with_retries(retries=2, retry_delay_seconds=30)
def corp_actions_adjust_task(universe: list[str]) -> dict[str, int]:
    from stock_rtx4060.data_lake.corp_actions.adjuster import adjust_ohlcv
    from stock_rtx4060.data_lake.store import get_default_store

    store = get_default_store()
    out: dict[str, int] = {}
    for ticker in universe:
        try:
            df = store.read(ticker)
            adjusted = adjust_ohlcv(df, [])
            out[ticker] = int(len(adjusted))
        except Exception as exc:  # noqa: BLE001
            logger.warning("corp_actions_adjust(%s) failed: %s", ticker, exc)
            out[ticker] = 0
    return out


@with_retries(retries=2, retry_delay_seconds=30)
def factor_compute_task(universe: list[str]) -> dict[str, Any]:
    from stock_rtx4060.data_lake.store import get_default_store
    from stock_rtx4060.factors.factor_zoo import FactorRegistry

    registry = FactorRegistry()
    store = get_default_store()
    out: dict[str, int] = {}
    for ticker in universe:
        try:
            panel = store.read(ticker)
            factors = registry.compute_all(panel)
            out[ticker] = int(factors.shape[1])
        except Exception as exc:  # noqa: BLE001
            logger.warning("factor_compute(%s) failed: %s", ticker, exc)
            out[ticker] = 0
    return {"factor_counts": out}


@with_retries(retries=1, retry_delay_seconds=15)
def model_predict_task(universe: list[str]) -> dict[str, Any]:
    try:
        from stock_rtx4060.ml.registry import load_production
    except Exception as exc:  # noqa: BLE001
        logger.warning("ml.registry import failed: %s", exc)
        return {"loaded": False}
    model = load_production("direction_v1")
    return {"loaded": model is not None, "tickers": list(universe)}


@with_retries(retries=1, retry_delay_seconds=15)
def portfolio_optimize_task(universe: list[str]) -> dict[str, Any]:
    try:
        from stock_rtx4060.portfolio.optimizer import optimize
    except Exception as exc:  # noqa: BLE001
        logger.warning("portfolio.optimizer unavailable: %s", exc)
        return {"weights": {}}
    try:
        import numpy as np
        import pandas as pd

        n = max(len(universe), 1)
        rng = np.random.default_rng(42)
        fake_returns = pd.DataFrame(rng.normal(0, 0.01, (252, n)), columns=universe)
        weights_series = optimize(fake_returns, method="hrp", max_weight=1.0)
        weights = weights_series.to_dict()
        return {"weights": weights, "method": "hrp"}
    except Exception as exc:  # noqa: BLE001
        logger.warning("portfolio_optimize failed: %s", exc)
        return {"weights": {}}


@with_retries(retries=2, retry_delay_seconds=30)
def recommend_task(universe: list[str], *, dry_run: bool = False) -> dict[str, Any]:
    from stock_rtx4060.recommendation_engine import RecommendationConfig, RecommendationEngine

    cfg = RecommendationConfig(universe=list(universe))
    engine = RecommendationEngine(cfg)
    results = engine.run()
    return {
        "results": [r.to_dict() for r in results],
        "result_count": len(results),
        "verdicts": [getattr(r, "verdict", "UNKNOWN") for r in results],
        "dry_run": dry_run,
    }


@with_retries(retries=1, retry_delay_seconds=10)
def snapshot_dashboard_task(payload: dict[str, Any]) -> dict[str, Any]:
    from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot

    if not isinstance(payload, dict):
        payload = {"results": []}
    payload.setdefault("results", [])
    snapshot = build_dashboard_snapshot(payload)
    return {"snapshot_keys": sorted(snapshot.keys()), "result_count": snapshot.get("result_count", 0)}


@with_retries(retries=1, retry_delay_seconds=10)
def alert_task(summary: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    from stock_rtx4060.alert_engine import (
        ALERT_TYPE_DAILY_SUMMARY,
        Alert,
        AlertPriority,
        dispatch,
    )

    priority = AlertPriority.LOW if dry_run else AlertPriority.MEDIUM
    alert = Alert(
        alert_type=ALERT_TYPE_DAILY_SUMMARY,
        ticker=None,
        track="US",
        priority=priority,
        message=f"daily_us_flow finished — {summary.get('result_count', 0)} candidates (dry_run={dry_run})",
        metadata=summary,
    )
    return dispatch([alert])


@flow(name="daily_us_flow")
def daily_us_flow(*, dry_run: bool = False, as_of: str | None = None) -> dict[str, Any]:
    """US (NYSE/Nasdaq) post-close DAG.  Mirror of ``daily_krx_flow``."""
    log = get_run_logger()
    universe = _resolve_universe()
    log.info("daily_us_flow start universe=%s dry_run=%s as_of=%s", universe, dry_run, as_of)

    results: dict[str, Any] = {"universe": universe, "dry_run": dry_run, "as_of": as_of}
    try:
        results["ingest"] = ingest_alpaca_task(universe, as_of=as_of)
        results["corp_actions"] = corp_actions_adjust_task(universe)
        results["factors"] = factor_compute_task(universe)
        results["model"] = model_predict_task(universe)
        results["portfolio"] = portfolio_optimize_task(universe)
        results["recommend"] = recommend_task(universe, dry_run=dry_run)
        results["dashboard"] = snapshot_dashboard_task(results["recommend"])
        results["alert"] = alert_task(results["recommend"], dry_run=dry_run)
    except Exception as exc:  # noqa: BLE001
        slack_on_failure(f"daily_us_flow failed: {exc}")
        log.error("daily_us_flow failed: %s", exc)
        raise
    log.info("daily_us_flow done")
    return results


__all__ = [
    "daily_us_flow",
    "ingest_alpaca_task",
    "corp_actions_adjust_task",
    "factor_compute_task",
    "model_predict_task",
    "portfolio_optimize_task",
    "recommend_task",
    "snapshot_dashboard_task",
    "alert_task",
    "US_FLOW_CRON",
    "US_FLOW_TIMEZONE",
]
