"""NotebookLM-backed news context for NewsSentimentAgent.

Fetches cached NotebookLM stock news analysis from iran-war-notelm API
and injects notebook_analysis + headlines into the advisor context.

Feature flag: NOTEBOOKLM_NEWS_MODE=off|cache|on|1|true (default: off)
API base:     NOTEBOOKLM_NEWS_API_BASE (default: http://127.0.0.1:8088)
Timeout:      NOTEBOOKLM_NEWS_TIMEOUT_SEC (default: 3.0)
"""

from __future__ import annotations

import logging
import os
import urllib.parse
from typing import Any

_LOGGER = logging.getLogger("advisors.notebooklm_news")

_ENABLED_VALUES = {"1", "true", "on", "cache"}
DEFAULT_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_TIMEOUT_SEC = 3.0


def _enabled() -> bool:
    return os.environ.get("NOTEBOOKLM_NEWS_MODE", "off").lower() in _ENABLED_VALUES


def _base_url() -> str:
    return os.environ.get("NOTEBOOKLM_NEWS_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("NOTEBOOKLM_NEWS_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
    except ValueError:
        return DEFAULT_TIMEOUT_SEC


def fetch_notebooklm_analysis(
    ticker: str,
    market: str = "US",
    timeout_sec: float | None = None,
) -> dict[str, Any] | None:
    """Pull cached NotebookLM analysis for *ticker* from iran-war-notelm API.

    Returns None if the feature is disabled, the API is unreachable, or the
    response schema is unexpected. Callers must handle None gracefully.
    """
    if not _enabled():
        return None

    qs = urllib.parse.urlencode({"symbol": ticker, "market": market})
    url = f"{_base_url()}/api/stock-news/notebook-analysis?{qs}"
    t = timeout_sec if timeout_sec is not None else _timeout()

    try:
        import httpx
        with httpx.Client(timeout=t) as client:
            resp = client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        _LOGGER.warning("[NotebookLM] API call failed for %s (%s): %s", ticker, market, exc)
        return None

    if payload.get("schema_version") != "notebook_stock_analysis.v1":
        _LOGGER.warning(
            "[NotebookLM] unexpected schema_version for %s: %r",
            ticker,
            payload.get("schema_version"),
        )
        return None
    return payload


def _to_headlines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert API payload sources to _NewsItem-compatible dicts."""
    analysis = payload.get("analysis") or {}
    out: list[dict[str, Any]] = []
    for s in payload.get("sources") or []:
        out.append({
            "source": s.get("source") or "notebooklm",
            "title": s.get("title") or "",
            "url": s.get("url") or "",
            "summary": analysis.get("summary") or "",
            "published_at": s.get("published_at"),
            "ticker_relevance": s.get("relevance"),
            "notebook_source_id": s.get("notebook_source_id"),
            "source_id": s.get("source_id"),
        })
    return out


def enrich_context_with_notebooklm(
    ticker: str,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    """Return a new context dict enriched with NotebookLM analysis.

    Injects:
    - ctx["notebook_analysis"] — full structured analysis dict
    - ctx["headlines"]         — source-backed headline list (prepended)
    - ctx["notebooklm_enriched"] — bool
    - ctx["notebooklm_count"]    — int

    On failure (disabled mode, API error), returns ctx unchanged with
    notebooklm_enriched=False and notebooklm_count=0.
    """
    market = str(ctx.get("market") or "US")
    payload = fetch_notebooklm_analysis(ticker, market=market)

    if not payload:
        return {
            **ctx,
            "notebooklm_enriched": False,
            "notebooklm_count": 0,
        }

    analysis = payload.get("analysis") or {}
    notebook_analysis = {
        "summary": analysis.get("summary"),
        "bullish_factors": list(analysis.get("bullish_factors") or []),
        "bearish_factors": list(analysis.get("bearish_factors") or []),
        "ticker_relevance": analysis.get("ticker_relevance"),
        "sentiment": analysis.get("sentiment"),
        "sentiment_score": analysis.get("sentiment_score"),
        "market_impact": analysis.get("market_impact"),
        "confidence": analysis.get("confidence"),
        "recommended_llm_instruction": analysis.get("recommended_llm_instruction"),
        "notebook": payload.get("notebook") or {},
        "as_of": payload.get("as_of"),
    }

    headlines = _to_headlines(payload)
    existing = list(ctx.get("headlines") or [])

    _LOGGER.info(
        "[NotebookLM] enriched %s: sentiment=%s confidence=%.2f sources=%d",
        ticker,
        analysis.get("sentiment", "?"),
        float(analysis.get("confidence") or 0),
        len(headlines),
    )

    return {
        **ctx,
        "notebook_analysis": notebook_analysis,
        "headlines": headlines + existing if headlines else existing,
        "notebooklm_enriched": True,
        "notebooklm_count": len(headlines),
    }
