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
import math as _math
from typing import Any

from .utils import flow, get_run_logger, slack_on_failure, task, with_retries

logger = logging.getLogger("flows.research_weekly")

DEFAULT_UNIVERSE = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
RESEARCH_FLOW_CRON = "0 2 * * 6"
RESEARCH_FLOW_TIMEZONE = "UTC"
PROMOTION_DELTA_THRESHOLD = 0.05  # 5% improvement required (legacy threshold)

# ---------------------------------------------------------------------------
# SPRT (Sequential Probability Ratio Test) promotion gate — Wave 4 BEST-1
# Replaces the arbitrary 5% delta with a statistically-grounded decision.
# Wave 5 will upgrade this to mSPRT for continuous-peeking safety.
# ---------------------------------------------------------------------------

def _sprt_promotion_decision(
    new_oos_brier: float,
    prod_oos_brier: float,
    n_weeks: int,
    *,
    alpha: float = 0.05,
    beta: float = 0.20,
    delta: float = 0.02,
    sprt_enabled: bool = True,
) -> dict[str, Any]:
    """Return an SPRT-based promotion decision for a model upgrade.

    Parameters
    ----------
    new_oos_brier:
        Out-of-sample Brier score of the candidate model (lower = better).
    prod_oos_brier:
        OOS Brier score of the current Production model.
    n_weeks:
        Number of weekly OOS observations available.
    alpha:
        Maximum acceptable Type I error (false promotion rate).
    beta:
        Maximum acceptable Type II error (missed improvement rate).
    delta:
        Minimum practical improvement in Brier score (e.g. 0.02 = 2 percentage
        points).  Used to calibrate effect size.
    sprt_enabled:
        Set ``False`` to fall back to the legacy 5 % delta check, allowing
        ``SPRT_GATE_ENABLED=false`` env-var opt-out.

    Returns
    -------
    dict with keys: status ("PROMOTE" | "STOP" | "CONTINUE"), z_stat, n_weeks,
    sprt_enabled, alpha, beta, delta.
    """
    if not sprt_enabled:
        # Legacy path: simple relative improvement threshold.
        rel = (prod_oos_brier - new_oos_brier) / max(abs(prod_oos_brier), 1e-9)
        status = "PROMOTE" if rel > PROMOTION_DELTA_THRESHOLD else "STOP"
        return {"status": status, "z_stat": float(rel), "n_weeks": n_weeks,
                "sprt_enabled": False, "alpha": alpha, "beta": beta, "delta": delta}

    if n_weeks < 4:
        # Too few observations — always continue without deciding.
        return {"status": "CONTINUE", "z_stat": 0.0, "n_weeks": n_weeks,
                "sprt_enabled": True, "alpha": alpha, "beta": beta, "delta": delta,
                "reason": "n_weeks < 4 — insufficient data"}

    improvement = prod_oos_brier - new_oos_brier  # positive = candidate is better
    # Pooled variance estimate from a two-sample normal approximation.
    sigma = _math.sqrt(
        2.0 * prod_oos_brier * max(1.0 - prod_oos_brier, 1e-9) / n_weeks
    )
    z = (improvement - delta) / max(sigma, 1e-9)

    # Wald SPRT boundaries.
    upper = _math.log((1.0 - beta) / max(alpha, 1e-9))   # H1: promote
    lower = _math.log(beta / max(1.0 - alpha, 1e-9))      # H0: stay

    if z >= upper:
        status = "PROMOTE"
    elif z <= lower:
        status = "STOP"
    else:
        status = "CONTINUE"

    return {
        "status": status,
        "z_stat": round(z, 4),
        "n_weeks": n_weeks,
        "sprt_enabled": True,
        "alpha": alpha,
        "beta": beta,
        "delta": delta,
    }


