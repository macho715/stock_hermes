"""KRX trading calendar fixture utilities.

The checked-in fixture is a reproducible local input for paper-only KRX pilot
tests. Live PyKRX refresh is handled by the tool script, not by unit tests.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "krx_trading_calendar.v1"
MARKET = "KRX"
TIMEZONE = "Asia/Seoul"
SOURCE = "pykrx.get_previous_business_days"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KRX_CALENDAR_FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "krx_trading_calendar_2026.json"


class KRXCalendarUnavailable(RuntimeError):
    """Raised when the local KRX calendar fixture cannot support a date."""


@dataclass(frozen=True)
class KRXCalendarFixture:
    schema_version: str
    market: str
    timezone: str
    source: str
    generated_at: str
    start_date: str
    end_date: str
    trading_days: tuple[str, ...]

    @property
    def trading_day_set(self) -> set[str]:
        return set(self.trading_days)


def load_krx_calendar_fixture(path: Path | str = KRX_CALENDAR_FIXTURE_PATH) -> KRXCalendarFixture:
    fixture_path = Path(path)
    if not fixture_path.exists():
        raise KRXCalendarUnavailable(f"krx_calendar_unavailable: {fixture_path}")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    date_range = payload.get("date_range") or {}
    trading_days = tuple(_normalize_days(payload.get("trading_days") or []))
    fixture = KRXCalendarFixture(
        schema_version=str(payload.get("schema_version") or ""),
        market=str(payload.get("market") or ""),
        timezone=str(payload.get("timezone") or ""),
        source=str(payload.get("source") or ""),
        generated_at=str(payload.get("generated_at") or ""),
        start_date=str(date_range.get("start") or ""),
        end_date=str(date_range.get("end") or ""),
        trading_days=trading_days,
    )
    _validate_fixture(fixture)
    return fixture


def next_krx_session(session_date: str | date, fixture: KRXCalendarFixture) -> str:
    current = _parse_date(session_date)
    start = _parse_date(fixture.start_date)
    end = _parse_date(fixture.end_date)
    if current < start or current > end:
        raise KRXCalendarUnavailable("krx_calendar_range_missing")

    trading_days = fixture.trading_day_set
    while current <= end:
        candidate = current.isoformat()
        if candidate in trading_days:
            return candidate
        current += timedelta(days=1)
    raise KRXCalendarUnavailable("krx_calendar_range_missing")


def generate_krx_calendar_fixture(
    output_path: Path | str,
    *,
    start_date: str,
    end_date: str,
    trading_days: Iterable[str | date],
    generated_at: str | None = None,
    source_status: str = "generated",
    notes: list[str] | None = None,
) -> Path:
    output = Path(output_path)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "market": MARKET,
        "timezone": TIMEZONE,
        "source": SOURCE,
        "source_status": source_status,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "date_range": {"start": _parse_date(start_date).isoformat(), "end": _parse_date(end_date).isoformat()},
        "trading_days": _normalize_days(trading_days),
        "notes": notes or [],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, output)
    return output


def _validate_fixture(fixture: KRXCalendarFixture) -> None:
    if fixture.schema_version != SCHEMA_VERSION:
        raise KRXCalendarUnavailable("krx_calendar_schema_mismatch")
    if fixture.market != MARKET:
        raise KRXCalendarUnavailable("krx_calendar_market_mismatch")
    if fixture.timezone != TIMEZONE:
        raise KRXCalendarUnavailable("krx_calendar_timezone_mismatch")
    if fixture.source != SOURCE:
        raise KRXCalendarUnavailable("krx_calendar_source_mismatch")
    if not fixture.trading_days:
        raise KRXCalendarUnavailable("krx_calendar_empty")
    if list(fixture.trading_days) != sorted(set(fixture.trading_days)):
        raise KRXCalendarUnavailable("krx_calendar_days_not_sorted_unique")
    if fixture.trading_days[0] < fixture.start_date or fixture.trading_days[-1] > fixture.end_date:
        raise KRXCalendarUnavailable("krx_calendar_range_mismatch")


def _normalize_days(days: Iterable[str | date]) -> list[str]:
    return sorted({_parse_date(day).isoformat() for day in days})


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
