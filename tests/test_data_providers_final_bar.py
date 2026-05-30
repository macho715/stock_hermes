from __future__ import annotations

import sys
from types import SimpleNamespace

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


def test_krx_final_provider_marks_authoritative_eod_final(monkeypatch):
    frame = pd.DataFrame(
        {
            "시가": [306000, 307000, 308000],
            "고가": [309000, 310000, 317000],
            "저가": [304000, 305000, 305500],
            "종가": [306500, 307500, 317000],
            "거래량": [8_000_000, 8_500_000, 37_241_537],
        },
        index=pd.to_datetime(["2026-05-27", "2026-05-28", "2026-05-29"]),
    )
    calls = {}

    def get_market_ohlcv_by_date(start_date, end_date, symbol, freq="d", adjusted=True):
        calls.update(
            {
                "start_date": start_date,
                "end_date": end_date,
                "symbol": symbol,
                "freq": freq,
                "adjusted": adjusted,
            }
        )
        return frame

    fake_stock = SimpleNamespace(get_market_ohlcv_by_date=get_market_ohlcv_by_date)
    monkeypatch.setitem(sys.modules, "pykrx", SimpleNamespace(stock=fake_stock))
    monkeypatch.setattr(data_providers, "_cache", SimpleNamespace(get=lambda *args: None, set=lambda *args: None))

    result = load_ohlcv_with_provider("005930.KS", "5y", data_provider="krx_final", after_market_close=True)

    assert calls["symbol"] == "005930"
    assert result.provider_used == "krx_final"
    assert result.source == "KRX_FINAL"
    assert result.metadata["source_priority"] == 1
    assert result.metadata["bar_type"] == "EOD_FINAL"
    assert result.metadata["eod_confirmed"] is True
    assert result.metadata["source_evidence_lock"] is True
    assert result.metadata["after_market_close"] is True
    assert result.metadata["final_bar_lock"]["inference_allowed"] is True
    assert result.metadata["final_bar_lock"]["readiness_status"] == "PASS"


def test_krx_final_missing_bar_blocks_inference(monkeypatch):
    """When KRX final provider returns empty frame, inference must be blocked."""
    calls = {}

    def get_market_ohlcv_by_date(start_date, end_date, symbol, freq="d", adjusted=True):
        calls.update(
            {
                "start_date": start_date,
                "end_date": end_date,
                "symbol": symbol,
                "freq": freq,
                "adjusted": adjusted,
            }
        )
        return pd.DataFrame()  # empty = no final bar available

    fake_stock = SimpleNamespace(get_market_ohlcv_by_date=get_market_ohlcv_by_date)
    monkeypatch.setitem(sys.modules, "pykrx", SimpleNamespace(stock=fake_stock))
    monkeypatch.setattr(data_providers, "_cache", SimpleNamespace(get=lambda *args: None, set=lambda *args: None))

    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="krx_final",
        after_market_close=True,
        data_lake_first=False,
    )

    assert result.metadata["eod_confirmed"] is False
    assert result.metadata["source_evidence_lock"] is False
    assert result.metadata["final_bar_lock"]["inference_allowed"] is False
    assert result.metadata["final_bar_lock"]["readiness_status"] == "AMBER_DATA_LAG_EVENT_CONFLICT"


def test_broker_final_provider_marks_authoritative_eod_final_from_configured_export(tmp_path, monkeypatch):
    export_path = tmp_path / "005930_broker_final.csv"
    export_path.write_text(
        "\n".join(
            [
                "Date,Open,High,Low,Close,Volume",
                "2026-05-27,306000,309000,304000,306500,8000000",
                "2026-05-28,307000,310000,305000,307500,8500000",
                "2026-05-29,308000,317000,305500,317000,37241537",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(data_providers, "_cache", SimpleNamespace(get=lambda *args: None, set=lambda *args: None))

    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="broker_final",
        provider_config={"broker_final_ohlcv_path": str(export_path)},
        after_market_close=True,
    )

    assert result.provider_used == "broker_final"
    assert result.source == "BROKER_FINAL"
    assert result.metadata["source_priority"] == 1
    assert result.metadata["bar_type"] == "EOD_FINAL"
    assert result.metadata["eod_confirmed"] is True
    assert result.metadata["source_evidence_lock"] is True
    assert result.metadata["final_bar_lock"]["inference_allowed"] is True
    assert result.frame.iloc[-1]["Close"] == 317000
    assert result.frame.iloc[-1]["Volume"] == 37241537
