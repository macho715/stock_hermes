"""Tests for stock_rtx4060.advisors.notebooklm_news adapter."""
from __future__ import annotations

import importlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Shared fixture payload
# ---------------------------------------------------------------------------

GOOD_PAYLOAD = {
    "schema_version": "notebook_stock_analysis.v1",
    "symbol": "AAPL",
    "market": "US",
    "as_of": "2026-05-30T12:00:00+04:00",
    "notebook": {"notebook_id": "nb_001", "source_ids": ["s1"], "source_count": 2},
    "analysis": {
        "summary": "moderately bullish",
        "bullish_factors": ["AI demand"],
        "bearish_factors": ["valuation risk"],
        "ticker_relevance": 0.9,
        "sentiment": "bullish",
        "sentiment_score": 0.4,
        "market_impact": "MEDIUM_HIGH",
        "confidence": 0.8,
        "recommended_llm_instruction": "verify against momentum",
    },
    "sources": [
        {
            "source_id": "s1",
            "notebook_source_id": "s1",
            "title": "AAPL news",
            "url": "https://reuters.com/aapl",
            "source": "Reuters",
            "published_at": "2026-05-30T08:00:00Z",
            "relevance": 0.9,
        }
    ],
    "cache": {"status": "HIT", "ttl_seconds": 900, "generated_at": "2026-05-30T12:00:00+04:00"},
    "errors": [],
}


def _reload():
    import stock_rtx4060.advisors.notebooklm_news as m
    importlib.reload(m)
    return m


def _mock_httpx_ok(payload=None):
    """Return a context-manager mock that simulates a successful GET."""
    if payload is None:
        payload = GOOD_PAYLOAD
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    client_cm = MagicMock()
    client_cm.__enter__ = MagicMock(return_value=client_cm)
    client_cm.__exit__ = MagicMock(return_value=False)
    client_cm.get.return_value = resp
    return client_cm


def _mock_httpx_error(exc):
    client_cm = MagicMock()
    client_cm.__enter__ = MagicMock(return_value=client_cm)
    client_cm.__exit__ = MagicMock(return_value=False)
    client_cm.get.side_effect = exc
    return client_cm


# ---------------------------------------------------------------------------
# _enabled
# ---------------------------------------------------------------------------

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("NOTEBOOKLM_NEWS_MODE", raising=False)
    mod = _reload()
    assert not mod._enabled()


@pytest.mark.parametrize("val", ["1", "true", "on", "cache", "ON", "TRUE"])
def test_enabled_values(monkeypatch, val):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", val)
    mod = _reload()
    assert mod._enabled()


def test_off_returns_none(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "off")
    mod = _reload()
    assert mod.fetch_notebooklm_analysis("AAPL") is None


# ---------------------------------------------------------------------------
# fetch_notebooklm_analysis
# ---------------------------------------------------------------------------

def test_fetch_success(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_API_BASE", "http://127.0.0.1:8088")
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_ok()):
        result = mod.fetch_notebooklm_analysis("AAPL", market="US")
    assert result is not None
    assert result["schema_version"] == "notebook_stock_analysis.v1"


def test_fetch_wrong_schema_returns_none(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    bad = {**GOOD_PAYLOAD, "schema_version": "wrong.v99"}
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_ok(bad)):
        result = mod.fetch_notebooklm_analysis("AAPL")
    assert result is None


def test_fetch_network_error_returns_none(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    import httpx
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))):
        result = mod.fetch_notebooklm_analysis("AAPL")
    assert result is None


# ---------------------------------------------------------------------------
# enrich_context_with_notebooklm
# ---------------------------------------------------------------------------

def test_enrich_success(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("LLM_ADVISOR_PROVIDER", "anthropic")
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_ok()):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    assert ctx["notebooklm_enriched"] is True
    assert ctx["notebook_analysis"]["sentiment"] == "bullish"
    assert ctx["notebook_analysis"]["market_impact"] == "MEDIUM_HIGH"
    assert len(ctx["headlines"]) == 1
    assert ctx["notebooklm_count"] == 1


def test_enrich_disabled_returns_unchanged(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "off")
    mod = _reload()
    ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US", "factors": {}})
    assert ctx["notebooklm_enriched"] is False
    assert ctx["notebooklm_count"] == 0
    assert "notebook_analysis" not in ctx


def test_enrich_api_error_does_not_raise(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_LOCAL_FALLBACK", "off")
    import httpx
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})
    assert ctx["notebooklm_enriched"] is False


def test_enrich_api_error_uses_notelm_fallback_when_news_exists(monkeypatch, tmp_path):
    """8088 down should still inject Notelm fallback analysis from real news rows."""
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_LOCAL_FALLBACK", "true")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_LOCAL_CACHE_DIR", str(tmp_path / "notelm-cache"))
    import httpx
    mod = _reload()
    ticker = SimpleNamespace(news=[
        {
            "content": {
                "title": "AAPL AI demand growth lifts revenue outlook",
                "summary": "Analysts cite strong AI demand and revenue growth.",
                "provider": {"displayName": "Yahoo Finance"},
                "canonicalUrl": {"url": "https://finance.yahoo.com/aapl"},
                "pubDate": "2026-05-30T10:00:00Z",
            }
        }
    ])
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))), \
            patch("yfinance.Ticker", return_value=ticker):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    assert ctx["notebooklm_enriched"] is True
    assert ctx["notebook_analysis"]["analysis_source"] == "notelm_fallback"
    assert ctx["notebook_analysis"]["cache_status"] == "LOCAL_FALLBACK"
    assert ctx["notebook_analysis"]["sentiment"] == "bullish"
    assert ctx["notebooklm_count"] == 1


