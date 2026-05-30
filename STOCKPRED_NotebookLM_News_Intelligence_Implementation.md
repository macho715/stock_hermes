# STOCKPRED × NotebookLM News Intelligence Layer 구현 문서

문서일: 2026-05-30
대상 Repo: `macho715/stock_1901`, `macho715/iran-war-notelm`
판정: NOT DONE
목표: 실시간 뉴스 수집 → NotebookLM source 저장 → NotebookLM 분석 → STOCKPRED 주가·기술지표·LLM advisor 반영

---

## 1. 검증 결과 요약

### 1.1 현재 구현 상태

| 영역 | 현재 상태 | 판정 |
|---|---|---|
| `iran-war-notelm` 뉴스 수집 | UAE/Iran 위기 뉴스 수집, dedup, NotebookLM 업로드 파이프라인 존재 | PARTIAL |
| `iran-war-notelm` NotebookLM 분석 | UAE safety analyst prompt 기반 threat 분석 존재 | PARTIAL |
| `iran-war-notelm` 주식용 API | `/api/stock-news/notebook-analysis` 없음 | NOT DONE |
| `stock_1901` NotebookLM adapter | `src/stock_rtx4060/advisors/notebooklm_news.py` 파일 없음 | NOT DONE |
| `stock_1901` orchestrator hook | optional import 시도는 존재하나 ImportError fallback만 작동 | PARTIAL |
| `NewsSentimentAgent` 주입 | `context["headlines"]` override는 존재 | PARTIAL |
| `notebook_analysis` 주입 | 없음 | NOT DONE |
| STOCKPRED dashboard 표시 | `advisor_score`, `advisor_rationale` 표시만 존재 | PARTIAL |
| source traceability | `source_id`, `notebook_source_id` stock advisor 결과 저장 없음 | NOT DONE |

### 1.2 결론

구현된 것은 “자리”와 “기존 UAE safety NotebookLM 파이프라인”이다.
아직 구현되지 않은 것은 “주식 ticker별 NotebookLM source 저장/분석 API”와 “STOCKPRED advisor 주입 adapter”다.

---

## 2. 목표 아키텍처

```text
[News Scraper]
  - ticker별 실시간 뉴스 수집
  - 중복 제거
  - relevance scoring
        ↓
[NotebookLM Source Writer]
  - webContent/textContent source 저장
  - notebook_id/source_id 기록
        ↓
[NotebookLM Stock Analyzer]
  - source-grounded 분석
  - bullish/bearish/market impact/confidence 생성
        ↓
[iran-war-notelm API]
  GET /api/stock-news/notebook-analysis?symbol=AAPL&market=US
  - 캐시된 분석 JSON 제공
        ↓
[stock_1901 notebooklm_news.py]
  - API pull
  - context["notebook_analysis"] 주입
  - context["headlines"] 보조 주입
        ↓
[stock_1901 Orchestrator]
  - price/volume/technical indicators + NotebookLM analysis 결합
        ↓
[STOCKPRED Dashboard]
  - advisor_score
  - advisor_rationale
  - NotebookLM impact/source count/confidence
```

---

## 3. 구현 원칙

1. Dashboard가 NotebookLM을 직접 호출하지 않는다.
2. NotebookLM 업로드·분석은 `iran-war-notelm`에서 비동기/캐시로 처리한다.
3. `stock_1901`은 캐시 API만 읽는다.
4. API 실패 시 추천 엔진은 중단하지 않고 neutral/no-data로 degrade한다.
5. LLM advisor 결과는 deterministic score를 임의로 상향하지 않는다.
6. `source_id`, `notebook_source_id`, `source_count`, `as_of`는 반드시 audit 가능하게 보존한다.

---

## 4. PR 구성

## PR-1: `iran-war-notelm` — 주식 뉴스 NotebookLM API 추가

### 4.1 신규 파일

