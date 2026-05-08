"""Tests for :class:`stock_rtx4060.advisors.news_sentiment.NewsSentimentAgent`."""

from __future__ import annotations

import asyncio

from stock_rtx4060.advisors.base import AdvisoryOutput
from stock_rtx4060.advisors.claude_client import CallResult
from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent


class _StubClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def acall(self, *, system, messages, tools=None, max_tokens=None):
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        return CallResult(
            text=self.payload,
            raw_message=None,
            tokens_in=120,
            tokens_out=40,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.001,
            prompt_hash="hash-news",
            model="claude-opus-4-7",
        )


def test_news_sentiment_returns_neutral_when_no_data():
    agent = NewsSentimentAgent(client=_StubClient(""))
    out = asyncio.run(agent.analyze("AAPL", {}))
    assert isinstance(out, AdvisoryOutput)
    assert out.score == 0.0
    assert out.confidence == 0.0
    assert "no news data" in out.rationale


def test_news_sentiment_uses_injected_headlines():
    payload = '{"score": 0.4, "confidence": 0.6, "rationale": "positive guidance", "citations": ["http://r/1"]}'
    client = _StubClient(payload)
    agent = NewsSentimentAgent(client=client)
    context = {
        "headlines": [
            {"source": "reuters", "title": "AAPL beats earnings", "url": "http://r/1", "summary": "Apple beats"},
        ]
    }
    out = asyncio.run(agent.analyze("AAPL", context))
    assert out.score == 0.4
    assert out.confidence == 0.6
    assert "positive" in out.rationale
    assert out.citations == ["http://r/1"]
    assert out.prompt_hash == "hash-news"
    assert out.tokens_in == 120
    assert out.cost_usd == 0.001
    # The user message must mention the ticker so we know the prompt
    # render reached the model.
    user_text = client.calls[0]["messages"][0]["content"]
    assert "AAPL" in user_text


def test_news_sentiment_clamps_out_of_range_score():
    payload = '{"score": 99, "confidence": 99, "rationale": "x", "citations": []}'
    agent = NewsSentimentAgent(client=_StubClient(payload))
    context = {"headlines": [{"source": "x", "title": "AAPL", "url": "u"}]}
    out = asyncio.run(agent.analyze("AAPL", context))
    assert -1.0 <= out.score <= 1.0
    assert 0.0 <= out.confidence <= 1.0


def test_news_sentiment_falls_back_to_headline_urls_when_citations_missing():
    payload = '{"score": 0.1, "confidence": 0.2, "rationale": "ok"}'
    agent = NewsSentimentAgent(client=_StubClient(payload))
    context = {"headlines": [{"source": "x", "title": "AAPL beat", "url": "http://r/2"}]}
    out = asyncio.run(agent.analyze("AAPL", context))
    assert "http://r/2" in out.citations
