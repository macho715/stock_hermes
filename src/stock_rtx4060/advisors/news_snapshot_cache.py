"""iran-war-notelm 뉴스 스냅샷 캐시 레이어 (다중 에이전트 시뮬레이션 권장 방안).

GitHub raw URL에서 stock_news_snapshot.json을 5분마다 폴링하여
in-memory cache로 유지한다. NewsSentimentAgent의 context['headlines']에
주입하여 기존 코드 변경 최소화.

Feature flag: NEWS_SNAPSHOT_URL 환경변수 설정 시 활성화 (미설정 시 off).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SNAPSHOT_URL_DEFAULT = (
    "https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json"
)
POLL_INTERVAL_SEC = int(os.environ.get("NEWS_SNAPSHOT_POLL_SEC", "300"))    # 5분 폴링
STALE_THRESHOLD_SEC = int(os.environ.get("NEWS_SNAPSHOT_STALE_SEC", "3600"))  # 1시간


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TickerSentiment:
    ticker: str
    sentiment_score: float
    sentiment_label: str    # "bullish" | "neutral" | "bearish"
    confidence: float
    headline: str
    ai_summary: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    geo_risk_tags: list[str] = field(default_factory=list)
    updated_at: str = ""
    is_stale: bool = False
    error: Optional[str] = None

    def to_headlines(self) -> list[dict[str, Any]]:
        """NewsSentimentAgent.context['headlines'] 형식으로 변환.

        Returns list of {source, title, url, summary} dicts.
        """
        items: list[dict[str, Any]] = []
        if self.headline:
            items.append({
                "source": "NotebookLM-Snapshot",
                "title": self.headline,
                "url": "",
                "summary": self.ai_summary,
            })
        for src in self.sources[:4]:
            items.append({
                "source": src.get("source_name", "news"),
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "summary": src.get("summary", ""),
            })
        return items


# ---------------------------------------------------------------------------
# Cache class
# ---------------------------------------------------------------------------

class NewsSentimentSnapshotCache:
    """스레드 안전 in-memory 캐시. 백그라운드 폴링으로 자동 갱신.

    사용법:
        cache = NewsSentimentSnapshotCache()
        cache.start()                            # 앱 시작 시 1회
        ctx = cache.inject_into_context(ticker, ctx)   # analyze() 직전
    """

    def __init__(self, snapshot_url: str = SNAPSHOT_URL_DEFAULT) -> None:
        self._url = snapshot_url
        self._cache: dict[str, TickerSentiment] = {}
        self._last_fetched_at: Optional[float] = None
        self._lock = threading.RLock()
        self._started = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """앱 시작 시 1회 호출. 첫 fetch 완료 후 백그라운드 폴링 시작."""
        if self._started:
            return
        self._fetch_and_update()
        t = threading.Thread(
            target=self._poll_loop, daemon=True, name="NewsSnapshotPoller"
        )
        t.start()
        self._started = True
        logger.info(
            "[SnapshotCache] 시작. %d 종목 로드, poll=%ds",
            len(self._cache), POLL_INTERVAL_SEC,
        )

    def get(self, ticker: str) -> Optional[TickerSentiment]:
        """종목별 최신 감성 데이터 반환. 없거나 stale이면 is_stale=True."""
        with self._lock:
            clean = ticker.upper().replace(".KS", "").replace(".KQ", "")
            # Try exact match first, then without suffix
            entry = self._cache.get(ticker.upper()) or self._cache.get(clean)
            if entry and self._is_global_stale():
                return TickerSentiment(**{**entry.__dict__, "is_stale": True})
            return entry

    def inject_into_context(self, ticker: str, context: dict[str, Any]) -> dict[str, Any]:
        """context dict에 notebook_analysis를 주입.

        Plan 정정(2026-05-30): ``context["headlines"]`` 감성분석 수준이 아니라
        ``context["notebook_analysis"]`` source-grounded 분석 결과를 주입한다.
        기존 RSS headlines는 raw evidence로 남기고 notebook_analysis가 상위 판단 근거가 됨.
        entry 없으면 context 그대로 반환 → 기존 RSS advisor 경로 fallback.
        """
        entry = self.get(ticker)
        if entry is None:
            return context

        enriched = dict(context)

        # [핵심 변경] notebook_analysis 키로 구조화된 분석 결과 주입
        enriched["notebook_analysis"] = {
            "summary": entry.ai_summary or entry.headline,
            "bullish_factors": [f for f in entry.geo_risk_tags if not f.startswith("-")],
            "bearish_factors": [f[1:].strip() for f in entry.geo_risk_tags if f.startswith("-")],
            "ticker_relevance": entry.confidence,
            "sentiment_score": entry.sentiment_score,
            "market_impact": _sentiment_to_impact(entry.sentiment_score),
            "confidence": entry.confidence,
            "recommended_llm_instruction": _build_instruction(entry),
            "source_ids": [s.get("url", "") for s in entry.sources[:3]],
            "notebook_id": "",
            "as_of": entry.updated_at,
            "is_stale": entry.is_stale,
        }

        # raw headlines는 참고 데이터로 낮춤 (기존 RSS headlines와 병합하지 않음)
        if entry.headline:
            enriched.setdefault("headlines", [])
            enriched["headlines"] = entry.to_headlines() + list(enriched.get("headlines") or [])

        enriched["notebooklm_snapshot_enriched"] = True
        enriched["notebooklm_snapshot_stale"] = entry.is_stale
        return enriched

    def status(self) -> dict[str, Any]:
        """헬스체크용 현황 반환."""
        with self._lock:
            age = (time.time() - self._last_fetched_at) if self._last_fetched_at else None
            return {
                "tickers": len(self._cache),
                "last_fetched_ago_sec": round(age, 1) if age else None,
                "stale": self._is_global_stale(),
                "url": self._url,
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        while True:
            time.sleep(POLL_INTERVAL_SEC)
            try:
                self._fetch_and_update()
            except Exception as exc:
                logger.warning("[SnapshotCache] poll 실패: %s", exc)

    def _fetch_and_update(self) -> None:
        try:
            with urllib.request.urlopen(self._url, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
        except Exception as exc:
            logger.error("[SnapshotCache] fetch 실패: %s (이전 캐시 유지)", exc)
            return

        try:
            data = json.loads(raw)
            new_cache: dict[str, TickerSentiment] = {}
            for ticker_key, entry in data.get("tickers", {}).items():
                ts = TickerSentiment(
                    ticker=entry.get("ticker", ticker_key),
                    sentiment_score=float(entry.get("sentiment_score", 0.0)),
                    sentiment_label=str(entry.get("sentiment_label", "neutral")),
                    confidence=float(entry.get("confidence", 0.0)),
                    headline=str(entry.get("headline", "")),
                    ai_summary=str(entry.get("ai_summary", "")),
                    sources=list(entry.get("sources", [])),
                    geo_risk_tags=list(entry.get("geo_risk_tags", [])),
                    updated_at=str(entry.get("updated_at", "")),
                    error=entry.get("error"),
                )
                new_cache[ticker_key.upper()] = ts
            with self._lock:
                self._cache = new_cache
                self._last_fetched_at = time.time()
            logger.info("[SnapshotCache] 갱신 완료: %d 종목", len(new_cache))
        except Exception as exc:
            logger.error("[SnapshotCache] 파싱 실패: %s", exc)

    def _is_global_stale(self) -> bool:
        return (
            self._last_fetched_at is None
            or (time.time() - self._last_fetched_at) > STALE_THRESHOLD_SEC
        )


# ---------------------------------------------------------------------------
# Helper functions for notebook_analysis construction
# ---------------------------------------------------------------------------

def _sentiment_to_impact(score: float) -> str:
    if score >= 0.7:   return "HIGH"
    if score >= 0.4:   return "MEDIUM_HIGH"
    if score >= 0.1:   return "MEDIUM"
    if score >= -0.1:  return "LOW"
    if score >= -0.4:  return "MEDIUM"
    if score >= -0.7:  return "MEDIUM_HIGH"
    return "HIGH"


def _build_instruction(entry: "TickerSentiment") -> str:
    if entry.sentiment_score >= 0.5:
        return f"긍정 편향으로 처리. 신뢰도 {entry.confidence:.0%}. 기술지표 교차 검증 권장."
    if entry.sentiment_score <= -0.5:
        return f"부정 편향으로 처리. 신뢰도 {entry.confidence:.0%}. 하방 리스크 중점 검토."
    return f"중립 처리. 신뢰도 {entry.confidence:.0%}. 기술지표 중심 판단 권장."


# ---------------------------------------------------------------------------
# Global singleton (opt-in via NEWS_SNAPSHOT_URL)
# ---------------------------------------------------------------------------

_snapshot_url = os.environ.get("NEWS_SNAPSHOT_URL", "")
if _snapshot_url:
    _default_cache: Optional[NewsSentimentSnapshotCache] = NewsSentimentSnapshotCache(_snapshot_url)
else:
    _default_cache = None


def get_default_cache() -> Optional[NewsSentimentSnapshotCache]:
    """Return the global cache if NEWS_SNAPSHOT_URL is configured."""
    return _default_cache