```text
iran-war-uae-monitor/src/iran_monitor/stock_news/
  __init__.py
  models.py
  scraper.py
  dedupe.py
  notebooklm_stock.py
  analyzer.py
  cache.py
  api.py
```

### 4.2 `models.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Sentiment = Literal["bullish", "bearish", "neutral", "mixed"]
MarketImpact = Literal["LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH"]


@dataclass(frozen=True)
class StockNewsItem:
    symbol: str
    market: str
    title: str
    url: str
    source: str
    published_at: str | None = None
    summary: str = ""
    ticker_relevance: float = 0.0
    hash_id: str = ""


@dataclass(frozen=True)
class NotebookSourceRef:
    source_id: str
    notebook_source_id: str | None
    title: str
    url: str
    source: str
    published_at: str | None
    relevance: float


@dataclass(frozen=True)
class StockNotebookAnalysis:
    summary: str
    bullish_factors: list[str]
    bearish_factors: list[str]
    ticker_relevance: float
    sentiment: Sentiment
    sentiment_score: float
    market_impact: MarketImpact
    confidence: float
    recommended_llm_instruction: str
```

### 4.3 `scraper.py`

MVP는 기존 RSS/httpx 기반으로 시작한다.

```python
import hashlib
from .models import StockNewsItem

DEFAULT_STOCK_FEEDS = {
    "reuters_business": "https://www.reutersagency.com/feed/?best-topics=business-finance",
    "marketwatch": "https://www.marketwatch.com/rss/topstories",
    "sec_8k": "SEC_EDGAR_OPTIONAL",
}


def _hash(symbol: str, title: str, url: str) -> str:
    raw = f"{symbol}|{title}|{url}".strip().lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def score_ticker_relevance(symbol: str, text: str) -> float:
    upper = text.upper()
    sym = symbol.upper().replace(".KS", "").replace(".KQ", "")
    if f" {sym} " in f" {upper} ":
        return 1.0
    return 0.35 if sym in upper else 0.0


async def scrape_stock_news(symbol: str, market: str = "US", limit: int = 12) -> list[StockNewsItem]:
    # TODO: feedparser/httpx 구현
    # 테스트에서는 fixture 기반으로 검증
    return []
```

### 4.4 `notebooklm_stock.py`

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

NOTEBOOK_TITLE_PREFIX = "STOCKPRED News Intelligence"


def build_source_text(symbol: str, market: str, articles: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"# {symbol} {market} Stock News Update — {now}", ""]
    for a in articles:
        lines.append(f"## {a['title']}")
        lines.append(f"- Source: {a.get('source', '')}")
        lines.append(f"- URL: {a.get('url', '')}")
        lines.append(f"- Published: {a.get('published_at', '')}")
        lines.append(f"- Summary: {a.get('summary', '')}")
        lines.append("")
    return "\n".join(lines)


def get_or_create_stock_notebook(client: Any, symbol: str, market: str) -> str:
    title = f"{NOTEBOOK_TITLE_PREFIX} — {market}:{symbol}"
    # 기존 iran_monitor.app의 _get_or_create_notebook 패턴을 stock 전용으로 분리
    raise NotImplementedError


def upload_stock_news_source(client: Any, notebook_id: str, symbol: str, market: str, articles: list[dict]) -> dict:
    content = build_source_text(symbol, market, articles)
    title = f"{symbol} stock news update"
    source = client.add_text_source(notebook_id, content, title=title)
    source_id = getattr(source, "id", None) or getattr(source, "source_id", None) or str(source)
    client.wait_for_source_ready(notebook_id, source_id)
    return {
        "notebook_id": notebook_id,
        "source_id": source_id,
        "notebook_source_id": source_id,
    }
```

### 4.5 `analyzer.py`

NotebookLM이 반환해야 하는 JSON 스키마를 고정한다.

