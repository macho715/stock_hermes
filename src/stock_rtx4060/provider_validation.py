"""Point-in-time validation for normalized OHLCV provider frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import pandas as pd

ProviderValidationStatus = Literal["PASS", "AMBER", "FAIL"]

REQUIRED_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


@dataclass(frozen=True)
class ProviderValidationResult:
    status: ProviderValidationStatus
    evidence: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def validate_provider_frame(
    frame: pd.DataFrame,
    *,
    provider_used: str,
    ticker: str,
    period: str,
    as_of: datetime | pd.Timestamp | None = None,
    min_rows: int = 1,
    freshness_days_warn: int = 5,
    freshness_days_fail: int = 365,
) -> ProviderValidationResult:
    """Validate whether a normalized OHLCV frame is usable for a point-in-time run."""

    run_time = _to_utc_timestamp(as_of)
    run_date = run_time.tz_convert(None).normalize()
    evidence: list[str] = []
    missing = [column for column in REQUIRED_OHLCV_COLUMNS if column not in frame.columns]
    row_count = int(len(frame))
    status: ProviderValidationStatus = "PASS"

    if missing:
        status = "FAIL"
        evidence.append(f"missing_ohlcv_columns={','.join(missing)}")
    if row_count < int(min_rows):
        status = "FAIL"
        evidence.append(f"row_count={row_count}, min_rows={int(min_rows)}")

    date_index = _date_index(frame)
    first_date = _date_string(date_index.min()) if date_index is not None and len(date_index) else None
    last_date = _date_string(date_index.max()) if date_index is not None and len(date_index) else None
    duplicate_dates = int(date_index.duplicated().sum()) if date_index is not None else 0
    future_rows = int((date_index > run_date).sum()) if date_index is not None else 0
    freshness_days: int | None = None

    if date_index is None:
        status = _max_status(status, "AMBER")
        evidence.append("date_index=missing_or_invalid")
    else:
        if duplicate_dates:
            status = "FAIL"
            evidence.append(f"duplicate_dates={duplicate_dates}")
        if future_rows:
            status = "FAIL"
            evidence.append(f"future_rows={future_rows}")
        if last_date:
            freshness_days = max(0, int((run_date - date_index.max()).days))
            if freshness_days >= freshness_days_fail:
                status = "FAIL"
                evidence.append(f"freshness_days={freshness_days}, fail_threshold={freshness_days_fail}")
            elif freshness_days > freshness_days_warn and provider_used != "synthetic":
                status = _max_status(status, "AMBER")
                evidence.append(f"freshness_days={freshness_days}, warn_threshold={freshness_days_warn}")

    null_critical_values = int(frame.loc[:, [c for c in REQUIRED_OHLCV_COLUMNS if c in frame.columns]].isna().sum().sum()) if not frame.empty else 0
    if null_critical_values:
        status = "FAIL"
        evidence.append(f"null_critical_values={null_critical_values}")

    if not evidence:
        evidence.append("provider_frame_validated")

    metadata: dict[str, Any] = {
        "status": status,
        "provider_validation_status": status,
        "ticker": ticker,
        "period": period,
        "provider_used": provider_used,
        "row_count": row_count,
        "first_date": first_date,
        "last_date": last_date,
        "future_rows": future_rows,
        "duplicate_dates": duplicate_dates,
        "missing_ohlcv_columns": missing,
        "null_critical_values": null_critical_values,
        "freshness_days": freshness_days,
        "evidence": evidence,
    }
    return ProviderValidationResult(status=status, evidence=evidence, metadata=metadata)


def _date_index(frame: pd.DataFrame) -> pd.DatetimeIndex | None:
    for column in frame.columns:
        if str(column).lower() in {"date", "datetime", "timestamp"}:
            values = pd.to_datetime(frame[column], errors="coerce")
            values = values[~values.isna()]
            if len(values):
                return pd.DatetimeIndex(values).tz_localize(None).normalize()
    if isinstance(frame.index, pd.RangeIndex):
        return None
    try:
        index = pd.to_datetime(frame.index, errors="coerce")
    except Exception:
        return None
    if index.isna().all():
        return None
    return pd.DatetimeIndex(index).tz_localize(None).normalize()


def _to_utc_timestamp(value: datetime | pd.Timestamp | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp.now(tz=UTC)
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize(UTC)
    return timestamp.tz_convert(UTC)


def _date_string(value: pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _max_status(current: ProviderValidationStatus, candidate: ProviderValidationStatus) -> ProviderValidationStatus:
    order = {"PASS": 0, "AMBER": 1, "FAIL": 2}
    return candidate if order[candidate] > order[current] else current
