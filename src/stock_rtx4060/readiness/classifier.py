"""LIVE_REVIEW_CANDIDATE gate logic.

This module is report-only.  It never approves live orders; it only decides
whether a candidate has enough evidence to be placed in a manual live-review
queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any

LIVE_REVIEW_RULES = {
    "min_cpcv_pass_rate": 0.60,
    "max_pbo": 0.20,
    "min_deflated_sharpe": 0.0,
    "min_forward_paper_days": 30,
    "min_forward_paper_alpha": 0.0,
    "max_rule_violations": 0,
}


@dataclass(frozen=True)
class LiveReviewDecision:
    ticker: str
    status: str
    live_review_candidate: bool
    paper_pass: bool
    blocking_reasons: list[str]
    passed_gates: list[str]
    failed_gates: list[str]
    safety_flags: dict[str, bool]
    readiness_status: str = ""
    remaining_blocks: list[str] = field(default_factory=list)
    new_capital_allowed: bool = False
    broker_order_execution: bool = False
    manual_approval_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "status": self.status,
            "readiness_status": self.readiness_status or self.status,
            "live_review_candidate": self.live_review_candidate,
            "paper_pass": self.paper_pass,
            "blocking_reasons": self.blocking_reasons,
            "remaining_blocks": self.remaining_blocks,
            "passed_gates": self.passed_gates,
            "failed_gates": self.failed_gates,
            "safety_flags": self.safety_flags,
            "new_capital_allowed": self.new_capital_allowed,
            "broker_order_execution": self.broker_order_execution,
            "manual_approval_required": self.manual_approval_required,
        }


def classify_live_review(
    *,
    ticker: str,
    cpcv_pass_rate: float | None,
    pbo: float | None,
    deflated_sharpe: float | None,
    forward_paper_days: int | None,
    forward_paper_alpha: float | None,
    rule_violations: int | None,
    model_card_present: bool,
    dashboard_safety_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a ticker for manual live-review eligibility.

    Required gates:
    - CPCV pass rate >= 60%
    - PBO <= 0.20
    - Deflated Sharpe > 0
    - forward paper days >= 30
    - forward paper alpha >= 0
    - zero rule violations
    - model card present
    - dashboard/report-only safety flags preserved
    """

    passed: list[str] = []
    failed: list[str] = []
    reasons: list[str] = []

    _check_floor("CPCV_PATH_RATE", cpcv_pass_rate, LIVE_REVIEW_RULES["min_cpcv_pass_rate"], passed, failed, reasons)
    _check_ceiling("PBO", pbo, LIVE_REVIEW_RULES["max_pbo"], passed, failed, reasons)
    _check_floor_strict(
        "DEFLATED_SHARPE",
        deflated_sharpe,
        LIVE_REVIEW_RULES["min_deflated_sharpe"],
        passed,
        failed,
        reasons,
    )
    _check_floor(
        "FORWARD_PAPER_DAYS",
        forward_paper_days,
        LIVE_REVIEW_RULES["min_forward_paper_days"],
        passed,
        failed,
        reasons,
    )
    _check_floor(
        "FORWARD_PAPER_ALPHA",
        forward_paper_alpha,
        LIVE_REVIEW_RULES["min_forward_paper_alpha"],
        passed,
        failed,
        reasons,
    )
    _check_ceiling(
        "RULE_VIOLATIONS",
        rule_violations,
        LIVE_REVIEW_RULES["max_rule_violations"],
        passed,
        failed,
        reasons,
    )

    if model_card_present:
        passed.append("MODEL_CARD_PRESENT")
    else:
        failed.append("MODEL_CARD_PRESENT")
        reasons.append("model card missing")

    safety = _normalize_safety_flags(dashboard_safety_flags)
    if all(safety.values()):
        passed.append("DASHBOARD_SAFETY_FLAGS")
    else:
        failed.append("DASHBOARD_SAFETY_FLAGS")
        missing = [name for name, ok in safety.items() if not ok]
        reasons.append(f"dashboard safety flags failed: {', '.join(missing)}")

    diagnostic_gates = {"CPCV_PATH_RATE", "PBO", "DEFLATED_SHARPE", "MODEL_CARD_PRESENT", "DASHBOARD_SAFETY_FLAGS"}
    paper_pass = diagnostic_gates.issubset(set(passed))
    live = not failed
    if live:
        status = "LIVE_REVIEW_CANDIDATE"
        readiness_status = "LIVE_REVIEW_CANDIDATE"
    elif paper_pass:
        status = "PAPER_PASS"
        readiness_status = "FORWARD_PAPER_RUNNING" if _has_forward_gate_failure(failed) else "PAPER_PASS"
    else:
        status = "AMBER_WATCHLIST"
        readiness_status = "AMBER_WATCHLIST"

    return LiveReviewDecision(
        ticker=ticker,
        status=status,
        live_review_candidate=live,
        paper_pass=paper_pass,
        blocking_reasons=reasons,
        passed_gates=passed,
        failed_gates=failed,
        safety_flags=safety,
        readiness_status=readiness_status,
        remaining_blocks=list(failed),
        new_capital_allowed=False,
        broker_order_execution=False,
        manual_approval_required=True,
    ).to_dict()


def _valid_number(value: float | int | None) -> bool:
    if value is None:
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return isfinite(numeric)


def _check_floor(
    name: str,
    value: float | int | None,
    threshold: float,
    passed: list[str],
    failed: list[str],
    reasons: list[str],
) -> None:
    if _valid_number(value) and float(value) >= threshold:
        passed.append(name)
        return
    failed.append(name)
    reasons.append(f"{name} {value!r} < {threshold}")


def _check_floor_strict(
    name: str,
    value: float | int | None,
    threshold: float,
    passed: list[str],
    failed: list[str],
    reasons: list[str],
) -> None:
    if _valid_number(value) and float(value) > threshold:
        passed.append(name)
        return
    failed.append(name)
    reasons.append(f"{name} {value!r} <= {threshold}")


def _check_ceiling(
    name: str,
    value: float | int | None,
    threshold: float,
    passed: list[str],
    failed: list[str],
    reasons: list[str],
) -> None:
    if _valid_number(value) and float(value) <= threshold:
        passed.append(name)
        return
    failed.append(name)
    reasons.append(f"{name} {value!r} > {threshold}")


def _normalize_safety_flags(flags: dict[str, Any] | None) -> dict[str, bool]:
    data = flags or {}
    return {
        "screening_output_only": data.get("screening_output_only") is True,
        "manual_approval_required": data.get("manual_approval_required") is True,
        "broker_order_execution_false": data.get("broker_order_execution") is False,
        "new_capital_allowed_false": data.get("new_capital_allowed") is False,
    }


def _has_forward_gate_failure(failed: list[str]) -> bool:
    return any(name in failed for name in ("FORWARD_PAPER_DAYS", "FORWARD_PAPER_ALPHA", "RULE_VIOLATIONS"))
