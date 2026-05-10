"""Journal entry writer for approved recommendations."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_journal_id(ticker: str, track: str, sequence: int, timestamp: datetime | None = None) -> str:
    """Generate journal ID: JRN-{YYYY}-{MMDD}-{TICKER}-{TRACK}-{SEQ}."""
    ts = timestamp or datetime.now(UTC)
    yyyy = ts.strftime("%Y")
    mmdd = ts.strftime("%m%d")
    return f"JRN-{yyyy}-{mmdd}-{ticker}-{track.upper()}-{sequence:03d}"


def write_journal_entry(
    output_dir: str | Path,
    ticker: str,
    track: str,
    verdict: str,
    approval_state: str,
    analyst: str,
    approver: str | None,
    cleared_gates: list[str],
    report_hash: str,
    snapshot_hash: str,
    kevpe_regime: str | None,
    kevpe_score: float | None,
    risk_plan: dict[str, Any],
    position_value: float | None,
    quantity: int | None,
    sequence: int = 1,
) -> Path:
    """Write a journal entry JSON file for an approved recommendation."""
    ts = datetime.now(UTC)
    journal_id = generate_journal_id(ticker, track, sequence, ts)

    entry: dict[str, Any] = {
        "journal_id": journal_id,
        "generated_at_utc": ts.isoformat(timespec="seconds"),
        "ticker": ticker,
        "track": track,
        "verdict": verdict,
        "approval_state": approval_state,
        "analyst": analyst,
        "approver": approver,
        "cleared_gates": cleared_gates,
        "report_hash": report_hash,
        "snapshot_hash": snapshot_hash,
    }

    if kevpe_regime is not None:
        entry["kevpe_regime"] = kevpe_regime
    if kevpe_score is not None:
        entry["kevpe_score"] = kevpe_score

    if risk_plan:
        entry["risk_plan"] = risk_plan
    if position_value is not None:
        entry["position_value"] = position_value
    if quantity is not None:
        entry["quantity"] = quantity

    # Write to journal/YYYY-MM/ directory
    year_month = ts.strftime("%Y-%m")
    dir_path = Path(output_dir) / "journal" / year_month
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{journal_id}.json"
    file_path.write_text(_stable_json(entry), encoding="utf-8")
    return file_path


def compute_file_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    return sha256_hex(Path(file_path).read_bytes().decode("utf-8", errors="replace"))