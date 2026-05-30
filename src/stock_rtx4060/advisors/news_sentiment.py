"""News sentiment agent.

Pulls headlines from RSS feeds (Reuters / Yonhap / Maeil for KR; Naver
news for KRX tickers; SEC EDGAR 8-K for US tickers) and asks Claude to
score the directional sentiment of the resulting flow.

When all sources are offline (or the optional dependencies are missing)
the agent returns a neutral score of ``0.0`` with confidence ``0.0`` and
rationale ``"no news data"`` — this is the documented degraded mode.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base import AdvisoryOutput
from .claude_client import _OPENBB_TOOLS_ENABLED, ClaudeClient
from .prompts import load_prompt, render

logger = logging.getLogger(__name__)

# Default RSS feeds keyed by source ID.  Tests inject their own.
DEFAULT_FEEDS = {
    "reuters": "https://www.reutersagency.com/feed/?best-topics=business-finance",
    "yonhap": "https://en.yna.co.kr/RSS/business.xml",
    "mk": "https://rss.mk.co.kr/rss/30000023.xml",
    "naver": "https://rss.naver.com/business.xml",
}


@dataclass
class _NewsItem:
    source: str
    title: str
    url: str
    summary: str = ""


@dataclass
class NewsSentimentAgent:
    """News sentiment advisor.  See module docstring for behaviour."""

    name: str = "news_sentiment"
    client: ClaudeClient = field(default_factory=ClaudeClient)
    feeds: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FEEDS))
    max_headlines: int = 12
    fetch_fn: Any = None  # injection seam for tests — see _fetch_for_ticker

    async def analyze(self, ticker: str, context: dict[str, Any]) -> AdvisoryOutput:
        as_of = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            headlines = list(self._fetch_for_ticker(ticker, context))
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("news fetch failed for %s: %s", ticker, exc)
            headlines = []

        if not headlines:
            # Degraded path — no live data, hand back the neutral verdict.
            return AdvisoryOutput(
                agent=self.name,
                ticker=ticker,
                score=0.0,
                confidence=0.0,
                rationale="no news data",
                citations=[],
                prompt_hash="",
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
            )

        system_tpl = load_prompt("news_system")
        user_tpl = load_prompt("news_user")
        rendered_user = render(
            user_tpl,
            {
                "ticker": ticker,
                "as_of": as_of,
                "headlines": [h.__dict__ for h in headlines],
                "notebook_analysis": context.get("notebook_analysis"),
            },
        )

        if _OPENBB_TOOLS_ENABLED:
            from .openbb_tools.tool_schemas import NEWS_TOOLS
            result = await self.client.acall_with_tools(
                system=system_tpl,
                messages=[{"role": "user", "content": rendered_user}],
                tools=NEWS_TOOLS,
                as_of=context.get("as_of"),
            )
        else:
            result = await self.client.acall(
                system=system_tpl,
                messages=[{"role": "user", "content": rendered_user}],
            )
        parsed = _parse_advisor_json(result.text)
        score = _clip(parsed.get("score", 0.0), -1.0, 1.0)
        confidence = _clip(parsed.get("confidence", 0.0), 0.0, 1.0)
        rationale = str(parsed.get("rationale", ""))[:1024]
        citations = list(parsed.get("citations", [])) or [h.url for h in headlines[:3]]
        # [AMH Memory — W4 FR-5] extract STL proposition from model output
        proposition = str(parsed.get("proposition", "") or parsed.get("logical_proposition", ""))[:512]
        return AdvisoryOutput(
            agent=self.name,
            ticker=ticker,
            score=float(score),
            confidence=float(confidence),
            rationale=rationale,
            citations=[str(c) for c in citations],
            prompt_hash=result.prompt_hash,
            tokens_in=int(result.tokens_in),
            tokens_out=int(result.tokens_out),
            cost_usd=float(result.cost_usd),
            logical_proposition=proposition,
        )

    # ------------------------------------------------------------------

    def _fetch_for_ticker(self, ticker: str, context: dict[str, Any]) -> Iterable[_NewsItem]:
        """Fetch headlines.  ``context['headlines']`` overrides the live fetch."""
        injected = context.get("headlines")
        if injected:
            for entry in injected[: self.max_headlines]:
                yield _NewsItem(
                    source=str(entry.get("source", "context")),
                    title=str(entry.get("title", "")),
                    url=str(entry.get("url", "")),
                    summary=str(entry.get("summary", "")),
                )
            return

        if self.fetch_fn is not None:
            for item in list(self.fetch_fn(ticker, context))[: self.max_headlines]:
                yield item
            return

        try:
            import feedparser  # type: ignore[import-not-found]
        except ImportError:
            return

        seen: set[str] = set()
        out: list[_NewsItem] = []
        for source_id, feed_url in self.feeds.items():
            try:
                parsed = feedparser.parse(feed_url)  # type: ignore[no-untyped-call]
            except Exception as exc:  # pragma: no cover - network error
                logger.debug("feed %s failed: %s", source_id, exc)
                continue
            for entry in getattr(parsed, "entries", [])[: self.max_headlines]:
                title = getattr(entry, "title", "") or ""
                link = getattr(entry, "link", "") or ""
                summary = getattr(entry, "summary", "") or ""
                if not title or not _matches_ticker(ticker, title + " " + summary):
                    continue
                if link in seen:
                    continue
                seen.add(link)
                out.append(_NewsItem(source=source_id, title=str(title), url=str(link), summary=str(summary)))
                if len(out) >= self.max_headlines:
                    break
            if len(out) >= self.max_headlines:
                break
        for item in out:
            yield item


def _matches_ticker(ticker: str, text: str) -> bool:
    if not ticker:
        return False
    pattern = re.compile(rf"\b{re.escape(ticker.upper())}\b", re.IGNORECASE)
    return bool(pattern.search(text or ""))


def _clip(value: Any, lo: float, hi: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = 0.0
    return max(lo, min(hi, v))


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _parse_advisor_json(text: str) -> dict[str, Any]:
    """Tolerantly extract the first JSON object in ``text``."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_RE.search(text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}


__all__ = ["NewsSentimentAgent", "_parse_advisor_json"]