def test_enrich_success_applies_openai_analysis_when_provider_enabled(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("LLM_ADVISOR_PROVIDER", "openai")
    mod = _reload()

    class FakeAnalyzer:
        def analyze(self, **kwargs):
            assert kwargs["ticker"] == "AAPL"
            assert kwargs["market"] == "US"
            assert kwargs["headlines"] == ["AAPL news"]
            return {
                "summary": "OpenAI structured AAPL analysis",
                "bullish_factors": ["AI demand is improving"],
                "bearish_factors": ["Valuation remains elevated"],
                "ticker_relevance": 0.95,
                "sentiment_score": 0.55,
                "market_impact": "MEDIUM_HIGH",
                "confidence": 0.88,
                "recommended_llm_instruction": "Treat as moderately bullish, verify gates.",
                "source_ids": ["s1"],
                "analysis_source": "openai_api",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "error": None,
            }

    with patch("httpx.Client", return_value=_mock_httpx_ok()), \
            patch("stock_rtx4060.advisors.openai_client.get_openai_analyzer", return_value=FakeAnalyzer()):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    analysis = ctx["notebook_analysis"]
    assert analysis["summary"] == "OpenAI structured AAPL analysis"
    assert analysis["analysis_source"] == "openai_api"
    assert analysis["sentiment"] == "bullish"
    assert analysis["sentiment_score"] == 0.55
    assert analysis["openai_model"] == "gpt-4o-mini"
    assert analysis["openai_provider"] == "openai"


def test_openai_error_preserves_original_notelm_analysis(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("LLM_ADVISOR_PROVIDER", "openai")
    mod = _reload()

    class FakeAnalyzer:
        def analyze(self, **kwargs):
            return {
                "summary": "",
                "bullish_factors": [],
                "bearish_factors": [],
                "ticker_relevance": 0.0,
                "sentiment_score": 0.0,
                "market_impact": "LOW",
                "confidence": 0.0,
                "recommended_llm_instruction": "",
                "source_ids": [],
                "error": "openai_analysis_failed:no_api_key",
            }

    with patch("httpx.Client", return_value=_mock_httpx_ok()), \
            patch("stock_rtx4060.advisors.openai_client.get_openai_analyzer", return_value=FakeAnalyzer()):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    analysis = ctx["notebook_analysis"]
    assert analysis["summary"] == "moderately bullish"
    assert analysis["analysis_source"] == "notebooklm"
    assert analysis["openai_error"] == "openai_analysis_failed:no_api_key"
    assert ctx["headlines"][0]["source"] == "Reuters"


def test_notelm_fallback_writes_and_reads_file_cache(monkeypatch, tmp_path):
    """Fallback payload is persisted so the next call skips yfinance."""
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_LOCAL_FALLBACK", "true")
    monkeypatch.setenv("NOTEBOOKLM_NEWS_LOCAL_CACHE_DIR", str(tmp_path / "notelm-cache"))
    import httpx
    mod = _reload()
    mod._fetch_yfinance_news.cache_clear()
    ticker = SimpleNamespace(news=[
        {
            "content": {
                "title": "AAPL AI demand growth lifts revenue outlook",
                "summary": "Analysts cite strong AI demand and revenue growth.",
                "provider": {"displayName": "Yahoo Finance"},
                "canonicalUrl": {"url": "https://finance.yahoo.com/aapl"},
                "pubDate": "2026-05-30T10:00:00Z",
            }
        }
    ])
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))), \
            patch("yfinance.Ticker", return_value=ticker):
        first = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    cache_path = tmp_path / "notelm-cache" / "US" / "AAPL.json"
    assert cache_path.exists()
    assert first["notebook_analysis"]["cache_status"] == "LOCAL_FALLBACK"

    mod._fetch_yfinance_news.cache_clear()
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))), \
            patch("yfinance.Ticker", side_effect=AssertionError("cache hit should skip yfinance")):
        second = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    assert second["notebook_analysis"]["analysis_source"] == "notelm_fallback"
    assert second["notebook_analysis"]["cache_status"] == "LOCAL_CACHE_HIT"
    assert second["notebooklm_count"] == 1


def test_enrich_preserves_existing_headlines(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    mod = _reload()
    existing = [{"source": "rss", "title": "old headline"}]
    with patch("httpx.Client", return_value=_mock_httpx_ok()):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US", "headlines": existing})

    # NotebookLM sources prepended, existing appended
    assert ctx["headlines"][0]["source"] == "Reuters"
    assert ctx["headlines"][-1]["source"] == "rss"


def test_enrich_notebook_analysis_keys(monkeypatch):
    monkeypatch.setenv("NOTEBOOKLM_NEWS_MODE", "cache")
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_ok()):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})

    na = ctx["notebook_analysis"]
    for key in ("summary", "bullish_factors", "bearish_factors",
                "sentiment", "sentiment_score", "market_impact",
                "confidence", "recommended_llm_instruction", "notebook", "as_of"):
        assert key in na, f"missing key: {key}"
