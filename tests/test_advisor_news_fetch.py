"""Coverage for the news-fetch injection seam."""

from __future__ import annotations

import asyncio

from stock_rtx4060.advisors.claude_client import CallResult
from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent, _NewsItem


class _StubClient:
    async def acall(self, *, system, messages, tools=None, max_tokens=None):
        return CallResult(
            text='{"score": 0.2, "confidence": 0.5, "rationale": "ok", "citations": ["http://x"]}',
            raw_message=None,
            tokens_in=10,
            tokens_out=5,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.0,
            prompt_hash="h",
            model="claude-opus-4-7",
        )


def test_fetch_fn_seam_used_when_no_context_headlines():
    captured: dict = {}

    def fake_fetch(ticker, context):
        captured["ticker"] = ticker
        return [_NewsItem(source="x", title=f"{ticker} headline", url="http://x", summary="s")]

    agent = NewsSentimentAgent(client=_StubClient(), fetch_fn=fake_fetch)
    out = asyncio.run(agent.analyze("MSFT", {}))
    assert captured["ticker"] == "MSFT"
    assert out.score == 0.2


def test_no_news_when_fetch_fn_returns_empty():
    agent = NewsSentimentAgent(client=_StubClient(), fetch_fn=lambda *_a, **_k: [])
    out = asyncio.run(agent.analyze("AAPL", {}))
    assert out.rationale == "no news data"
    assert out.score == 0.0
    assert out.confidence == 0.0


def test_macro_panel_fetcher_seam():
    from stock_rtx4060.advisors.macro_regime import MacroRegimeAgent

    panel = {"t10y2y": 0.05, "vix": 18.0, "dxy": 100, "kospi_trend_pct": 0.01, "spy_trend_pct": 0.02, "krwusd": 1330}
    agent = MacroRegimeAgent(client=_StubClient(), panel_fetcher=lambda: panel)
    out = asyncio.run(agent.analyze("SPY", {}))
    # Stub client returns a positive score JSON; the regime classifier
    # accepts that without erroring out.
    assert -1.0 <= out.score <= 1.0
