"""Validation gates for recommendation candidates."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class GateResult(str, Enum):
    PASS = "PASS"
    AMBER = "AMBER"
    RED = "RED"
    ZERO = "ZERO"


@dataclass(frozen=True)
class GateEvidence:
    gate: str
    result: GateResult
    evidence: dict[str, Any]


def g01_data_freshness(provider_metadata: dict[str, Any] | None) -> GateEvidence:
    """G-01: DATA_FRESHNESS — check staleness by market."""
    if not provider_metadata:
        return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.RED, evidence={"error": "no metadata"})

    ticker_type = provider_metadata.get("ticker_type", "UNKNOWN")
    freshness_minutes = provider_metadata.get("data_freshness_minutes", -1)
    market = ticker_type.upper()

    # KRX: 1 business day = ~1440 minutes (allowing for weekend gap)
    if market == "KRX":
        if freshness_minutes <= 1440:
            return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.PASS, evidence={"market": market, "stale_days": 0})
        if freshness_minutes <= 4320:  # 3 days
            return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.AMBER, evidence={"market": market, "stale_days": freshness_minutes / 1440})
        return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.RED, evidence={"market": market, "stale_days": freshness_minutes / 1440, "reason": "KRX >3 business days stale"})

    # NYSE/NASDAQ: 1 calendar day = 1440 minutes
    if market in ("NYSE", "NASDAQ"):
        if freshness_minutes <= 1440:
            return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.PASS, evidence={"market": market})
        return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.RED, evidence={"market": market, "stale_days": freshness_minutes / 1440})

    return GateEvidence(gate="G-01_DATA_FRESHNESS", result=GateResult.RED, evidence={"market": market, "reason": "unknown market"})


def g02_price_crosscheck(price_a: float | None, price_b: float | None) -> GateEvidence:
    """G-02: PRICE_CROSSCHECK — dual-source delta check."""
    if price_a is None or price_b is None:
        return GateEvidence(gate="G-02_PRICE_CROSSCHECK", result=GateResult.AMBER, evidence={"error": "single source only"})
    if price_a <= 0 or price_b <= 0:
        return GateEvidence(gate="G-02_PRICE_CROSSCHECK", result=GateResult.RED, evidence={"error": "invalid price"})

    delta_pct = abs(price_a - price_b) / ((price_a + price_b) / 2) * 100
    if delta_pct <= 1.0:
        result = GateResult.PASS
    elif delta_pct <= 3.0:
        result = GateResult.AMBER
    else:
        result = GateResult.RED

    return GateEvidence(
        gate="G-02_PRICE_CROSSCHECK",
        result=result,
        evidence={"price_a": price_a, "price_b": price_b, "delta_pct": round(delta_pct, 4), "crosscheck_passed": result == GateResult.PASS},
    )


def g03_schema_completeness(frame_rows: int, columns: list[str], volume_all_zero: bool = False, close_invalid: bool = False) -> GateEvidence:
    """G-03: SCHEMA_COMPLETENESS — required columns, row count, volume check."""
    required_cols = {"date", "open", "high", "low", "close", "volume"}
    col_lower = {c.lower().strip() for c in columns}
    missing = required_cols - col_lower

    if missing:
        return GateEvidence(gate="G-03_SCHEMA_COMPLETENESS", result=GateResult.RED, evidence={"missing_columns": list(missing)})
    if frame_rows < 30:
        return GateEvidence(gate="G-03_SCHEMA_COMPLETENESS", result=GateResult.RED, evidence={"row_count": frame_rows, "reason": "insufficient history"})
    if volume_all_zero:
        return GateEvidence(gate="G-03_SCHEMA_COMPLETENESS", result=GateResult.RED, evidence={"volume_all_zero": True})
    if close_invalid:
        return GateEvidence(gate="G-03_SCHEMA_COMPLETENESS", result=GateResult.RED, evidence={"close_invalid": True})

    return GateEvidence(gate="G-03_SCHEMA_COMPLETENESS", result=GateResult.PASS, evidence={"row_count": frame_rows, "column_check": "all present"})


def g04_corp_action_sanity(close_prices: list[float], drop_threshold_pct: float = 20.0) -> GateEvidence:
    """G-04: CORP_ACTION_SANITY — detect sudden price drops >20%."""
    if len(close_prices) < 2:
        return GateEvidence(gate="G-04_CORP_ACTION_SANITY", result=GateResult.PASS, evidence={"reason": "insufficient data"})

    max_drop = 0.0
    for i in range(1, len(close_prices)):
        if close_prices[i - 1] <= 0:
            continue
        drop_pct = (close_prices[i - 1] - close_prices[i]) / close_prices[i - 1] * 100
        max_drop = max(max_drop, drop_pct)

    if max_drop < 10.0:
        return GateEvidence(gate="G-04_CORP_ACTION_SANITY", result=GateResult.PASS, evidence={"corp_action_detected": False})
    if max_drop < drop_threshold_pct:
        return GateEvidence(gate="G-04_CORP_ACTION_SANITY", result=GateResult.AMBER, evidence={"corp_action_detected": True, "drop_pct": round(max_drop, 2), "action_type": "suspected_corp_action"})
    return GateEvidence(gate="G-04_CORP_ACTION_SANITY", result=GateResult.AMBER, evidence={"corp_action_detected": True, "drop_pct": round(max_drop, 2), "action_type": "unexplained_drop"})


def g05_model_health(auc: float | None, accuracy: float | None) -> GateEvidence:
    """G-05: MODEL_HEALTH — AUC >= 0.55, Accuracy >= 0.50."""
    if auc is None or accuracy is None:
        return GateEvidence(gate="G-05_MODEL_HEALTH", result=GateResult.RED, evidence={"error": "model failed to train"})

    if auc >= 0.55 and accuracy >= 0.50:
        return GateEvidence(gate="G-05_MODEL_HEALTH", result=GateResult.PASS, evidence={"auc": auc, "accuracy": accuracy})
    if auc >= 0.50:
        return GateEvidence(gate="G-05_MODEL_HEALTH", result=GateResult.AMBER, evidence={"auc": auc, "accuracy": accuracy, "reason": "AUC marginal"})
    return GateEvidence(gate="G-05_MODEL_HEALTH", result=GateResult.RED, evidence={"auc": auc, "accuracy": accuracy, "reason": "below thresholds"})


def g06_oof_coverage(coverage_pct: float | None) -> GateEvidence:
    """G-06: OOF_COVERAGE — coverage >= 70%."""
    if coverage_pct is None:
        return GateEvidence(gate="G-06_OOF_COVERAGE", result=GateResult.RED, evidence={"error": "no coverage data"})

    if coverage_pct >= 70:
        return GateEvidence(gate="G-06_OOF_COVERAGE", result=GateResult.PASS, evidence={"oof_coverage_pct": coverage_pct})
    if coverage_pct >= 50:
        return GateEvidence(gate="G-06_OOF_COVERAGE", result=GateResult.AMBER, evidence={"oof_coverage_pct": coverage_pct})
    return GateEvidence(gate="G-06_OOF_COVERAGE", result=GateResult.RED, evidence={"oof_coverage_pct": coverage_pct, "reason": "below 50%"})


def g07_risk_plan(stop_pct: float | None, tp2_pct: float | None, risk_budget_pct: float | None, risk_reward: float | None, track: str = "S") -> GateEvidence:
    """G-07: RISK_PLAN — valid stop/target, R/R meets track threshold."""
    if stop_pct is None or tp2_pct is None or risk_budget_pct is None or risk_reward is None:
        return GateEvidence(gate="G-07_RISK_PLAN", result=GateResult.RED, evidence={"error": "missing risk plan fields"})
    if stop_pct >= 0 or tp2_pct <= stop_pct:
        return GateEvidence(gate="G-07_RISK_PLAN", result=GateResult.RED, evidence={"stop_pct": stop_pct, "tp2_pct": tp2_pct, "reason": "invalid plan"})

    threshold = 2.0 if track.upper() == "S" else 1.5
    if risk_reward >= threshold:
        return GateEvidence(gate="G-07_RISK_PLAN", result=GateResult.PASS, evidence={"stop_pct": stop_pct, "tp2_pct": tp2_pct, "risk_reward": risk_reward, "risk_budget_pct": risk_budget_pct})
    if risk_reward >= 1.5:
        return GateEvidence(gate="G-07_RISK_PLAN", result=GateResult.AMBER, evidence={"stop_pct": stop_pct, "tp2_pct": tp2_pct, "risk_reward": risk_reward, "reason": "marginal R/R"})
    return GateEvidence(gate="G-07_RISK_PLAN", result=GateResult.AMBER, evidence={"stop_pct": stop_pct, "tp2_pct": tp2_pct, "risk_reward": risk_reward, "reason": "below 1.5"})


def g08_backtest_sanity(sharpe: float | None, mdd_pct: float | None, return_pct: float | None = None) -> GateEvidence:
    """G-08: BACKTEST_SANITY — Sharpe >= 0, MDD < 20%."""
    if sharpe is None or mdd_pct is None:
        return GateEvidence(gate="G-08_BACKTEST_SANITY", result=GateResult.AMBER, evidence={"error": "no backtest data"})

    if mdd_pct >= 20:
        return GateEvidence(gate="G-08_BACKTEST_SANITY", result=GateResult.RED, evidence={"sharpe": sharpe, "mdd_pct": mdd_pct, "reason": "MDD >= 20%"})
    if sharpe >= 0:
        return GateEvidence(gate="G-08_BACKTEST_SANITY", result=GateResult.PASS, evidence={"sharpe": sharpe, "mdd_pct": mdd_pct, "return_pct": return_pct})
    if sharpe >= -0.5:
        return GateEvidence(gate="G-08_BACKTEST_SANITY", result=GateResult.AMBER, evidence={"sharpe": sharpe, "mdd_pct": mdd_pct, "return_pct": return_pct})
    return GateEvidence(gate="G-08_BACKTEST_SANITY", result=GateResult.AMBER, evidence={"sharpe": sharpe, "mdd_pct": mdd_pct, "reason": "negative trend"})


def g09_approval(all_gates_pass: bool, any_red: bool, amber_cleared: bool, has_amber: bool) -> GateEvidence:
    """G-09: APPROVAL — state machine result."""
    if any_red:
        return GateEvidence(gate="G-09_APPROVAL", result=GateResult.RED, evidence={"approval_status": "BLOCKED", "reason": "RED gate present"})
    if all_gates_pass:
        return GateEvidence(gate="G-09_APPROVAL", result=GateResult.PASS, evidence={"approval_status": "APPROVED"})
    if has_amber and not amber_cleared:
        return GateEvidence(gate="G-09_APPROVAL", result=GateResult.AMBER, evidence={"approval_status": "PENDING_REVIEW", "reason": "AMBER not cleared"})
    if amber_cleared:
        return GateEvidence(gate="G-09_APPROVAL", result=GateResult.PASS, evidence={"approval_status": "APPROVED_WITH_AMBER", "cleared_flags": True})
    return GateEvidence(gate="G-09_APPROVAL", result=GateResult.AMBER, evidence={"approval_status": "PENDING_REVIEW"})


def g10_audit_evidence(audit_event_count: int, has_provider_event: bool, has_recommend_event: bool) -> GateEvidence:
    """G-10: AUDIT_EVIDENCE — trace completeness check."""
    if has_provider_event and has_recommend_event:
        return GateEvidence(gate="G-10_AUDIT_EVIDENCE", result=GateResult.PASS, evidence={"audit_event_count": audit_event_count, "provider_event_present": True, "recommend_event_present": True})
    if not has_provider_event:
        return GateEvidence(gate="G-10_AUDIT_EVIDENCE", result=GateResult.RED, evidence={"audit_event_count": audit_event_count, "reason": "provider_attempt event missing"})
    return GateEvidence(gate="G-10_AUDIT_EVIDENCE", result=GateResult.RED, evidence={"audit_event_count": audit_event_count, "reason": "recommend event missing"})