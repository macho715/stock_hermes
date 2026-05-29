from __future__ import annotations

import pandas as pd

import stock_rtx4060.data_providers as data_providers
from stock_rtx4060.data_providers import load_ohlcv_with_provider


def test_cached_pykrx_provider_marks_final_bar_not_locked_after_close(monkeypatch):
    frame = pd.DataFrame(
        {
            "Date": ["2026-05-27", "2026-05-28", "2026-05-29"],
            "Open": [306000.0, 307000.0, 308000.0],
            "High": [309000.0, 310000.0, 309500.0],
            "Low": [304000.0, 305000.0, 308000.0],
            "Close": [306500.0, 307500.0, 308500.0],
            "Volume": [8_000_000.0, 8_500_000.0, 9_039_622.0],
        }
    )

    class FakeCache:
        def get(self, ticker, period, provider):
            assert (ticker, period, provider) == ("005930.KS", "3y", "pykrx")
            return frame

        def set(self, *args, **kwargs):
            raise AssertionError("cache hit should not write through")

    monkeypatch.setattr(data_providers, "_cache", FakeCache())

    result = load_ohlcv_with_provider("005930.KS", "3y", data_provider="pykrx", after_market_close=True)

    assert result.source == "pykrx:cache"
    assert result.metadata["bar_type"] == "CACHE"
    assert result.metadata["source_evidence_lock"] is False
    assert result.metadata["eod_confirmed"] is False
    assert result.metadata["final_bar_lock"]["inference_allowed"] is False
    assert result.metadata["final_bar_lock"]["readiness_status"] == "AMBER_DATA_LAG_EVENT_CONFLICT"
    assert "EOD_FINAL_BAR_NOT_LOCKED" in result.metadata["final_bar_lock"]["blocking_reasons"]
