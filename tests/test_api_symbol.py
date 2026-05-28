import pandas as pd

import api_server


def test_frame_to_ohlcv_records_uses_date_column_with_range_index():
    frame = pd.DataFrame(
        {
            "Date": ["2026-05-01", "2026-05-04"],
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [1000, 2000],
        }
    )

    records = api_server._frame_to_ohlcv_records(frame)

    assert records[0]["date"] == "2026-05-01"
    assert records[1]["date"] == "2026-05-04"
    assert records[1]["timestamp"] > records[0]["timestamp"]
