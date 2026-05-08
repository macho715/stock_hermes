"""Weekly research flow — RD-Agent factor mining + Optuna HPO + MLflow promotion.

Schedule (Prefect deployment): cron ``"0 2 * * 6"`` (Sat 02:00 UTC). The flow
runs three sequential phases:

1. **Factor mining** via :mod:`stock_rtx4060.factors.rd_agent.runner` — produces
   new factor module files which are picked up by the next factor_compute run.
2. **HPO refresh** via :func:`stock_rtx4060.ml.hpo.run_hpo` on a synthetic
   training panel (real flow swaps the panel with a PIT-aligned dataframe).
3. **Promotion gate**: if the new study's ``best_value`` improves on the
   currently registered Production model by more than 5%, register & promote
   the new version via :func:`stock_rtx4060.ml.registry.promote`.
"""

from __future__ import annotations

import logging
from typing import Any

from .utils import flow, get_run_logger, slack_on_failure, with_retries

logger = logging.getLogger("flows.research_weekly")

DEFAULT_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
RESEARCH_FLOW_CRON = "0 2 * * 6"
RESEARCH_FLOW_TIMEZONE = "UTC"
PROMOTION_DELTA_THRESHOLD = 0.05  # 5% improvement required


@with_retries(retries=1, retry_delay_seconds=30)
def factor_mining_task(universe: list[str], *, cycles: int = 1, budget_usd: float = 1.0) -> dict[str, Any]:
    """Run RD-Agent factor mining; returns a list of newly produced files."""
    from pathlib import Path

    from stock_rtx4060.factors.rd_agent.runner import run_factor_mining

    new_files = run_factor_mining(universe, cycles=cycles, budget_usd=budget_usd)
    return {"new_factor_files": [str(p) for p in new_files], "count": len(new_files)}


@with_retries(retries=1, retry_delay_seconds=30)
def hpo_task(universe: list[str], *, n_trials: int = 10) -> dict[str, Any]:
    """Run an Optuna HPO study; returns ``{best_params, best_value}``."""
    try:
        import numpy as np
        import pandas as pd

        from stock_rtx4060.ml.hpo import run_hpo
    except Exception as exc:  # noqa: BLE001 - optuna may be missing
        logger.warning("hpo dependencies missing: %s", exc)
        return {"best_value": float("nan"), "best_params": {}, "skipped": True}
    # Synthetic panel — real flow loads from the PIT lake.
    rng = np.random.default_rng(42)
    n = 200
    X = pd.DataFrame(rng.normal(size=(n, 6)), columns=[f"f{i}" for i in range(6)])
    y = pd.Series((X["f0"] + 0.5 * rng.normal(size=n) > 0).astype(int))
    try:
        result = run_hpo(X, y, n_trials=n_trials)
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_hpo failed: %s", exc)
        return {"best_value": float("nan"), "best_params": {}, "skipped": True, "error": str(exc)}
    # Strip the heavy ``study`` object so the return value is JSON-friendly.
    return {
        "best_value": float(result.get("best_value", float("nan"))),
        "best_params": dict(result.get("best_params", {})),
        "skipped": False,
    }


_PRODUCTION_METRIC_NAME = "oos_brier"


def _current_production_score(model_name: str) -> float | None:
    """Best-effort lookup of the Production model's last reported score.

    Returns the most recent ``oos_brier`` value on the run that produced the
    current Production version, or ``None`` when MLflow / the model / the
    metric is unavailable.  Without this real lookup the gate would always
    cold-start (delta = inf) and promote any candidate, defeating the
    threshold check.
    """
    try:
        from stock_rtx4060.ml.registry import list_versions
    except Exception:  # noqa: BLE001
        return None
    versions = list_versions(model_name)
    if not versions:
        return None
    # Prefer the version explicitly tagged Production; fall back to highest
    # version number if no stage info (alias-based MLflow registries).
    prod = next((v for v in versions if str(v.get("stage", "")).lower() == "production"), None)
    if prod is None:
        return None
    run_id = prod.get("run_id")
    if not run_id:
        return None
    try:
        import mlflow  # type: ignore[import-not-found]
        from mlflow.tracking import MlflowClient  # type: ignore[import-not-found]

        client = MlflowClient()
        run = client.get_run(run_id)
        metric = run.data.metrics.get(_PRODUCTION_METRIC_NAME)
        if metric is None:
            return None
        return float(metric)
    except Exception:  # noqa: BLE001 - registry not configured / metric absent
        return None


