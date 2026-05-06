import json
from pathlib import Path

import pytest

from stock_rtx4060.krx_calendar import (
    KRX_CALENDAR_FIXTURE_PATH,
    KRXCalendarUnavailable,
    generate_krx_calendar_fixture,
    load_krx_calendar_fixture,
    next_krx_session,
)


def test_checked_in_krx_calendar_fixture_has_required_contract():
    fixture = load_krx_calendar_fixture(KRX_CALENDAR_FIXTURE_PATH)

    assert fixture.schema_version == "krx_trading_calendar.v1"
    assert fixture.market == "KRX"
    assert fixture.timezone == "Asia/Seoul"
    assert fixture.source == "pykrx.get_previous_business_days"
    assert fixture.start_date <= "2026-01-02"
    assert fixture.end_date >= "2026-12-30"
    assert "2026-01-02" in fixture.trading_days
    assert "2026-01-01" not in fixture.trading_days


def test_krx_calendar_skips_non_trading_day_and_fails_closed_out_of_range():
    fixture = load_krx_calendar_fixture(KRX_CALENDAR_FIXTURE_PATH)

    assert next_krx_session("2026-01-01", fixture) == "2026-01-02"
    assert next_krx_session("2026-01-02", fixture) == "2026-01-02"

    with pytest.raises(KRXCalendarUnavailable, match="krx_calendar_range_missing"):
        next_krx_session("2027-01-01", fixture)


def test_generate_krx_calendar_fixture_writes_sorted_deterministic_payload():
    output = Path("reports/test_outputs/krx_trading_calendar_unit.json")
    try:
        written = generate_krx_calendar_fixture(
            output,
            start_date="2026-01-01",
            end_date="2026-01-06",
            trading_days=["2026-01-05", "2026-01-02", "2026-01-06"],
            generated_at="2026-05-05T00:00:00+00:00",
        )

        payload = json.loads(written.read_text(encoding="utf-8"))
        assert written == output
        assert payload["schema_version"] == "krx_trading_calendar.v1"
        assert payload["market"] == "KRX"
        assert payload["timezone"] == "Asia/Seoul"
        assert payload["source"] == "pykrx.get_previous_business_days"
        assert payload["date_range"] == {"start": "2026-01-01", "end": "2026-01-06"}
        assert payload["trading_days"] == ["2026-01-02", "2026-01-05", "2026-01-06"]
        assert not Path(str(output) + ".tmp").exists()
    finally:
        output.unlink(missing_ok=True)
