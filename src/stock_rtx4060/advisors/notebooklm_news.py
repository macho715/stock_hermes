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
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger("advisors.notebooklm_news")

_ENABLED_VALUES = {"1", "true", "on", "cache"}
_DISABLED_VALUES = {"0", "false", "off", "no"}
DEFAULT_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_TIMEOUT_SEC = 3.0
DEFAULT_LOCAL_FALLBACK_TTL_SEC = 900
DEFAULT_LOCAL_CACHE_DIR = "reports/notelm_fallback_cache"

_BULLISH_TERMS = (
    "beat", "beats", "growth", "raises", "raised", "upgrade", "upgraded",
    "strong", "record", "surge", "rally", "bullish", "profit", "revenue",
    "demand", "ai", "expands", "partnership", "approval", "buyback",
)
_BEARISH_TERMS = (
    "miss", "misses", "cut", "cuts", "downgrade", "downgraded", "weak",
    "probe", "lawsuit", "risk", "falls", "decline", "bearish", "loss",
    "tariff", "delay", "slump", "warning", "recall", "fine", "pressure",
)


def _enabled() -> bool:
    return os.environ.get("NOTEBOOKLM_NEWS_MODE", "off").lower() in _ENABLED_VALUES


def _base_url() -> str:
    return os.environ.get("NOTEBOOKLM_NEWS_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def _timeout() -> float:
    try:
        return float(os.environ.get("NOTEBOOKLM_NEWS_TIMEOUT_SEC", str(DEFAULT_TIMEOUT_SEC)))
    except ValueError:
        return DEFAULT_TIMEOUT_SEC


def _local_fallback_enabled() -> bool:
    value = os.environ.get("NOTEBOOKLM_NEWS_LOCAL_FALLBACK", "true").strip().lower()
    return value not in _DISABLED_VALUES


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _local_cache_dir() -> Path:
    return Path(os.environ.get("NOTEBOOKLM_NEWS_LOCAL_CACHE_DIR", DEFAULT_LOCAL_CACHE_DIR))


def _local_cache_ttl_sec() -> int:
    raw = os.environ.get("NOTEBOOKLM_NEWS_LOCAL_FALLBACK_TTL_SEC", str(DEFAULT_LOCAL_FALLBACK_TTL_SEC))
    try:
        return max(0, int(float(raw)))
    except ValueError:
        return DEFAULT_LOCAL_FALLBACK_TTL_SEC


def _local_cache_path(ticker: str, market: str) -> Path:
    clean_ticker = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in ticker.upper())
    clean_market = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in market.upper())
    return _local_cache_dir() / clean_market / f"{clean_ticker}.json"


def _parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_local_fallback_cache(ticker: str, market: str) -> dict[str, Any] | None:
    path = _local_cache_path(ticker, market)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if payload.get("schema_version") != "notebook_stock_analysis.v1":
        return None
    if str(payload.get("symbol") or "").upper() != ticker.upper():
        return None
    if str(payload.get("market") or "").upper() != market.upper():
        return None

    generated_at = ((payload.get("cache") or {}).get("generated_at")) or payload.get("as_of")
    generated_dt = _parse_iso(generated_at)
    if generated_dt is None:
        return None
    if generated_dt.tzinfo is None:
        generated_dt = generated_dt.replace(tzinfo=UTC)

    ttl = _local_cache_ttl_sec()
    age = (datetime.now(UTC) - generated_dt.astimezone(UTC)).total_seconds()
    if ttl > 0 and age > ttl:
        return None

    cached = dict(payload)
    cache_meta = dict(cached.get("cache") or {})
    cache_meta["status"] = "LOCAL_CACHE_HIT"
    cache_meta["path"] = str(path)
    cache_meta["age_seconds"] = round(max(age, 0.0), 3)
    cached["cache"] = cache_meta
    return cached


def _write_local_fallback_cache(ticker: str, market: str, payload: dict[str, Any]) -> None:
    path = _local_cache_path(ticker, market)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:
        _LOGGER.info("[Notelm] local fallback cache write failed for %s:%s: %s", market, ticker, exc)


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
            "source_type": s.get("source_type") or payload.get("analysis", {}).get("analysis_source"),
        })
    return out


def _sentiment_label(score: Any) -> str:
    try:
        numeric = float(score)
    except (TypeError, ValueError):
        return "neutral"
    if numeric >= 0.2:
        return "bullish"
    if numeric <= -0.2:
        return "bearish"
    return "neutral"