```python
STOCK_ANALYSIS_PROMPT = """
You are a stock market news analyst.

Analyze the notebook sources for {symbol} ({market}).
Return ONLY valid JSON with keys:
summary, bullish_factors, bearish_factors, ticker_relevance,
sentiment, sentiment_score, market_impact, confidence,
recommended_llm_instruction.

Rules:
- sentiment must be bullish|bearish|neutral|mixed
- sentiment_score must be -1.0..1.0
- ticker_relevance and confidence must be 0.0..1.0
- market_impact must be LOW|MEDIUM|MEDIUM_HIGH|HIGH
- Do not invent facts not grounded in sources.
- If evidence is weak, lower confidence.
"""


def analyze_stock_news_with_notebooklm(client, notebook_id: str, symbol: str, market: str) -> dict:
    prompt = STOCK_ANALYSIS_PROMPT.format(symbol=symbol, market=market)
    response = client.query(notebook_id, prompt, timeout=90)
    answer = str(response.get("answer", "")).strip()
    return parse_json_payload(answer)
```

### 4.6 `cache.py`

```python
import json
from datetime import datetime, timedelta, UTC
from pathlib import Path

CACHE_DIR = Path("storage/stock_news_cache")
DEFAULT_TTL_SEC = 900


def cache_path(symbol: str, market: str) -> Path:
    return CACHE_DIR / market.upper() / f"{symbol.upper()}.json"


def read_cache(symbol: str, market: str, ttl_sec: int = DEFAULT_TTL_SEC) -> dict | None:
    path = cache_path(symbol, market)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    generated = datetime.fromisoformat(data["cache"]["generated_at"])
    if datetime.now(UTC) - generated > timedelta(seconds=ttl_sec):
        return None
    return data


def write_cache(symbol: str, market: str, payload: dict) -> None:
    path = cache_path(symbol, market)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

### 4.7 `api.py`

FastAPI가 없다면 추가한다. 이미 서버가 있으면 router만 붙인다.

```python
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/api/stock-news/notebook-analysis")
async def get_stock_news_notebook_analysis(
    symbol: str = Query(..., min_length=1),
    market: str = "US",
    refresh: bool = False,
):
    # 1) cache hit
    # 2) scrape
    # 3) upload NotebookLM source
    # 4) query NotebookLM analysis
    # 5) cache write
    # 6) return schema_version=notebook_stock_analysis.v1
    raise NotImplementedError
```

### 4.8 API 응답 계약

```json
{
  "schema_version": "notebook_stock_analysis.v1",
  "symbol": "AAPL",
  "market": "US",
  "as_of": "2026-05-30T12:00:00+04:00",
  "notebook": {
    "notebook_id": "nb_xxx",
    "source_ids": ["src_001"],
    "source_count": 12,
    "notebook_url": "https://notebooklm.google.com/notebook/nb_xxx"
  },
  "analysis": {
    "summary": "Source-grounded stock news analysis.",
    "bullish_factors": ["..."],
    "bearish_factors": ["..."],
    "ticker_relevance": 0.87,
    "sentiment": "bullish",
    "sentiment_score": 0.42,
    "market_impact": "MEDIUM_HIGH",
    "confidence": 0.78,
    "recommended_llm_instruction": "Treat news impact as moderately bullish; verify against price momentum."
  },
  "sources": [
    {
      "source_id": "src_001",
      "notebook_source_id": "src_001",
      "title": "News title",
      "url": "https://example.com/news",
      "source": "Reuters",
      "published_at": "2026-05-30T08:00:00Z",
      "relevance": 0.91
    }
  ],
  "cache": {
    "status": "MISS",
    "ttl_seconds": 900,
    "generated_at": "2026-05-30T12:00:00+04:00"
  },
  "errors": []
}
```

---

## PR-2: `stock_1901` — NotebookLM adapter + context injection

### 5.1 신규 파일

```text
stock_1901/src/stock_rtx4060/advisors/notebooklm_news.py
```

### 5.2 Adapter 구현

```python
from __future__ import annotations