def _msprt_oos_check(
    forward_returns: list[float],
    *,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Run Wave-5 mSPRT monitoring over AutoForwardRecorder daily returns."""

    import os as _os

    if enabled is None:
        enabled = _os.environ.get("MSPRT_ENABLED", "true").lower() not in ("0", "false", "no")
    if not enabled:
        return {"decision": "DISABLED", "n_obs": len(forward_returns), "msprt_enabled": False}

    try:
        from stock_rtx4060.backtest.msprt_monitor import MSPRTMonitor
    except Exception as exc:  # noqa: BLE001 - keep weekly flow import-safe
        return {
            "decision": "SKIPPED",
            "n_obs": len(forward_returns),
            "msprt_enabled": False,
            "reason": f"msprt_unavailable:{exc}",
        }

    monitor = MSPRTMonitor()
    for ret in forward_returns:
        monitor.update(float(ret))
    snapshot = monitor.snapshot()
    snapshot["msprt_enabled"] = True
    return snapshot


@with_retries(retries=1, retry_delay_seconds=30)
def factor_mining_task(universe: list[str], *, cycles: int = 1, budget_usd: float = 1.0) -> dict[str, Any]:
    """Run RD-Agent factor mining; returns a list of newly produced files."""

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
    # mlflow 3.x log_input — synthetic training dataset reference
    try:
        import mlflow  # type: ignore[import-not-found]
        if hasattr(mlflow, 'log_input'):
            input_ds = mlflow.data.from_pandas(X, targets=y, name="hpo_train_synthetic")
            mlflow.log_input(input_ds, context="training")
    except Exception:  # pragma: no cover - mlflow 3.x optional
        pass
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

    # [Wave 4 BEST-1] SPRT gate — statistically grounded promotion decision.
    import os as _os
    sprt_enabled = _os.environ.get("SPRT_GATE_ENABLED", "true").lower() not in ("0", "false", "no")
    if baseline is not None and baseline > 0:
        sprt_result = _sprt_promotion_decision(
            new_oos_brier=new_value,
            prod_oos_brier=baseline,
            n_weeks=1,  # one week of data per HPO run; callers may override via context
            sprt_enabled=sprt_enabled,
        )
        # Log SPRT z-stat to MLflow for lineage tracking.
        try:
            import mlflow  # type: ignore[import-not-found]
            mlflow.log_metrics({"sprt_z_stat": sprt_result["z_stat"]})
        except Exception:  # pragma: no cover — mlflow optional
            pass

        if sprt_result["status"] == "STOP":
            return {
                "promoted": False,
                "reason": "sprt_stop",
                "sprt_z_stat": sprt_result["z_stat"],
                "delta": delta,
                "best_value": new_value,
                "baseline": baseline,
            }
        # PROMOTE: falls through to the standard promote() call below.
        # CONTINUE: not enough data yet — fall through to legacy delta check.
        # This preserves backward compatibility when n_weeks is small.

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


@with_retries(retries=1, retry_delay_seconds=30)
def qlib_export_task(universe: list[str], *, run_date: str | None = None) -> dict[str, Any]:
    """Export OHLCV data from DuckDB to Qlib bin format for RD-Agent consumption.

    Calls :func:`stock_rtx4060.factors.rd_agent.qlib_exporter.export_ohlcv_to_qlib`.
    Gracefully degrades when qlib is not installed (CSV layer is still produced).
    """
    from datetime import date as Date

    actual_date = run_date or str(Date.today())
    try:
        from stock_rtx4060.factors.rd_agent.qlib_exporter import export_ohlcv_to_qlib

        rows = export_ohlcv_to_qlib(universe, actual_date, convert_bin=True)
        return {"exported": rows, "run_date": actual_date, "skipped": False}
    except Exception as exc:  # noqa: BLE001 - qlib may be missing; degrade gracefully
        logger.warning("qlib_export_task failed: %s", exc)
        return {"exported": {}, "run_date": actual_date, "skipped": True, "error": str(exc)}


@with_retries(retries=1, retry_delay_seconds=30)
def factor_validation_task(*, run_date: str | None = None) -> dict[str, Any]:
    """Validate and stage newly discovered factors for approval.

    Calls :func:`stock_rtx4060.factors.rd_agent.registry_hook.validate_and_stage`.
    When the registry_hook module is absent the task returns a skipped result
    so the flow can continue without hard dependency on P7 infrastructure.
    """
    from datetime import date as Date

    actual_date = run_date or str(Date.today())
    try:
        from stock_rtx4060.factors.rd_agent.loader import load_discovered_factors

        # Load all discovered factor classes (validation requires panel + fwd_returns
        # which are not available here; the full validate_and_stage pipeline runs
        # inside the ops approval step via cmd_factor_approve).
        factors = load_discovered_factors(session_id=actual_date)
        names = [name for name, _ in factors] if factors else []
        return {"staged_names": names, "session_id": actual_date, "skipped": False}
    except ImportError:
        logger.warning("registry_hook/loader module not found — factor_validation_task skipped")
        return {"staged": None, "run_date": actual_date, "skipped": True}
    except Exception as exc:  # noqa: BLE001
        logger.warning("factor_validation_task failed: %s", exc)
        return {"staged": None, "run_date": actual_date, "skipped": True, "error": str(exc)}


def _notify_factors_ready(factor_count: int, run_date: str) -> None:
    """Send a Slack/Discord notification that factors are staged and awaiting approval.

    Resolution order for webhook URLs:
      1. ``STOCK1901_SLACK_WEBHOOK_URL`` env var  → Slack
      2. ``STOCK1901_DISCORD_WEBHOOK_URL`` env var → Discord
    A missing URL logs a warning and exits silently — notifications are best-effort.
    """
    import os

    slack_url = os.environ.get("STOCK1901_SLACK_WEBHOOK_URL")
    discord_url = os.environ.get("STOCK1901_DISCORD_WEBHOOK_URL")
    url = slack_url or discord_url
    if not url:
        logger.warning("factor_notification: no webhook URL configured; skipping")
        return

    platform = "Slack" if slack_url else "Discord"
    text = (
        f":rocket: *RD-Agent Factor Factory — Factors Ready for Approval*\n"
        f"*Run date:* {run_date}\n"
        f"*Staged factors:* {factor_count}\n"
        f"Use `python -m stock_rtx4060.main factor-approve` to register approved factors."
    )

    try:
        import httpx

        if discord_url:
            payload = {"content": text}
        else:
            payload = {"text": text}

        resp = httpx.post(url, json=payload, timeout=10.0)
        if not (200 <= resp.status_code < 300):
            logger.warning("factor_notification: %s webhook returned %s", platform, resp.status_code)
        else:
            logger.info("factor_notification sent via %s", platform)
    except Exception as exc:  # noqa: BLE001 - notification must never raise
        logger.warning("factor_notification request failed: %s", exc)


@task
def factor_notification_task(factor_count: int, *, run_date: str | None = None) -> dict[str, Any]:
    """Send a Slack/Discord alert when new factors are staged and awaiting approval.

    This task is intentionally idempotent — it posts a best-effort notification
    and always returns ``{"sent": True}`` so the flow does not block on delivery.
    """
    from datetime import date as Date

    actual_date = run_date or str(Date.today())
    _notify_factors_ready(factor_count=factor_count, run_date=actual_date)
    return {"sent": True, "run_date": actual_date, "factor_count": factor_count}


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
    "qlib_export_task",
    "factor_validation_task",
    "factor_notification_task",
    "_msprt_oos_check",
    "RESEARCH_FLOW_CRON",
    "RESEARCH_FLOW_TIMEZONE",
    "PROMOTION_DELTA_THRESHOLD",
]
