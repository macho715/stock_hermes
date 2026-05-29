from __future__ import annotations

from stock_rtx4060.recommendation_engine import (
    RecommendationConfig,
    RecommendationEngine,
    select_post_close_provider,
)


def test_post_close_krx_auto_selects_krx_final():
    selected = select_post_close_provider(
        ticker="005930.KS",
        requested_provider="auto",
        after_market_close=True,
        provider_config={},
    )

    assert selected == "krx_final"


def test_post_close_krx_pykrx_selects_krx_final():
    selected = select_post_close_provider(
        ticker="005930.KS",
        requested_provider="pykrx",
        after_market_close=True,
        provider_config={},
    )

    assert selected == "krx_final"


def test_post_close_krx_prefers_broker_final_when_export_is_configured():
    selected = select_post_close_provider(
        ticker="005930.KS",
        requested_provider="pykrx",
        after_market_close=True,
        provider_config={"broker_final_ohlcv_path": "broker-final.csv"},
    )

    assert selected == "broker_final"


def test_regular_session_krx_keeps_requested_provider():
    selected = select_post_close_provider(
        ticker="005930.KS",
        requested_provider="pykrx",
        after_market_close=False,
        provider_config={"broker_final_ohlcv_path": "broker-final.csv"},
    )

    assert selected == "pykrx"


def test_us_ticker_post_close_keeps_requested_provider():
    selected = select_post_close_provider(
        ticker="AAPL",
        requested_provider="auto",
        after_market_close=True,
        provider_config={"broker_final_ohlcv_path": "broker-final.csv"},
    )

    assert selected == "auto"


def test_recommendation_engine_passes_effective_post_close_provider(monkeypatch):
    calls = {}

    def fake_load_ohlcv_result(*args, **kwargs):
        calls.update(kwargs)
        raise RuntimeError("stop after provider selection")

    monkeypatch.setattr("stock_rtx4060.recommendation_engine.load_ohlcv_result", fake_load_ohlcv_result)
    engine = RecommendationEngine(
        RecommendationConfig(
            universe=["005930.KS"],
            data_provider="pykrx",
            after_market_close=True,
        )
    )

    try:
        engine._load_ohlcv_cached("005930.KS")
    except RuntimeError as exc:
        assert "stop after provider selection" in str(exc)

    assert calls["data_provider"] == "krx_final"
    assert calls["after_market_close"] is True