import os
import urllib.parse
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_TIMEOUT_SEC = 3.0


def _enabled() -> bool:
    return os.environ.get("NOTEBOOKLM_NEWS_MODE", "off").lower() in {"1", "true", "on", "cache"}


def _base_url() -> str:
    return os.environ.get("NOTEBOOKLM_NEWS_API_BASE", DEFAULT_BASE_URL).rstrip("/")


def fetch_notebooklm_analysis(
    ticker: str,
    market: str = "US",
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
) -> dict[str, Any] | None:
    if not _enabled():
        return None

    qs = urllib.parse.urlencode({"symbol": ticker, "market": market})
    url = f"{_base_url()}/api/stock-news/notebook-analysis?{qs}"

    try:
        with httpx.Client(timeout=timeout_sec) as client:
            resp = client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception:
        return None

    if payload.get("schema_version") != "notebook_stock_analysis.v1":
        return None
    return payload


def _to_headlines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    analysis = payload.get("analysis") or {}
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


def enrich_context_with_notebooklm(ticker: str, ctx: dict[str, Any]) -> dict[str, Any]:
    market = str(ctx.get("market") or "US")
    payload = fetch_notebooklm_analysis(ticker, market=market)

    if not payload:
        ctx.setdefault("notebooklm_enriched", False)
        ctx.setdefault("notebooklm_count", 0)
        return ctx

    analysis = payload.get("analysis") or {}
    ctx["notebook_analysis"] = {
        "summary": analysis.get("summary"),
        "bullish_factors": analysis.get("bullish_factors") or [],
        "bearish_factors": analysis.get("bearish_factors") or [],
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
    if headlines:
        ctx["headlines"] = headlines

    ctx["notebooklm_enriched"] = True
    ctx["notebooklm_count"] = len(headlines)
    return ctx
```

### 5.3 `recommendation_engine.py` 수정

현재 `_apply_advisor_blend()` context에는 `factors`, `shap`, `bull_summary`만 존재한다.
여기에 market을 넣는다.

```python
context = {
    "market": "KRX" if ticker.endswith((".KS", ".KQ")) else "US",
    "factors": {
        "latest": snap.get("latest"),
        "sma20": snap.get("sma20"),
        "sma50": snap.get("sma50"),
        "atr_pct": snap.get("atr_pct"),
        "market_regime_score": snap.get("market_regime_score"),
        "direction_prob": model_stats.get("latest_prob"),
    },
    "shap": {},
    "bull_summary": (
        f"{ticker} score={deterministic_score:.2f} prob={model_stats.get('latest_prob', 0):.3f}"
    ),
}
```

### 5.4 `NewsSentimentAgent` prompt 확장

현재는 `headlines`만 render한다. `notebook_analysis`를 함께 전달해야 한다.

수정 전:

```python
rendered_user = render(
    user_tpl, {"ticker": ticker, "as_of": as_of, "headlines": [h.__dict__ for h in headlines]}
)
```

수정 후:

```python
rendered_user = render(
    user_tpl,
    {
        "ticker": ticker,
        "as_of": as_of,
        "headlines": [h.__dict__ for h in headlines],
        "notebook_analysis": context.get("notebook_analysis"),
    },
)
```

### 5.5 `news_user` prompt 수정

```text
Ticker: {{ticker}}
As of: {{as_of}}

NotebookLM source-grounded analysis:
{{notebook_analysis}}

Headlines:
{{headlines}}

Task:
Return ONLY JSON:
{
  "score": -1.0..1.0,
  "confidence": 0.0..1.0,
  "rationale": "explain how NotebookLM analysis and price context affect the stock view",
  "citations": ["source URLs"],
  "proposition": "single falsifiable market proposition"
}

Rules:
- If NotebookLM confidence is low, reduce your confidence.
- If price momentum contradicts news sentiment, state the conflict.
- Do not upgrade recommendation gates. This is advisory only.
```

---

## PR-3: Dashboard display

### 6.1 `RecommendationResult` 필드 추가

```python
notebooklm_impact: str | None = None
notebooklm_confidence: float | None = None
notebooklm_source_count: int | None = None
notebooklm_as_of: str | None = None
```

### 6.2 `_apply_advisor_blend()` 반환 확장

현재 반환:

```python
return advisor_score, advisor_rationale, float(blended), advisor_regime
```

확장:

```python
return advisor_score, advisor_rationale, float(blended), advisor_regime, notebook_meta
```

### 6.3 `RecommendationCard.jsx` 표시 추가

LLM Advisor block 내부에 아래 표시 추가:

```jsx
{result.notebooklm_impact && (
  <div style={{ marginTop: 6, fontSize: 8, color: C.textDim }}>
    NotebookLM: <b style={{ color: C.text }}>{result.notebooklm_impact}</b>
    {result.notebooklm_confidence != null && (
      <> · Conf {Number(result.notebooklm_confidence).toFixed(2)}</>
    )}
    {result.notebooklm_source_count != null && (
      <> · Sources {result.notebooklm_source_count}</>
    )}
  </div>
)}
```

---

## 7. 테스트 계획

### 7.1 `iran-war-notelm`

```text
tests/test_stock_news_models.py
tests/test_stock_news_cache.py
tests/test_stock_news_notebook_upload.py
tests/test_stock_news_analysis_api.py
tests/test_stock_news_fallback.py
```

핵심 테스트:

```python
def test_stock_news_api_contract(client):
    resp = client.get("/api/stock-news/notebook-analysis?symbol=AAPL&market=US")
    assert resp.status_code == 200
    data = resp.json()
    assert data["schema_version"] == "notebook_stock_analysis.v1"
    assert data["symbol"] == "AAPL"
    assert "analysis" in data
    assert "sources" in data
    assert "cache" in data
```

### 7.2 `stock_1901`

```text
tests/test_advisor_notebooklm_news.py
tests/test_advisor_notebooklm_context.py
tests/test_news_sentiment_notebook_analysis.py
tests/test_recommendation_engine_notebooklm_meta.py
```

핵심 테스트:

```python
def test_enrich_context_with_notebooklm_success(httpx_mock):
    httpx_mock.add_response(json={
        "schema_version": "notebook_stock_analysis.v1",
        "symbol": "AAPL",
        "market": "US",
        "as_of": "2026-05-30T12:00:00+04:00",
        "notebook": {"source_count": 2},
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
            {"source_id": "s1", "title": "AAPL news", "url": "https://x", "source": "Reuters", "relevance": 0.9}
        ],
        "cache": {"status": "HIT", "ttl_seconds": 900},
        "errors": [],
    })

    ctx = enrich_context_with_notebooklm("AAPL", {"market": "US"})
    assert ctx["notebooklm_enriched"] is True
    assert ctx["notebook_analysis"]["sentiment"] == "bullish"
    assert len(ctx["headlines"]) == 1
