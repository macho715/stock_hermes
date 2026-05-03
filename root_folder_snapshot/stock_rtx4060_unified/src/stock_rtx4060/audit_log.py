"""Structured audit logging for report-only stock workflows."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

AuditStatus = Literal["SUCCESS", "FAIL", "FALLBACK", "SKIPPED"]

SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "passwd",
    "authorization",
    "bearer",
    "account",
    "credential",
    "private_url",
)

SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization|bearer)=([^&\s]+)"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{8,}"),
)


@dataclass
class AuditEvent:
    """Single JSONL audit event."""

    event_type: str
    status: AuditStatus
    command: str
    ticker: str | None = None
    period: str | None = None
    provider_requested: str | None = None
    provider_used: str | None = None
    endpoint: str | None = None
    source: str | None = None
    message: str | None = None
    error_type: str | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def to_dict(self) -> dict[str, Any]:
        return mask_secret(asdict(self))


class AuditLogger:
    """Append-only JSONL writer with secret masking."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def for_output_dir(cls, output_dir: str | Path, filename: str = "audit_log.jsonl") -> "AuditLogger":
        return cls(Path(output_dir) / filename)

    def write(self, event: AuditEvent) -> Path:
        line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return self.path


def mask_secret(value: Any, key_hint: str | None = None) -> Any:
    """Return a copy of value with obvious credentials masked."""

    if _is_sensitive_key(key_hint):
        return "<masked>"
    if isinstance(value, dict):
        return {str(key): mask_secret(item, str(key)) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_secret(item, key_hint) for item in value]
    if isinstance(value, tuple):
        return [mask_secret(item, key_hint) for item in value]
    if isinstance(value, str):
        masked = value
        for pattern in SENSITIVE_VALUE_PATTERNS:
            masked = pattern.sub(_mask_match, masked)
        return masked
    return value


def _is_sensitive_key(key_hint: str | None) -> bool:
    if not key_hint:
        return False
    normalized = key_hint.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _mask_match(match: re.Match[str]) -> str:
    text = match.group(0)
    if "=" in text:
        prefix = text.split("=", 1)[0]
        return f"{prefix}=<masked>"
    if text.lower().startswith("bearer "):
        return "Bearer <masked>"
    return "<masked>"
