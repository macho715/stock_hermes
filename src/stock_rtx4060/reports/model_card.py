"""Model card generation for manual live-review evidence."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def build_model_card(
    *,
    ticker: str,
    gate_decision: dict[str, Any],
    cpcv_report: dict[str, Any] | None = None,
    pbo_report: dict[str, Any] | None = None,
    dsr_report: dict[str, Any] | None = None,
) -> str:
    decision = gate_decision or {}
    lines = [
        f"# Model Card - {ticker}",
        "",
        f"Generated UTC: {datetime.now(UTC).isoformat(timespec='seconds')}",
        "",
        "Report-only / Manual review / No broker order execution.",
        "",
        "## Gate Decision",
        "",
        f"- status: {decision.get('status')}",
        f"- live_review_candidate: {decision.get('live_review_candidate') is True}",
        f"- paper_pass: {decision.get('paper_pass') is True}",
        "",
        "## Blocking Reasons",
        "",
    ]
    reasons = decision.get("blocking_reasons") or []
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- CPCV pass rate: {_fmt((cpcv_report or {}).get('pass_rate'))}",
            f"- PBO: {_fmt((pbo_report or {}).get('pbo'))}",
            f"- Deflated Sharpe: {_fmt((dsr_report or {}).get('deflated_sharpe'))}",
            "",
            "## Safety Boundary",
            "",
            "- broker_order_execution: false",
            "- manual_approval_required: true",
            "- screening_output_only: true",
        ]
    )
    return "\n".join(lines) + "\n"


def write_model_card(path: str | Path, **kwargs: Any) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_model_card(**kwargs), encoding="utf-8")
    return output


def _fmt(value: Any) -> str:
    if value is None:
        return "missing"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)
