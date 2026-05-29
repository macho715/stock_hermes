"""forward_review_pack.py — generates 30-day forward paper trading review pack.

The review pack is a Markdown report summarising the forward paper trading
evidence for manual user review.

Safety contract (immutable — must appear in every generated report):
  "This is a paper-trading evidence report only."
  "No broker order was executed."
  "No new capital is allowed by the system."
  "User review is required before any real investment decision."
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


_DISCLAIMER = """\
---
**REPORT-ONLY DISCLAIMER**

This is a paper-trading evidence report only.
No broker order was executed.
No new capital is allowed by the system.
User review is required before any real investment decision.
---"""


def evaluate_forward_summary(summary: dict[str, Any]) -> str:
    """Return ``"PASS"`` or ``"FAIL"`` based on forward summary gates.

    Gates (all must pass for PASS):
    - ``days >= target_days``  (default 30 when target_days missing)
    - ``forward_paper_alpha_pct >= 0.00``
    - ``rule_violation_count == 0``
    - ``critical_data_missing_count == 0``
    - ``max_forward_drawdown_pct <= forward_mdd_limit`` (default 20.0)
    """
    days = int(summary.get("days", 0))
    target = int(summary.get("target_days", summary.get("stop_after_days", 30)))
    alpha = float(summary.get("forward_paper_alpha_pct", 0.0) or 0.0)
    violations = int(summary.get("rule_violation_count", 0))
    missing = int(summary.get("critical_data_missing_count", 0))
    mdd = float(summary.get("max_forward_drawdown_pct", 0.0) or 0.0)
    mdd_limit = float(summary.get("forward_mdd_limit", 20.0))

    if days < target:
        return "FAIL"
    if alpha < 0.0:
        return "FAIL"
    if violations > 0:
        return "FAIL"
    if missing > 0:
        return "FAIL"
    if mdd > mdd_limit:
        return "FAIL"
    return "PASS"


def write_review_pack(summary: dict[str, Any], *, output_path: str) -> str:
    """Write a Markdown review pack and return its path.

    The report always includes the mandatory report-only disclaimer and
    the ``FORWARD_COMPLETE_USER_REVIEW_REQUIRED`` status line.
    """
    status = evaluate_forward_summary(summary)
    symbol = summary.get("symbol", "UNKNOWN")
    days = summary.get("days", 0)
    alpha = summary.get("forward_paper_alpha_pct", 0.0)
    violations = summary.get("rule_violation_count", 0)
    missing = summary.get("critical_data_missing_count", 0)
    mdd = summary.get("max_forward_drawdown_pct", 0.0)
    start = summary.get("start_date", "—")
    end = summary.get("end_date", "—")
    bench = summary.get("benchmark_symbol", "—")
    generated = datetime.now(UTC).isoformat(timespec="seconds")

    lines = [
        f"# Forward Paper Trading Review Pack — {symbol}",
        "",
        _DISCLAIMER,
        "",
        f"**Generated:** {generated}  ",
        f"**Final Status:** `FORWARD_COMPLETE_USER_REVIEW_REQUIRED`  ",
        f"**Forward Pass:** `{status}`",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Symbol | {symbol} |",
        f"| Benchmark | {bench} |",
        f"| Trading days recorded | {days} |",
        f"| Period | {start} → {end} |",
        f"| Cumulative alpha vs benchmark | {alpha:+.4f}% |",
        f"| Rule violations | {violations} |",
        f"| Critical data missing | {missing} |",
        f"| Max forward drawdown | {mdd:.4f}% |",
        f"| Forward pass status | **{status}** |",
        "",
        "---",
        "",
        "## Daily Log Coverage",
        "",
        f"Recorded {days} trading days from {start} to {end}.",
        "",
        "---",
        "",
        "## Alpha vs Benchmark",
        "",
        f"Cumulative alpha: **{alpha:+.4f}%** vs {bench}.",
        "",
        "---",
        "",
        "## Rule Violations",
        "",
        f"Total violations: **{violations}** (0 = PASS).",
        "",
        "---",
        "",
        "## Drawdown",
        "",
        f"Maximum forward drawdown: **{mdd:.4f}%**.",
        "",
        "---",
        "",
        "## Data Quality",
        "",
        f"Critical data missing days: **{missing}** (0 = PASS).",
        "",
        "---",
        "",
        "## Final Status",
        "",
        "```",
        "FORWARD_COMPLETE_USER_REVIEW_REQUIRED",
        "```",
        "",
        "## User Decision Required",
        "",
        "Please review the evidence above and choose one of:",
        "",
        "- [ ] Proceed with LIVE_REVIEW_CANDIDATE assessment (manual approval required)",
        "- [ ] Extend observation (continue paper trading)",
        "- [ ] System upgrade or re-training required",
        "",
        _DISCLAIMER,
        "",
    ]

    content = "\n".join(lines)
    import pathlib
    pathlib.Path(output_path).write_text(content, encoding="utf-8")
    return output_path
