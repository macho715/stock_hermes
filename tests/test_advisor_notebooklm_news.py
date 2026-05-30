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
    import httpx
    mod = _reload()
    with patch("httpx.Client", return_value=_mock_httpx_error(httpx.ConnectError("refused"))):
        ctx = mod.enrich_context_with_notebooklm("AAPL", {"market": "US"})
    assert ctx["notebooklm_enriched"] is False


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
