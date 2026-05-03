import pandas as pd

from stock_rtx4060.provider_validation import validate_provider_frame


def _frame(index=None):
    idx = index if index is not None else pd.bdate_range("2026-04-01", periods=5)
    return pd.DataFrame(
        {
            "Open": [10, 11, 12, 13, 14],
            "High": [11, 12, 13, 14, 15],
            "Low": [9, 10, 11, 12, 13],
            "Close": [10.5, 11.5, 12.5, 13.5, 14.5],
            "Volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=idx,
    )


def test_provider_validation_passes_clean_synthetic_frame():
    result = validate_provider_frame(
        _frame(),
        provider_used="synthetic",
        ticker="SYNTH-A",
        period="3y",
        as_of=pd.Timestamp("2026-04-08", tz="UTC"),
        min_rows=5,
    )

    assert result.status == "PASS"
    assert result.metadata["row_count"] == 5
    assert result.metadata["first_date"] == "2026-04-01"
    assert result.metadata["last_date"] == "2026-04-07"
    assert result.metadata["provider_validation_status"] == "PASS"


def test_provider_validation_fails_missing_required_ohlcv_column():
    frame = _frame().drop(columns=["Volume"])

    result = validate_provider_frame(frame, provider_used="yfinance", ticker="AAPL", period="1y", min_rows=5)

    assert result.status == "FAIL"
    assert "Volume" in result.metadata["missing_ohlcv_columns"]


def test_provider_validation_flags_future_and_duplicate_dates():
    index = pd.DatetimeIndex(["2026-04-01", "2026-04-02", "2026-04-02", "2026-04-06", "2026-04-20"])

    result = validate_provider_frame(
        _frame(index),
        provider_used="yfinance",
        ticker="AAPL",
        period="1y",
        as_of=pd.Timestamp("2026-04-08", tz="UTC"),
        min_rows=5,
    )

    assert result.status == "FAIL"
    assert result.metadata["future_rows"] == 1
    assert result.metadata["duplicate_dates"] == 1


def test_provider_validation_marks_stale_real_provider_as_amber():
    result = validate_provider_frame(
        _frame(),
        provider_used="yfinance",
        ticker="AAPL",
        period="1y",
        as_of=pd.Timestamp("2026-04-20", tz="UTC"),
        min_rows=5,
        freshness_days_warn=3,
        freshness_days_fail=30,
    )

    assert result.status == "AMBER"
    assert result.metadata["freshness_days"] == 13