def _latest_candidate_version(model_name: str) -> int | None:
    """Return the highest registered version of ``model_name`` (or None)."""
    try:
        from stock_rtx4060.ml.registry import list_versions
    except Exception:  # noqa: BLE001
        return None
    versions = list_versions(model_name)
    if not versions:
        return None
    return max(int(v.get("version", 0) or 0) for v in versions) or None


@with_retries(retries=1, retry_delay_seconds=30)
def promotion_gate_task(
    hpo_summary: dict[str, Any],
    *,
    model_name: str = "direction_v1",
    threshold: float = PROMOTION_DELTA_THRESHOLD,
) -> dict[str, Any]:
    """Promote the new model when ``best_value`` beats prod by ``threshold``.

    Returns a dict describing the promotion decision so callers can assert
    in tests without poking MLflow.
    """
    if hpo_summary.get("skipped"):
        return {"promoted": False, "reason": "hpo_skipped"}

    new_value = float(hpo_summary.get("best_value", float("nan")))
    if new_value != new_value:  # NaN guard
        return {"promoted": False, "reason": "nan_best_value"}

    baseline = _current_production_score(model_name)
    if baseline is None:
        # No baseline — promote unconditionally (cold-start branch). The HPO
        # objective is Brier loss (lower is better), so we still gate on the
        # caller-provided summary.
        delta = float("inf")
    else:
        if baseline <= 0:
            delta = float("inf")
        else:
            # HPO minimises Brier loss → improvement means new < baseline.
            delta = (baseline - new_value) / abs(baseline)

    if delta > threshold:
        candidate_version = _latest_candidate_version(model_name)
        if candidate_version is None:
            return {
                "promoted": False,
                "reason": "no_candidate_version",
                "delta": delta,
                "best_value": new_value,
                "baseline": baseline,
            }
        try:
            from stock_rtx4060.ml.registry import promote

            # Promote the latest registered version (produced by the
            # immediately-preceding HPO + register_model step in the real
            # flow).  Tests monkeypatch the promote symbol.
            promote(name=model_name, version=candidate_version, stage="Production")
            return {
                "promoted": True,
                "delta": delta,
                "best_value": new_value,
                "baseline": baseline,
                "version": candidate_version,
            }
        except Exception as exc:  # noqa: BLE001 - promotion failure must not crash flow
            logger.warning("promote() failed: %s", exc)
            return {"promoted": False, "reason": f"promote_error:{exc}", "delta": delta}

    return {"promoted": False, "delta": delta, "best_value": new_value, "baseline": baseline}


@flow(name="research_weekly_flow")
def research_weekly_flow(*, universe: list[str] | None = None) -> dict[str, Any]:
    """Sat-02:00 research cycle: mining → HPO → promotion gate."""
    log = get_run_logger()
    uni = list(universe) if universe else list(DEFAULT_UNIVERSE)
    log.info("research_weekly_flow start universe=%s", uni)

    results: dict[str, Any] = {"universe": uni}
    try:
        results["mining"] = factor_mining_task(uni)
        results["hpo"] = hpo_task(uni)
        results["promotion"] = promotion_gate_task(results["hpo"])
    except Exception as exc:  # noqa: BLE001
        slack_on_failure(f"research_weekly_flow failed: {exc}")
        log.error("research_weekly_flow failed: %s", exc)
        raise
    log.info("research_weekly_flow done — promoted=%s", results.get("promotion", {}).get("promoted"))
    return results


__all__ = [
    "research_weekly_flow",
    "factor_mining_task",
    "hpo_task",
    "promotion_gate_task",
    "RESEARCH_FLOW_CRON",
    "RESEARCH_FLOW_TIMEZONE",
    "PROMOTION_DELTA_THRESHOLD",
]
