"""Tests for OpenAI News Analyzer (Structured Outputs).

Unit tests use mocked OpenAI calls (no real API key needed).
Integration test is skipped unless OPENAI_API_KEY is set.
"""

from __future__ import annotations

import json
import os
import unittest.mock as mock

import pytest

from stock_rtx4060.advisors.openai_client import (
    NotebookAnalysis,
    OpenAINewsAnalyzer,
    _PYDANTIC_AVAILABLE,
    get_openai_analyzer,
    is_openai_provider,
)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

def test_notebook_analysis_schema_has_required_fields():
    """NotebookAnalysis Pydantic schema must have all required fields."""
    assert _PYDANTIC_AVAILABLE, "pydantic must be installed"
    fields = set(NotebookAnalysis.model_fields.keys())
    required = {
        "summary", "bullish_factors", "bearish_factors",
        "ticker_relevance", "sentiment_score", "market_impact",
        "confidence", "recommended_llm_instruction", "source_ids",
    }
    assert required.issubset(fields), f"Missing fields: {required - fields}"


def test_notebook_analysis_sentiment_bounds():
    """sentiment_score must be in [-1, 1]."""
    with pytest.raises(Exception):
        NotebookAnalysis(
            summary="test", bullish_factors=[], bearish_factors=[],
            ticker_relevance=0.5, sentiment_score=2.0,  # invalid
            market_impact="LOW", confidence=0.5,
            recommended_llm_instruction="test",
        )


def test_notebook_analysis_confidence_bounds():
    """confidence must be in [0, 1]."""
    with pytest.raises(Exception):
        NotebookAnalysis(
            summary="test", bullish_factors=[], bearish_factors=[],
            ticker_relevance=0.5, sentiment_score=0.0,
            market_impact="LOW", confidence=1.5,  # invalid
            recommended_llm_instruction="test",
        )


def test_notebook_analysis_valid_construction():
    """Valid NotebookAnalysis should construct without error."""
    obj = NotebookAnalysis(
        summary="Test summary",
        bullish_factors=["Factor 1"],
        bearish_factors=[],
        ticker_relevance=0.87,
        sentiment_score=0.42,
        market_impact="MEDIUM_HIGH",
        confidence=0.78,
        recommended_llm_instruction="Treat as bullish",
        source_ids=["src_001"],
    )
    assert obj.sentiment_score == 0.42
    assert obj.market_impact == "MEDIUM_HIGH"
    d = obj.model_dump()
    assert d["ticker_relevance"] == 0.87


# ---------------------------------------------------------------------------
# Analyzer tests (mocked API)
# ---------------------------------------------------------------------------

def _make_mock_response(data: dict):
    """Build a mock OpenAI responses.parse() response."""
    parsed = NotebookAnalysis(**data)
    resp = mock.MagicMock()
    resp.output_parsed = parsed
    return resp


def test_analyzer_returns_notebook_analysis_dict():
    """analyze() must return a dict with all notebook_analysis keys."""
    analyzer = OpenAINewsAnalyzer(api_key="test-key", model="gpt-4o-mini")
    mock_data = {
        "summary": "AAPL AI demand strong",
        "bullish_factors": ["AI revenue growth"],
        "bearish_factors": ["Valuation stretch"],
        "ticker_relevance": 0.9,
        "sentiment_score": 0.5,
        "market_impact": "MEDIUM",
        "confidence": 0.75,
        "recommended_llm_instruction": "Moderate bullish",
        "source_ids": [],
    }
    with mock.patch.object(
        analyzer, "_get_client"
    ) as mock_client:
        mc = mock.MagicMock()
        mc.responses.parse.return_value = _make_mock_response(mock_data)
        mock_client.return_value = mc

        result = analyzer.analyze(
            ticker="AAPL", market="US",
            headlines=["Apple beats earnings", "iPhone demand strong"],
        )

    assert result["summary"] == "AAPL AI demand strong"
    assert result["sentiment_score"] == 0.5
    assert result["market_impact"] == "MEDIUM"
    assert result["error"] is None


def test_analyzer_fallback_on_api_error():
    """When OpenAI API raises, fallback dict with error key is returned."""
    analyzer = OpenAINewsAnalyzer(api_key="test-key", model="gpt-4o-mini")
    with mock.patch.object(analyzer, "_get_client") as mock_client:
        mc = mock.MagicMock()
        mc.responses.parse.side_effect = Exception("API timeout")
        mock_client.return_value = mc

        result = analyzer.analyze(
            ticker="AAPL", market="US", headlines=["Some news"]
        )

    assert "error" in result
    assert "openai_analysis_failed" in result["error"]
    assert result["sentiment_score"] == 0.0


def test_analyzer_neutral_when_no_headlines():
    """Empty headlines + no notebook_summary returns neutral dict."""
    analyzer = OpenAINewsAnalyzer(api_key="test-key")
    result = analyzer.analyze(ticker="MSFT", market="US", headlines=[])
    assert result["sentiment_score"] == 0.0
    assert result["market_impact"] == "LOW"
    assert result.get("error") is None


def test_analyzer_no_api_key_returns_fallback():
    """No API key → fallback with no_api_key error."""
    analyzer = OpenAINewsAnalyzer(api_key="")
    result = analyzer.analyze(ticker="NVDA", market="US", headlines=["NVDA record"])
    assert "no_api_key" in result.get("error", "")


# ---------------------------------------------------------------------------
# Provider factory tests
# ---------------------------------------------------------------------------

def test_is_openai_provider_false_by_default(monkeypatch):
    monkeypatch.setenv("LLM_ADVISOR_PROVIDER", "anthropic")
    import importlib
    import stock_rtx4060.advisors.openai_client as m
    importlib.reload(m)
    assert not m.is_openai_provider()


def test_get_openai_analyzer_none_when_not_openai(monkeypatch):
    monkeypatch.setenv("LLM_ADVISOR_PROVIDER", "minimax")
    import importlib
    import stock_rtx4060.advisors.openai_client as m
    importlib.reload(m)
    assert m.get_openai_analyzer() is None


# ---------------------------------------------------------------------------
# Integration test (skipped unless explicitly enabled with a valid key)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("RUN_OPENAI_LIVE_TESTS") != "1" or not os.environ.get("OPENAI_API_KEY"),
    reason="RUN_OPENAI_LIVE_TESTS=1 and OPENAI_API_KEY are required for live integration",
)
def test_live_analyze_aapl():
    """Integration: real OpenAI call with gpt-4o-mini."""
    analyzer = OpenAINewsAnalyzer(model="gpt-4o-mini")
    result = analyzer.analyze(
        ticker="AAPL", market="US",
        headlines=[
            "Apple reports record quarterly revenue",
            "iPhone 16 Pro demand exceeds expectations",
        ],
        company_name="Apple Inc.",
    )
    assert result.get("error") is None, f"API error: {result.get('error')}"
    assert -1.0 <= result["sentiment_score"] <= 1.0
    assert result["market_impact"] in {"LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH", "CRITICAL"}
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["bullish_factors"], list)
    assert isinstance(result["bearish_factors"], list)
