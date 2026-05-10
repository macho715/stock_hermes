"""Provenance audit log for every PIT read/write. Append-only JSONL."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_PROVENANCE_PATH = Path(os.environ.get("PIT_PROVENANCE_LOG", "audit_log/provenance.jsonl"))


def _ts() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _append(payload: dict[str, Any], *, path: Path | None = None) -> None:
    target = path or DEFAULT_PROVENANCE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")


def log_pit_read(*, ticker: str, as_of: Any, rows: int, backend: str, path: Path | None = None) -> None:
    _append(
        {
            "event": "pit_read",
            "ticker": ticker,
            "as_of": str(as_of) if as_of else None,
            "rows": int(rows),
            "backend": backend,
            "ts": _ts(),
        },
        path=path,
    )


def log_pit_write(*, ticker: str, source: str, rows: int, backend: str, path: Path | None = None) -> None:
    _append(
        {
            "event": "pit_write",
            "ticker": ticker,
            "source": source,
            "rows": int(rows),
            "backend": backend,
            "ts": _ts(),
        },
        path=path,
    )