```

---

## 8. 환경 변수

### `iran-war-notelm`

```env
STOCK_NEWS_ENABLED=true
STOCK_NEWS_API_ENABLED=true
STOCK_NEWS_TTL_SEC=900
STOCK_NEWS_MAX_ARTICLES=12
STOCK_NEWS_NOTEBOOK_TITLE_PREFIX=STOCKPRED News Intelligence
STOCK_NEWS_REFRESH_MINUTES=15
NOTEBOOKLM_QUERY_TIMEOUT_SEC=90
```

### `stock_1901`

```env
NOTEBOOKLM_NEWS_MODE=cache
NOTEBOOKLM_NEWS_API_BASE=http://127.0.0.1:8088
NOTEBOOKLM_NEWS_TIMEOUT_SEC=3
ADVISOR_RUN=true
ADVISOR_BLEND_WEIGHT=0.10
```

---

## 9. 실행 명령

### 9.1 `iran-war-notelm`

```bash
cd C:\Users\jichu\Downloads\주식\.codex-inspect\iran-war-notelm
python -m pytest tests/test_stock_news_analysis_api.py -q
python -m iran_monitor.stock_news.api
```

### 9.2 `stock_1901`

```bash
cd C:\Users\jichu\Downloads\주식\stock_1901
python -m pytest tests/test_advisor_notebooklm_news.py tests/test_news_sentiment.py tests/test_advisor_news_fetch.py -q
```

### 9.3 통합 smoke

```bash
set NOTEBOOKLM_NEWS_MODE=cache
set NOTEBOOKLM_NEWS_API_BASE=http://127.0.0.1:8088
python -m stock_rtx4060.advisors.notebooklm_news --symbol AAPL --market US
```

---

## 10. Definition of Done

| Gate | 조건 | 판정 기준 |
|---|---|---|
| API Contract | `/api/stock-news/notebook-analysis` 응답 고정 | schema_version 통과 |
| NotebookLM Source | source_id 저장 | source_count >= 1 |
| Analysis | analysis JSON 생성 | sentiment/confidence 존재 |
| Adapter | `context["notebook_analysis"]` 생성 | unit test PASS |
| Advisor | rationale에 NotebookLM 분석 반영 | advisor_rationale에 source-grounded 문구 |
| Dashboard | NotebookLM impact 표시 | UI smoke PASS |
| Fallback | API 장애 시 추천 엔진 계속 작동 | neutral/no-data fallback |
| Audit | source_id/notebook_source_id 저장 | JSON output 또는 DB field 확인 |

---

## 11. 리스크와 차단 조건

| Risk | Impact | Mitigation |
|---|---|---|
| NotebookLM login/session 만료 | source upload 실패 | cache fallback + health check |
| NotebookLM query API 불안정 | analysis 누락 | stock_1901 fallback: no notebook data |
| 뉴스 source 품질 낮음 | ticker relevance 오판 | relevance threshold >= 0.60 |
| Dashboard 요청 지연 | UX 악화 | dashboard 직접 호출 금지 |
| LLM advisor 과신 | 추천 gate 왜곡 | advisor는 downgrade/report-only 원칙 유지 |

---

## 12. 최종 구현 순서

1. `iran-war-notelm`에 stock_news package 추가.
2. stock news API contract test부터 작성.
3. NotebookLM upload wrapper를 stock 전용으로 분리.
4. NotebookLM stock analysis prompt와 parser 작성.
5. cache layer 작성.
6. `/api/stock-news/notebook-analysis` endpoint 작성.
7. `stock_1901/advisors/notebooklm_news.py` adapter 작성.
8. `NewsSentimentAgent` prompt에 `notebook_analysis` 추가.
9. `recommendation_engine.py`에서 market/context meta 전달.
10. dashboard `RecommendationCard.jsx`에 NotebookLM impact 표시.
11. 통합 smoke 후 regression test 실행.

---

## 13. ZERO log

| 단계 | 이유 | 위험 | 요청데이터 | 다음조치 |
|---|---|---|---|---|
| 운영 반영 | 실제 stock-specific NotebookLM API 없음 | STOCKPRED에 NotebookLM 분석 미반영 | `/api/stock-news/notebook-analysis` 구현 | PR-1부터 진행 |
| Dashboard 표시 | notebooklm fields 없음 | 화면에 근거 source 표시 불가 | `notebooklm_impact`, `source_count`, `confidence` 필드 | PR-3에서 추가 |
| Traceability | source_id 저장 미완료 | 분석 근거 재현 불가 | source_id/notebook_source_id DB/JSON 저장 위치 | PR-1/PR-3에서 반영 |
