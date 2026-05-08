"""Append-only audit log for advisor calls.

Layout: ``<output_dir>/audit_log/advisor.jsonl``.  Every line is a JSON
record with the full payload (rationale, citations, prompt hash, token
counts, cost) plus an ISO-8601 timestamp.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .base import AdvisoryOutput

DEFAULT_PATH = Path("audit_log") / "advisor.jsonl"


def log_advisor_call(output: AdvisoryOutput, *, path: Path | None = None) -> Path:
    """Append ``output`` to the advisor audit log.  Returns the file path."""
    target = Path(path) if path is not None else DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    record = asdict(output)
    record["timestamp_utc"] = datetime.now(UTC).isoformat(timespec="seconds")
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return target


def check_completeness(
    advisory_scores: Iterable[tuple[str, float]],
    audit_path: Path | None = None,
) -> tuple[bool, list[str]]:
    """Verify every nonzero ``advisory_score`` has an audit entry today.

    Parameters
    ----------
    advisory_scores
        Iterable of ``(ticker, score)`` tuples — the in-memory blend
        produced by the orchestrator.
    audit_path
        Path to the audit log JSONL file.  Defaults to the module-level
        :data:`DEFAULT_PATH`.

    Returns
    -------
    ``(ok, missing)`` — ``ok`` is ``True`` when every nonzero score has a
    corresponding audit line dated today; ``missing`` is the list of
    tickers without coverage.
    """
    target = Path(audit_path) if audit_path is not None else DEFAULT_PATH
    today = datetime.now(UTC).date().isoformat()
    coverage: set[str] = set()
    if target.exists():
        with target.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = str(record.get("timestamp_utc", ""))
                if not ts.startswith(today):
                    continue
                ticker = record.get("ticker")
                if ticker:
                    coverage.add(str(ticker))

    missing: list[str] = []
    for ticker, score in advisory_scores:
        if abs(float(score)) < 1e-9:
            continue
        if str(ticker) not in coverage:
            missing.append(str(ticker))
    return (len(missing) == 0, missing)


__all__ = ["log_advisor_call", "check_completeness", "DEFAULT_PATH"]
