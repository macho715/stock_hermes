from types import SimpleNamespace

import pandas as pd

import api_server
from stock_rtx4060 import recommendation_engine as rec_engine


def test_full_universe_both_track_expands_top_for_dedupe():
    universe = ["005930.KS", "000660.KS", "005380.KS"]

    assert api_server._expanded_top_for_full_universe(universe, "BOTH", 3) == 6
    assert api_server._expanded_top_for_full_universe(universe, "S", 3) == 3
    assert api_server._expanded_top_for_full_universe(universe, "BOTH", 2) == 2


def test_full_universe_both_track_dedupes_best_sorted_result_per_ticker():
    universe = ["005930.KS", "000660.KS", "005380.KS"]
    rows = [
        SimpleNamespace(ticker="005930.KS", track="L", score=99),
        SimpleNamespace(ticker="000660.KS", track="S", score=95),
        SimpleNamespace(ticker="005930.KS", track="S", score=91),
        SimpleNamespace(ticker="005380.KS", track="L", score=90),
        SimpleNamespace(ticker="000660.KS", track="L", score=89),
    ]

    result = api_server._dedupe_full_universe_results(rows, universe, "BOTH", 3)

    assert [row.ticker for row in result] == ["005930.KS", "000660.KS", "005380.KS"]
    assert [row.track for row in result] == ["L", "S", "L"]


def test_partial_top_request_keeps_track_level_candidates():
    universe = ["005930.KS", "000660.KS", "005380.KS"]
    rows = [
        SimpleNamespace(ticker="005930.KS", track="L"),
        SimpleNamespace(ticker="005930.KS", track="S"),
    ]

    assert api_server._dedupe_full_universe_results(rows, universe, "BOTH", 2) is rows


def test_local_alt_vite_origin_is_allowed_by_cors():
    client = api_server.app.test_client()

    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5174"})

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:5174"


def test_watchlist_notelm_endpoint_returns_real_price_fields(monkeypatch):
    frame = pd.DataFrame(
        {
            "Open": [100.0, 104.0],
            "High": [105.0, 108.0],
            "Low": [99.0, 103.0],
            "Close": [102.0, 107.0],
            "Volume": [1000, 1500],
        },
        index=pd.date_range("2026-05-29", periods=2),
    )

    def fake_load_ohlcv_with_provider(*args, **kwargs):
        assert args[0] == "AAPL"
        assert kwargs["synthetic"] is False
        assert kwargs["data_provider"] == "yfinance"
        assert kwargs["command"] == "watchlist_notelm_price"
        return SimpleNamespace(frame=frame, provider_used="yfinance", source="yfinance")

    def fake_enrich_context_with_notebooklm(ticker, ctx):
        assert ticker == "AAPL"
        assert ctx["market"] == "US"
        return {
            "notebooklm_enriched": True,
            "notebooklm_count": 1,
            "notebook_analysis": {
                "sentiment": "bullish",
                "sentiment_score": 0.4,
                "confidence": 0.72,
                "analysis_source": "notelm_fallback",
            },
            "headlines": [{"title": "AAPL source-backed news", "source": "Yahoo Finance"}],
        }

    monkeypatch.setattr(api_server, "load_ohlcv_with_provider", fake_load_ohlcv_with_provider)
    monkeypatch.setattr(
        "stock_rtx4060.advisors.notebooklm_news.enrich_context_with_notebooklm",
        fake_enrich_context_with_notebooklm,
    )

    client = api_server.app.test_client()
    response = client.get("/api/watchlist-notelm?universe=AAPL&market=US")

    assert response.status_code == 200
    payload = response.get_json()
    row = payload["results"][0]
    assert row["price"] == 107.0
    assert row["previous_close"] == 102.0
    assert round(row["change"], 2) == 5.0
    assert round(row["change_pct"], 2) == 4.9
    assert row["volume"] == 1500
    assert row["price_provider"] == "yfinance"
    assert row["rec"] == "BUY"


def test_recommendation_error_result_keeps_display_data(monkeypatch):
    monkeypatch.setattr(
        rec_engine,
        "_fetch_fundamentals",
        lambda ticker: {
            "market_cap": 3_000_000_000_000.0,
            "pe_ttm": 31.4,
            "eps_ttm": 6.22,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "source": "yfinance.info",
        },
    )
    monkeypatch.setattr(
        rec_engine,
        "_notebook_context_for_snapshot",
        lambda ticker: {
            "notebooklm_count": 2,
            "notebook_analysis": {
                "market_impact": "positive",
                "confidence": 0.72,
                "as_of": "2026-05-30T00:00:00+00:00",
                "notebook": {"source_count": 2},
            },
            "headlines": [{"title": "AAPL source-backed news", "source": "Yahoo Finance"}],
        },
    )
    monkeypatch.setattr(
        rec_engine,
        "_latest_price_context",
        lambda ticker: {
            "latest_close": 195.42,
            "previous_close": 193.24,
            "change": 2.18,
            "change_pct": 1.13,
            "price_provider": "yfinance",
        },
    )

    result = rec_engine._error_result("AAPL", "S", "model failed")

    assert result.verdict == "RED_DATA_OR_MODEL_ERROR"
    assert result.latest_close == 195.42
    assert result.entry == 195.42
    assert result.tp1 > result.entry
    assert result.stop < result.entry
    assert result.fundamentals["sector"] == "Technology"
    assert result.news_headlines[0]["title"] == "AAPL source-backed news"
    assert result.notebook_analysis["market_impact"] == "positive"
    assert result.notebooklm_confidence == 0.72
    assert result.scenario_outlook["bull"]["range"] != "—"