def _maybe_apply_openai_analysis(ticker: str, market: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Optionally refine NotebookLM/Notelm analysis through OpenAI.

    OpenAI is enabled only when ``LLM_ADVISOR_PROVIDER=openai``. If the API key
    is missing or the call fails, the original payload remains the source of
    truth and the error is attached for observability.
    """
    try:
        from .openai_client import get_openai_analyzer

        analyzer = get_openai_analyzer()
    except Exception as exc:
        _LOGGER.info("[OpenAI] analyzer unavailable for %s: %s", ticker, exc)
        return payload

    if analyzer is None:
        return payload

    analysis = dict(payload.get("analysis") or {})
    headlines = _to_headlines(payload)
    headline_titles = [str(item.get("title") or "").strip() for item in headlines if item.get("title")]
    notebook = payload.get("notebook") or {}
    source_ids = list(notebook.get("source_ids") or [])
    result = analyzer.analyze(
        ticker=ticker,
        market=market,
        headlines=headline_titles,
        notebook_summary=str(analysis.get("summary") or ""),
        source_ids=source_ids,
        company_name=str(payload.get("company_name") or ""),
    )

    if result.get("error"):
        merged = dict(payload)
        merged_analysis = dict(analysis)
        merged_analysis["openai_error"] = result.get("error")
        merged_analysis["openai_analysis_source"] = "openai_api"
        merged["analysis"] = merged_analysis
        return merged

    merged_analysis = {
        **analysis,
        "summary": result.get("summary") or analysis.get("summary"),
        "bullish_factors": list(result.get("bullish_factors") or analysis.get("bullish_factors") or []),
        "bearish_factors": list(result.get("bearish_factors") or analysis.get("bearish_factors") or []),
        "ticker_relevance": result.get("ticker_relevance", analysis.get("ticker_relevance")),
        "sentiment": _sentiment_label(result.get("sentiment_score")),
        "sentiment_score": result.get("sentiment_score", analysis.get("sentiment_score")),
        "market_impact": result.get("market_impact") or analysis.get("market_impact"),
        "confidence": result.get("confidence", analysis.get("confidence")),
        "recommended_llm_instruction": result.get("recommended_llm_instruction")
        or analysis.get("recommended_llm_instruction"),
        "analysis_source": "openai_api",
        "source_labels": list(analysis.get("source_labels") or []) + ["OpenAI"],
        "openai_model": result.get("model"),
        "openai_provider": result.get("provider"),
        "openai_enriched_at": _now_iso(),
    }
    merged = dict(payload)
    merged["analysis"] = merged_analysis
    merged["openai_analysis"] = result
    return merged


@lru_cache(maxsize=128)
def _fetch_yfinance_news(ticker: str, limit: int = 8) -> list[dict[str, Any]]:
    clean = str(ticker or "").strip().upper()
    if not clean:
        return []
    try:
        import yfinance as yf

        raw_items = yf.Ticker(clean).news or []
    except Exception as exc:
        _LOGGER.info("[Notelm] local fallback news unavailable for %s: %s", clean, exc)
        return []

    rows: list[dict[str, Any]] = []
    for item in raw_items[:limit]:
        if not isinstance(item, dict):
            continue
        content = item.get("content") if isinstance(item.get("content"), dict) else item
        provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
        canonical = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
        click = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
        title = content.get("title") or item.get("title")
        if not title:
            continue
        rows.append({
            "title": str(title),
            "url": canonical.get("url") or click.get("url") or item.get("link") or "",
            "source": provider.get("displayName") or item.get("publisher") or "Yahoo Finance",
            "published_at": content.get("pubDate") or content.get("displayTime") or item.get("providerPublishTime"),
            "summary": content.get("summary") or content.get("description") or "",
            "relevance": 1.0,
            "source_type": "yfinance.news",
        })
    return rows


def _term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term in lower]


def _build_notelm_fallback_payload(ticker: str, market: str) -> dict[str, Any] | None:
    """Build a Notelm-style local rule-based analysis when the API is down.

    This mirrors iran-war-notelm's documented fallback principle: NotebookLM
    query first, deterministic keyword scoring when the query path fails.
    """
    if not _local_fallback_enabled():
        return None

    cached = _read_local_fallback_cache(ticker, market)
    if cached:
        return cached

    articles = _fetch_yfinance_news(ticker)
    if not articles:
        return None

    bullish_factors: list[str] = []
    bearish_factors: list[str] = []
    score = 0
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        bull_hits = _term_hits(text, _BULLISH_TERMS)
        bear_hits = _term_hits(text, _BEARISH_TERMS)
        score += len(bull_hits) - len(bear_hits)
        if bull_hits:
            bullish_factors.append(str(article.get("title") or "").strip())
        if bear_hits:
            bearish_factors.append(str(article.get("title") or "").strip())

    sentiment_score = max(-1.0, min(1.0, score / max(len(articles), 1)))
    if sentiment_score >= 0.2:
        sentiment = "bullish"
    elif sentiment_score <= -0.2:
        sentiment = "bearish"
    elif bullish_factors and bearish_factors:
        sentiment = "mixed"
    else:
        sentiment = "neutral"

    abs_score = abs(sentiment_score)
    market_impact = "HIGH" if abs_score >= 0.75 else "MEDIUM_HIGH" if abs_score >= 0.45 else "MEDIUM" if abs_score >= 0.15 else "LOW"
    confidence = round(min(0.85, 0.35 + min(len(articles), 8) * 0.05 + abs_score * 0.20), 2)
    if not bullish_factors and sentiment in {"bullish", "neutral", "mixed"}:
        bullish_factors = [str(a.get("title") or "").strip() for a in articles[:3] if a.get("title")]
    if not bearish_factors and sentiment in {"bearish", "neutral", "mixed"}:
        bearish_factors = [str(a.get("title") or "").strip() for a in articles[-2:] if a.get("title")]

    summary = (
        f"Notelm local fallback analyzed {len(articles)} source-backed headlines for "
        f"{ticker.upper()} because the NotebookLM API was unavailable."
    )
    now = _now_iso()
    sources = []
    for idx, article in enumerate(articles, start=1):
        sources.append({
            "source_id": f"notelm_yfinance_{idx}",
            "notebook_source_id": f"notelm_local_{idx}",
            "title": article.get("title"),
            "url": article.get("url"),
            "source": article.get("source"),
            "published_at": article.get("published_at"),
            "relevance": article.get("relevance", 1.0),
            "source_type": article.get("source_type", "yfinance.news"),
        })
    payload = {
        "schema_version": "notebook_stock_analysis.v1",
        "symbol": ticker.upper(),
        "market": market.upper(),
        "as_of": now,
        "notebook": {
            "notebook_id": "notelm-local-fallback",
            "source_ids": [s["source_id"] for s in sources],
            "source_count": len(sources),
            "notebook_url": None,
        },
        "analysis": {
            "summary": summary,
            "bullish_factors": bullish_factors[:3],
            "bearish_factors": bearish_factors[:2],
            "ticker_relevance": 1.0,
            "sentiment": sentiment,
            "sentiment_score": round(sentiment_score, 3),
            "market_impact": market_impact,
            "confidence": confidence,
            "recommended_llm_instruction": "Use as source-backed Notelm fallback only; verify against price, risk, and model gates.",
            "analysis_source": "notelm_fallback",
            "source_labels": [str(s.get("source") or "YFinance") for s in sources],
        },
        "sources": sources,
        "cache": {
            "status": "LOCAL_FALLBACK",
            "ttl_seconds": 0,
            "generated_at": now,
        },
        "errors": ["notebooklm_api_unavailable"],
    }
    _write_local_fallback_cache(ticker, market, payload)
    return payload


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
    if not _enabled():
        return {
            **ctx,
            "notebooklm_enriched": False,
            "notebooklm_count": 0,
        }

    market = str(ctx.get("market") or "US")
    payload = fetch_notebooklm_analysis(ticker, market=market)
    if not payload:
        payload = _build_notelm_fallback_payload(ticker, market)

    if not payload:
        return {
            **ctx,
            "notebooklm_enriched": False,
            "notebooklm_count": 0,
        }

    payload = _maybe_apply_openai_analysis(ticker, market, payload)
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
        "analysis_source": analysis.get("analysis_source") or "notebooklm",
        "source_labels": list(analysis.get("source_labels") or []),
        "notebook": payload.get("notebook") or {},
        "as_of": payload.get("as_of"),
        "cache_status": (payload.get("cache") or {}).get("status"),
        "openai_model": analysis.get("openai_model"),
        "openai_provider": analysis.get("openai_provider"),
        "openai_error": analysis.get("openai_error"),
        "openai_enriched_at": analysis.get("openai_enriched_at"),
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
