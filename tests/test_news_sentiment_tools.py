"""Tests for news_sentiment.py and macro_regime.py tool injection."""

from __future__ import annotations

import asyncio
import unittest.mock as mock

from stock_rtx4060.advisors.base import AdvisoryOutput
from stock_rtx4060.advisors.claude_client import CallResult


def _make_call_result(text='{"score": 0.3, "confidence": 0.7, "rationale": "bullish"}'):
    return CallResult(
        text=text,
        raw_message=None,
        tokens_in=100,
        tokens_out=50,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        cost_usd=0.001,
        prompt_hash="abc123",
        model="claude-opus-4-7",
    )


def _make_news_item():
    item = mock.MagicMock()
    item.source = "test"
    item.title = "headline"
    item.url = "http://example.com"
    item.summary = ""
    item.__dict__ = {"source": "test", "title": "headline", "url": "http://example.com", "summary": ""}
    return item


# ---------------------------------------------------------------------------
# NewsSentimentAgent
# ---------------------------------------------------------------------------

def test_news_agent_uses_acall_when_tools_disabled(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.news_sentiment._OPENBB_TOOLS_ENABLED", False
    )
    from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
    agent = NewsSentimentAgent()
    acall_mock = mock.AsyncMock(return_value=_make_call_result())
    with mock.patch.object(agent.client, "acall", acall_mock):
        with mock.patch.object(agent, "_fetch_for_ticker", return_value=[_make_news_item()]):
            result = asyncio.run(agent.analyze("AAPL", {}))
    acall_mock.assert_called_once()
    assert isinstance(result, AdvisoryOutput)


def test_news_agent_uses_acall_with_tools_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.news_sentiment._OPENBB_TOOLS_ENABLED", True
    )
    from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
    agent = NewsSentimentAgent()
    acall_tools_mock = mock.AsyncMock(return_value=_make_call_result())
    with mock.patch.object(agent.client, "acall_with_tools", acall_tools_mock):
        with mock.patch.object(agent, "_fetch_for_ticker", return_value=[_make_news_item()]):
            result = asyncio.run(agent.analyze("AAPL", {}))
    acall_tools_mock.assert_called_once()
    assert isinstance(result, AdvisoryOutput)


def test_news_agent_passes_as_of_to_tools(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.news_sentiment._OPENBB_TOOLS_ENABLED", True
    )
    from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
    agent = NewsSentimentAgent()
    acall_tools_mock = mock.AsyncMock(return_value=_make_call_result())
    with mock.patch.object(agent.client, "acall_with_tools", acall_tools_mock):
        with mock.patch.object(agent, "_fetch_for_ticker", return_value=[_make_news_item()]):
            asyncio.run(agent.analyze("AAPL", {"as_of": "2026-05-29"}))
    _, kwargs = acall_tools_mock.call_args
    assert kwargs.get("as_of") == "2026-05-29"


def test_news_agent_neutral_when_no_headlines(monkeypatch):
    """No headlines → neutral result without any LLM call."""
    monkeypatch.setattr(
        "stock_rtx4060.advisors.news_sentiment._OPENBB_TOOLS_ENABLED", False
    )
    from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
    agent = NewsSentimentAgent()
    with mock.patch.object(agent, "_fetch_for_ticker", return_value=[]):
        result = asyncio.run(agent.analyze("AAPL", {}))
    assert result.score == 0.0
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# MacroRegimeAgent
# ---------------------------------------------------------------------------

def test_macro_agent_uses_acall_when_tools_disabled(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.macro_regime._OPENBB_TOOLS_ENABLED", False
    )
    from stock_rtx4060.advisors.macro_regime import MacroRegimeAgent
    agent = MacroRegimeAgent()
    panel = {"t10y2y": 0.5, "vix": 18.0, "dxy": 103.0}
    with mock.patch.object(agent, "_build_panel", return_value=panel):
        acall_mock = mock.AsyncMock(return_value=_make_call_result(
            '{"regime":"neutral","score":0.0,"confidence":0.6,"rationale":"stable"}'
        ))
        with mock.patch.object(agent.client, "acall", acall_mock):
            result = asyncio.run(agent.analyze("AAPL", {}))
    acall_mock.assert_called_once()
    assert isinstance(result, AdvisoryOutput)


def test_macro_agent_uses_acall_with_tools_when_enabled(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.macro_regime._OPENBB_TOOLS_ENABLED", True
    )
    from stock_rtx4060.advisors.macro_regime import MacroRegimeAgent
    agent = MacroRegimeAgent()
    panel = {"vix": 20.0, "t10y2y": -0.1}
    with mock.patch.object(agent, "_build_panel", return_value=panel):
        acall_tools_mock = mock.AsyncMock(return_value=_make_call_result(
            '{"regime":"risk_off","score":-0.3,"confidence":0.75,"rationale":"inverted curve"}'
        ))
        with mock.patch.object(agent.client, "acall_with_tools", acall_tools_mock):
            result = asyncio.run(agent.analyze("AAPL", {}))
    acall_tools_mock.assert_called_once()
    assert isinstance(result, AdvisoryOutput)
    assert result.score < 0


def test_macro_agent_neutral_when_no_panel(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.macro_regime._OPENBB_TOOLS_ENABLED", True
    )
    from stock_rtx4060.advisors.macro_regime import MacroRegimeAgent
    agent = MacroRegimeAgent()
    with mock.patch.object(agent, "_build_panel", return_value={}):
        result = asyncio.run(agent.analyze("AAPL", {}))
    assert result.score == 0.0
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Backward compatibility — score clamping still works
# ---------------------------------------------------------------------------

def test_news_agent_score_clamped(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.news_sentiment._OPENBB_TOOLS_ENABLED", False
    )
    from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
    agent = NewsSentimentAgent()
    with mock.patch.object(agent.client, "acall", mock.AsyncMock(
        return_value=_make_call_result('{"score": 1.5, "confidence": 0.9, "rationale": "x"}')
    )):
        with mock.patch.object(agent, "_fetch_for_ticker", return_value=[_make_news_item()]):
            result = asyncio.run(agent.analyze("AAPL", {}))
    assert -1.0 <= result.score <= 1.0
