from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.run_cfast_validation import validate_price_frame  # noqa: E402


def test_timeseries_input_rejects_missing_date():
    frame = pd.DataFrame({"SPY": [1.0, 2.0, 3.0]})

    with pytest.raises(ValueError, match="Date"):
        validate_price_frame(frame, min_rows=2)


def test_timeseries_input_rejects_duplicate_dates():
    frame = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-01", "2024-01-02"],
        "SPY": [1.0, 2.0, 3.0],
    })

    with pytest.raises(ValueError, match="duplicates"):
        validate_price_frame(frame, min_rows=2)


def test_timeseries_input_rejects_descending_dates():
    frame = pd.DataFrame({
        "Date": ["2024-01-03", "2024-01-02", "2024-01-01"],
        "SPY": [1.0, 2.0, 3.0],
    })

    with pytest.raises(ValueError, match="increasing"):
        validate_price_frame(frame, min_rows=2)


def test_timeseries_input_rejects_insufficient_rows():
    frame = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "SPY": [1.0, 2.0],
    })

    with pytest.raises(ValueError, match="at least 3"):
        validate_price_frame(frame, min_rows=3)
