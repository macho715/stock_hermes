"""Readiness evidence snapshot builder."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .classifier import classify_live_review


def build_readiness_snapshot(
    *,
    ticker: str,
    cpcv_report: dict[str, Any] | str | Path | None = None,
    pbo_report: dict[str, Any] | str | Path | None = None,
    dsr_report: dict[str, Any] | str | Path | None = None,
    paper_status: dict[str, Any] | str | Path | None = None,
    model_card_path: str | Path | None = None,
    dashboard_safety_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single report-only snapshot for live-review gate evidence."""

    cpcv = _load_mapping(cpcv_report)
    pbo = _load_mapping(pbo_report)
    dsr = _load_mapping(dsr_report)
    paper = _load_mapping(paper_status)
    equity_curve = paper.get("equity_curve") if isinstance(paper.get("equity_curve"), list) else []
    paper_days = _first_present(paper, "forward_paper_days", "days")
    if paper_days is None:
        paper_days = len(equity_curve)
    paper_alpha = _first_present(paper, "forward_paper_alpha", "alpha_pct")
    if paper_alpha is None:
        paper_alpha = _paper_alpha_from_equity(equity_curve)
    rule_violations = _first_present(paper, "rule_violations", "rule_violation_count")
    if rule_violations is None:
        details = paper.get("rule_violations_detail")
        rule_violations = len(details) if isinstance(details, list) else None

    model_card_exists = bool(model_card_path and Path(model_card_path).exists())
    decision = classify_live_review(
        ticker=ticker,
        cpcv_pass_rate=_first_number(cpcv, "pass_rate", "path_pass_rate"),
        pbo=_first_number(pbo, "pbo", "probability_of_backtest_overfitting"),
        deflated_sharpe=_first_number(dsr, "deflated_sharpe", "dsr"),
        forward_paper_days=_to_int(paper_days),
        forward_paper_alpha=_to_float(paper_alpha),
        rule_violations=_to_int(rule_violations),
        model_card_present=model_card_exists,
        dashboard_safety_flags=dashboard_safety_flags,
    )
    return {
        "schema_version": "live_review_snapshot.v1",
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "ticker": ticker,
        "decision": decision,
        "evidence": {
            "cpcv": cpcv,
            "pbo": pbo,
            "dsr": dsr,
            "paper": {
                "forward_paper_days": _to_int(paper_days),
                "forward_paper_alpha": _to_float(paper_alpha),
                "rule_violations": _to_int(rule_violations),
            },
            "model_card_path": str(model_card_path) if model_card_path else None,
            "model_card_present": model_card_exists,
            "dashboard_safety_flags": dashboard_safety_flags or {},
        },
        "report_only": True,
        "broker_order_execution": False,
        "manual_approval_required": True,
        "new_capital_allowed": False,
    }


def write_readiness_snapshot(path: str | Path, **kwargs: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_readiness_snapshot(**kwargs)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _load_mapping(value: dict[str, Any] | str | Path | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        payload = json.loads(Path(value).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_number(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = _to_float(data.get(key))
        if value is not None:
            return value
    return None


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data.get(key) is not None:
            return data.get(key)
    return None


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paper_alpha_from_equity(rows: list[Any]) -> float | None:
    if len(rows) < 2:
        return None
    try:
        first = float(rows[0]["equity"])
        last = float(rows[-1]["equity"])
    except (KeyError, TypeError, ValueError):
        return None
    if first <= 0:
        return None
    return (last / first - 1.0) * 100.0
