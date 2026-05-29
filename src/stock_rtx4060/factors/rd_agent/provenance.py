"""Provenance / audit-logging helpers for the RD-Agent workflow.

All events are appended to ``audit_log/rd_agent.jsonl`` (created if it does
not already exist).  The log format is a newline-delimited JSON (JSONL).

Schema E1 — RDAgentAuditEvent
-----------------------------
ts              (str)  ISO-8601 timestamp with timezone, e.g. "2026-05-29T14:30:00.000Z"
session_id      (str)  RD-Agent session identifier
event           (str)  Event name: cycle_complete | factor_validated | factor_approved | budget_exceeded
cycles_run      (int)  Number of RD-Agent cycles completed
budget_spent_usd (float) Cumulative USD cost incurred so far
budget_limit_usd (float) Per-session USD budget cap
new_factor_files (list[str]) Paths of newly discovered/created factor files this cycle
validated_pass  (int)  Count of factors passing validation this cycle
validated_fail  (int)  Count of factors failing validation this cycle
approved_by     (str)  Approver identifier (e.g. "operator" or "auto"); empty string if none
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

# Audit log root — sibling to the existing audit_log/ directory
_AUDIT_ROOT = Path(__file__).parent.parent.parent.parent.parent / "audit_log"
_LOG_PATH = _AUDIT_ROOT / "rd_agent.jsonl"


@dataclass
class RDAgentAuditEvent:
    """E1 audit event schema for RD-Agent provenance tracking."""

    ts: str
    session_id: str
    event: Literal["cycle_complete", "factor_validated", "factor_approved", "budget_exceeded"]
    cycles_run: int
    budget_spent_usd: float
    budget_limit_usd: float
    new_factor_files: list[str] = field(default_factory=list)
    validated_pass: int = 0
    validated_fail: int = 0
    approved_by: str = ""


def _timestamp() -> str:
    """Return an ISO-8601 timestamp in UTC."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_log_dir() -> None:
    """Create the audit log directory if it does not exist."""
    _AUDIT_ROOT.mkdir(parents=True, exist_ok=True)


def _append(event: RDAgentAuditEvent) -> None:
    """Append a serialised JSON event to the audit log file."""
    _ensure_log_dir()
    line = json.dumps(asdict(event), ensure_ascii=False)
    with open(_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def log_cycle_complete(
    session_id: str,
    cycles_run: int,
    budget_spent_usd: float,
    budget_limit_usd: float,
    new_factor_files: list[str],
    validated_pass: int,
    validated_fail: int,
    approved_by: str = "",
) -> None:
    """Record completion of an RD-Agent exploration cycle."""
    _append(
        RDAgentAuditEvent(
            ts=_timestamp(),
            session_id=session_id,
            event="cycle_complete",
            cycles_run=cycles_run,
            budget_spent_usd=budget_spent_usd,
            budget_limit_usd=budget_limit_usd,
            new_factor_files=new_factor_files,
            validated_pass=validated_pass,
            validated_fail=validated_fail,
            approved_by=approved_by,
        )
    )


def log_factor_validated(
    session_id: str,
    cycles_run: int,
    budget_spent_usd: float,
    budget_limit_usd: float,
    new_factor_files: list[str],
    validated_pass: int,
    validated_fail: int,
    approved_by: str = "",
) -> None:
    """Record a factor validation outcome within the current cycle."""
    _append(
        RDAgentAuditEvent(
            ts=_timestamp(),
            session_id=session_id,
            event="factor_validated",
            cycles_run=cycles_run,
            budget_spent_usd=budget_spent_usd,
            budget_limit_usd=budget_limit_usd,
            new_factor_files=new_factor_files,
            validated_pass=validated_pass,
            validated_fail=validated_fail,
            approved_by=approved_by,
        )
    )


def log_factor_approved(
    session_id: str,
    cycles_run: int,
    budget_spent_usd: float,
    budget_limit_usd: float,
    new_factor_files: list[str],
    approved_by: str = "operator",
) -> None:
    """Record operator approval of one or more discovered factors."""
    _append(
        RDAgentAuditEvent(
            ts=_timestamp(),
            session_id=session_id,
            event="factor_approved",
            cycles_run=cycles_run,
            budget_spent_usd=budget_spent_usd,
            budget_limit_usd=budget_limit_usd,
            new_factor_files=new_factor_files,
            validated_pass=0,
            validated_fail=0,
            approved_by=approved_by,
        )
    )


def log_budget_exceeded(
    session_id: str,
    cycles_run: int,
    budget_spent_usd: float,
    budget_limit_usd: float,
    new_factor_files: list[str],
    validated_pass: int,
    validated_fail: int,
    approved_by: str = "",
) -> None:
    """Record that the per-session budget limit was reached."""
    _append(
        RDAgentAuditEvent(
            ts=_timestamp(),
            session_id=session_id,
            event="budget_exceeded",
            cycles_run=cycles_run,
            budget_spent_usd=budget_spent_usd,
            budget_limit_usd=budget_limit_usd,
            new_factor_files=new_factor_files,
            validated_pass=validated_pass,
            validated_fail=validated_fail,
            approved_by=approved_by,
        )
    )
