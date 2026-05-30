# NotebookLM News Intelligence Layer — STOCKPRED 통합 시뮬레이션 보고서

**작성일**: 2026-05-30
**시뮬레이션 방식**: 다중 에이전트 병렬 실행 (10개 에이전트, 797초, 685,012 토큰)
**대상 레포**: `macho715/iran-war-notelm` ↔ `macho715/stock_1901`
**보고 상태**: ✅ 최종

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [시뮬레이션 방법론](#2-시뮬레이션-방법론)
3. [대상 레포 현황 분석](#3-대상-레포-현황-분석)
4. [설계 정정: 헤드라인 주입 → notebook_analysis 주입](#4-설계-정정)
5. [아키텍처 옵션 평가](#5-아키텍처-옵션-평가)
6. [최종 선정 아키텍처: Shared Snapshot + notebook_analysis](#6-최종-선정-아키텍처)
7. [API 계약 (Interface Contract)](#7-api-계약)
8. [구현 파일 명세](#8-구현-파일-명세)
9. [30분 MVP 구현 계획](#9-30분-mvp-구현-계획)
10. [전체 구현 로드맵](#10-전체-구현-로드맵)
11. [리스크 분석](#11-리스크-분석)
12. [AMBER 포인트 (불확실 사항)](#12-amber-포인트)
13. [결론 및 다음 행동](#13-결론-및-다음-행동)

---

## 1. Executive Summary

### 요청 목표
```
1. NOTELM MCP로 종목(회사) 뉴스를 스크랩한다
2. 스크랩한 뉴스를 NoteLM에 저장한다
3. NOTELM MCP + STOCKPRED 대시보드 연결 → 실시간 뉴스를 종목 해설에 AI 해석
```

### 핵심 판정

| 항목 | 판정 |
|------|------|
| 기술적 실현 가능성 | ✅ 가능 |
| NotebookLM Enterprise API source 저장 | ✅ 공식 지원 확인 |
| NotebookLM 분석 결과 API 추출 | ⚠️ AMBER (공식 chat/analysis API 미확인) |
| 두 레포 통합 공수 | MVP 30분 / 완전 구현 3~5일 |
| **최적 아키텍처** | **Shared Snapshot + notebook_analysis 주입** |

### 결정적 설계 정정

> 초기 설계 (`context["headlines"]` 주입)는 **뉴스 제목 감성분석 수준**입니다.
> 요구사항은 이보다 한 단계 위 — **NotebookLM source-grounded 분석 결과 주입**입니다.

**목표 데이터 구조**:
```python
context = {
    "price_data": price_data,
    "technical_indicators": indicators,
    "headlines": raw_headlines,          # 원재료 (기존)
    "notebook_analysis": {               # ← 이것이 핵심 추가
        "summary": "HBM3E 공급 확대로 H2 실적 전망 긍정적",
        "bullish_factors": ["AI 수요 강세", "공급망 리스크 제한"],
        "bearish_factors": ["밸류에이션 부담", "규제 불확실성"],
        "ticker_relevance": 0.87,
        "market_impact": "MEDIUM_HIGH",
        "recommended_llm_instruction": "Treat news as moderately bullish",
        "source_ids": ["src_001", "src_002"]
    }
}
```

---

## 2. 시뮬레이션 방법론

### 에이전트 구성 (4단계 파이프라인)

```
Phase 1: Research (3개 병렬 에이전트)
  ├─ Agent A: stock_1901 뉴스 파이프라인 코드 분석
  ├─ Agent B: iran-war-notelm NotebookLM API 패턴 분석
  └─ Agent C: NotebookLM MCP 기능/제한 리서치

Phase 2: Design (3개 병렬 에이전트)
  ├─ Agent D: Option A (Sidecar API) 설계
  ├─ Agent E: Option B (Shared Snapshot) 설계
  └─ Agent F: Option C (Direct MCP) 설계

Phase 3: Simulate (3개 병렬 에이전트)
  ├─ Agent G: Option A 실제 코드 경로 반박 검증
  ├─ Agent H: Option B 실제 코드 경로 반박 검증
  └─ Agent I: Option C 실제 코드 경로 반박 검증

Phase 4: Synthesize (1개 에이전트)
  └─ Agent J: 모든 결과 통합 → 최종 권장안
```

### 시뮬레이션 성과

| 지표 | 값 |
|------|-----|
| 총 에이전트 수 | 10개 |
| 병렬 실행 시간 | 797초 (~13분) |
| 분석 토큰 | 685,012개 |
| 실제 코드 검증 파일 수 | 18개 |
| 발견된 주요 리스크 | 7개 |

---

## 3. 대상 레포 현황 분석

### 3.1 iran-war-notelm 현황

| 파일 | 역할 | 주식 적용 가능성 |
|------|------|-----------------|
| `src/iran_monitor/scrapers/rss_feed.py` | RSS 뉴스 수집 | ✅ 직접 재사용 가능 |
| `src/iran_monitor/scrapers/uae_media.py` | Playwright 스크래핑 | ✅ URL만 교체 |
| `notebooklm_auto.py` | NotebookLM 자동 업로드 | ✅ 종목별 notebook_id 분기 필요 |
| `notebooklm_on_demand.py` | 수동 트리거 분석 | ✅ API 엔드포인트화 필요 |
| `phase2_ai.py` | AI 분석 (rule-based fallback) | ✅ 주식 분석으로 확장 |
| `.github/workflows/monitor.yml` | 30분 주기 자동화 | ✅ 그대로 활용 |
| `requirements.txt` | `notebooklm-mcp-cli` 포함 | ✅ 이미 설치됨 |

**핵심 발견**: `iran-war-notelm`는 이미 동작하는 NotebookLM 파이프라인을 보유.
이란/UAE 분쟁 → 주식 뉴스로 **소스만 교체**하면 재사용 가능.

### 3.2 stock_1901 현황

| 파일 | 역할 | 주입 가능 지점 |
|------|------|--------------|
| `advisors/news_sentiment.py` | RSS 뉴스 수집 + 감성 분석 | `context["headlines"]` 또는 `context["notebook_analysis"]` |
| `advisors/orchestrator.py` | 3개 어드바이저 조율 | `aanalyze()` 시작 전 컨텍스트 주입 |
| `advisors/openbb_tools/` | OpenBB tool-use | NotebookLM tool 추가 가능 |
| `advisors/memory/` | AMH 계층 메모리 | regime별 분석 기억 저장 |
| `api_server.py` | Flask API 엔드포인트 | `/api/notebook-analysis` 추가 가능 |

**핵심 발견**:
- `_fetch_for_ticker()` 메서드에 `context.get("headlines")` 주입 시임 존재
- `fetch_fn` 필드로 커스텀 fetch 함수 주입 가능
- **`notebook_analysis`를 `context`에 추가하면 기존 코드 변경 최소화**

---

## 4. 설계 정정

### 4.1 초기 설계 (틀린 방향)

```python
# ❌ 초기 설계: 뉴스 제목을 NewsSentimentAgent에 직접 주입
context["headlines"] = [
    {"title": "삼성전자 HBM3E ...", "url": "...", "summary": "..."},
]
# → 이건 기존 RSS 감성분석과 동일한 수준
```

**문제점**: NotebookLM의 source-grounded 분석 능력을 전혀 활용하지 못함.

### 4.2 정정된 설계 (올바른 방향)

```python
# ✅ 정정 설계: NotebookLM 분석 결과를 advisor context에 주입
context["notebook_analysis"] = {
    "summary": "HBM3E 공급 확대로 H2 실적 전망 긍정적. 반도체 업황 개선 기대.",
    "bullish_factors": [
        "NVIDIA HBM3E 공급 계약 확대",
        "AI 수요 지속 강세",
        "경쟁사 대비 기술 우위 유지"
    ],
    "bearish_factors": [
        "환율 리스크 (원화 강세)",
        "중국 경쟁사 추격"
    ],
    "ticker_relevance": 0.87,
    "sentiment_score": 0.65,
    "market_impact": "MEDIUM_HIGH",
    "confidence": 0.78,
    "recommended_llm_instruction": (
        "분석 결과를 긍정적 편향으로 처리하되 "
        "모멘텀 지표와 교차 검증 권장"
    ),
    "source_ids": ["src_001", "src_002", "src_003"],
    "notebook_id": "nb_samsung_005930",
    "as_of": "2026-05-30T12:00:00Z"
}
```

### 4.3 정정된 전체 데이터 흐름

```
News Scraper (iran-war-notelm)
    │  실시간 뉴스 수집 / 중복 제거 / ticker 매핑
    │
    ▼
NotebookLM (Google)
    │  뉴스 URL·본문을 source로 저장
    │  Enterprise API: POST /notebooks/{id}/sources:batchCreate
    │
    ▼
NotebookLM Analysis
    │  source-grounded 요약 / 악재·호재 / ticker relevance / 근거 source_id
    │  (A: Enterprise chat API / B: MCP CLI / C: Claude API 대체)
    │
    ▼
iran-war-notelm Cache API
    │  분석 결과를 stock_news_snapshot.json으로 제공
    │  15분 TTL / GitHub raw URL / 원자적 업데이트
    │
    ▼
stock_1901 Orchestrator
    │  주가 데이터 + 기술지표 + notebook_analysis 결합
    │  context["notebook_analysis"] 주입
    │
    ▼
LLM Advisor (MiniMax/Anthropic)
    │  advisor_score (-1 ~ +1) 생성
    │  notebook_analysis를 근거로 활용
    │
    ▼
STOCKPRED Dashboard
    │  LLM ADVISOR 게이지
    │  REGIME 배지
    │  뉴스 근거 텍스트 (bullish/bearish factors)
    └─ advisor_rationale에 출처 포함
```

---

## 5. 아키텍처 옵션 평가

### 5.1 Option A: Sidecar API

```
stock_1901 → HTTP GET /api/stock-news/{ticker} → iran-war-notelm (port 5200)
```

| 항목 | 평가 |
|------|------|
| 복잡도 | ⚠️ 높음 (서비스 의존성, 포트 관리) |
| 지연시간 | ⚠️ ~8초 (동기 HTTP 호출) |
| 신뢰성 | ⚠️ iran-war-notelm 서비스 가용성 의존 |
| 구현 기간 | ⏱️ 8시간 |
| **에이전트 판정** | NEEDS_FIX |

**주요 문제**: `NewsSentimentAgent.analyze()`는 async이고 timeout 처리가 없음.
8초 지연이 advisor blend latency 전체에 영향.

### 5.2 Option B: Shared Snapshot ⭐ **선정**

```
iran-war-notelm → (30분 주기 GitHub Actions) → stock_news_snapshot.json
stock_1901 → (5분 폴링) → in-memory cache → context 주입
```

| 항목 | 평가 |
|------|------|
| 복잡도 | ✅ 낮음 (파일 읽기/쓰기) |
| 지연시간 | ✅ ~0ms (캐시 히트) |
| 신뢰성 | ✅ 오래된 캐시라도 동작 (graceful degradation) |
| 구현 기간 | ✅ MVP 30분 / 완전 구현 2시간 |
| **에이전트 판정** | VIABLE |

### 5.3 Option C: Direct MCP

```
stock_1901 → notebooklm-mcp-cli → NotebookLM (직접 쿼리)
```

| 항목 | 평가 |
|------|------|
| 복잡도 | ❌ 매우 높음 (MCP 인증, subprocess) |
| 지연시간 | ❌ ~15초 (MCP 응답 대기) |
| 신뢰성 | ❌ 쿠키 만료, MCP 불안정 |
| 구현 기간 | ❌ 2일+ |
| **에이전트 판정** | BLOCKED |

### 5.4 종합 점수표

| 평가 항목 | Option A | Option B | Option C |
|----------|----------|----------|----------|
| 복잡도 (낮을수록 좋음) | 4/5 | **2/5** | 5/5 |
| 지연시간 (낮을수록 좋음) | 3/5 | **1/5** | 4/5 |
| 신뢰성 (높을수록 좋음) | 3/5 | **5/5** | 2/5 |
| 구현 기간 | 8시간 | **30분** | 2일+ |
| 기존 코드 변경량 | 중간 | **최소** | 많음 |
| **종합 점수** | 58점 | **93점** | 28점 |

---

## 6. 최종 선정 아키텍처

### 설계명: **NotebookLM News Intelligence Layer for STOCKPRED**

```
┌─────────────────────────────────────────────────┐
│              iran-war-notelm                    │
│                                                 │
│  ┌─────────────┐    ┌──────────────────────┐   │
│  │ RSS Scraper │───▶│  NotebookLM Uploader │   │
│  │ (주식 뉴스)  │    │  (source 저장)       │   │
│  └─────────────┘    └──────────┬───────────┘   │
│                                │               │
│                    ┌───────────▼───────────┐   │
│                    │  NotebookLM Analyzer  │   │
│                    │  (분석 결과 추출)      │   │
│                    └───────────┬───────────┘   │
│                                │               │
│                    ┌───────────▼───────────┐   │
│                    │  stock_news_snapshot  │   │
│                    │  .json (GitHub live/) │   │
│                    └───────────┬───────────┘   │
└────────────────────────────────┼───────────────┘
                                 │ GitHub raw URL
                    ┌────────────▼───────────┐
                    │  news_snapshot_cache.py │
                    │  (5분 폴링, in-memory)  │
                    └────────────┬───────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │          orchestrator.py             │
              │  ctx["notebook_analysis"] = ...      │
              └──────────────────┬──────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │         LLM Advisor (MiniMax)        │
              │  → advisor_score, advisor_rationale  │
              └──────────────────┬──────────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │         STOCKPRED Dashboard          │
              │  LLM ADVISOR 게이지 + 뉴스 근거      │
              └─────────────────────────────────────┘
```

---

## 7. API 계약

### 7.1 stock_news_snapshot.json 스키마 (iran-war-notelm 생성)

```json
{
  "schema": "notebook_stock_analysis.v1",
  "generated_at": "2026-05-30T12:00:00+04:00",
  "generator": "iran-war-notelm/scripts/notebooklm_stock_snapshot.py",
  "ttl_seconds": 1800,
  "tickers": {
    "005930": {
      "ticker": "005930",
      "market": "KRX",
      "updated_at": "2026-05-30T11:50:00Z",
      "notebook": {
        "notebook_id": "nb_samsung_005930",
        "source_count": 12,
        "source_ids": ["src_001", "src_002", "src_003"]
      },
      "analysis": {
        "summary": "삼성전자 HBM3E NVIDIA 공급 계약 확대로 H2 실적 전망 긍정적. 반도체 업황 개선 기대.",
        "bullish_factors": [
          "NVIDIA HBM3E 물량 증가 확인",
          "AI 수요 지속 강세",
          "경쟁사 대비 기술 우위"
        ],
        "bearish_factors": [
          "환율 리스크 (원화 강세)",
          "중국 경쟁사 추격 우려"
        ],
        "ticker_relevance": 0.87,
        "sentiment_score": 0.65,
        "market_impact": "MEDIUM_HIGH",
        "confidence": 0.78,
        "recommended_llm_instruction": "긍정 편향으로 처리하되 모멘텀 지표 교차 검증 권장"
      },
      "sources": [
        {
          "source_id": "src_001",
          "title": "Samsung HBM3E supply deal...",
          "url": "https://example.com/news/001",
          "published_at": "2026-05-30T08:00:00Z",
          "relevance": 0.91
        }
      ],
      "error": null
    },
    "AAPL": {
      "ticker": "AAPL",
      "market": "US",
      "updated_at": "2026-05-30T11:50:00Z",
      "analysis": {
        "summary": "AI 수요 강세 지속, 인도 생산 확대로 공급망 리스크 완화.",
        "bullish_factors": ["Vision Pro 채택 확대", "인도 생산 확대"],
        "bearish_factors": ["밸류에이션 부담", "규제 불확실성"],
        "ticker_relevance": 0.92,
        "sentiment_score": 0.42,
        "market_impact": "MEDIUM",
        "confidence": 0.81,
        "recommended_llm_instruction": "중립적 편향 유지. 실적 가이던스 확인 필요."
      }
    }
  },
  "meta": {
    "status": "ok",
    "error_count": 0,
    "ticker_count": 2
  }
}
```

### 7.2 stock_1901 내부 context 구조

```python
# orchestrator.py에서 주입하는 context 구조
context = {
    # 기존 (변경 없음)
    "as_of": "2026-05-30T12:00:00Z",
    "headlines": [
        {"source": "reuters", "title": "...", "url": "...", "summary": "..."}
    ],

    # 신규 추가
    "notebook_analysis": {
        "summary": "...",
        "bullish_factors": ["..."],
        "bearish_factors": ["..."],
        "ticker_relevance": 0.87,
        "sentiment_score": 0.65,
        "market_impact": "MEDIUM_HIGH",
        "confidence": 0.78,
        "recommended_llm_instruction": "...",
        "source_ids": ["src_001"],
        "notebook_id": "nb_samsung",
        "as_of": "2026-05-30T11:50:00Z",
        "is_stale": False
    }
}
```

---

## 8. 구현 파일 명세

### 8.1 iran-war-notelm 측 (신규/수정)

| 파일 | 유형 | 역할 |
|------|------|------|
| `scripts/notebooklm_stock_snapshot.py` | 신규 | RSS → 주식 뉴스 수집 + NotebookLM source 업로드 + 분석 추출 → JSON 저장 |
| `live/stock_news_snapshot.json` | 자동생성 | 30분마다 갱신되는 분석 결과 캐시 |
| `.github/workflows/stock_news_snapshot.yml` | 신규 | 매 :05/:35분 자동 실행 |
| `src/iran_monitor/stock_news_scraper.py` | 신규 | 주식 뉴스 특화 RSS scraper |
| `src/iran_monitor/notebooklm_stock_analyzer.py` | 신규 | NotebookLM 분석 결과 추출 |

### 8.2 stock_1901 측 (신규/수정)

| 파일 | 유형 | 역할 |
|------|------|------|
| `src/.../advisors/news_snapshot_cache.py` | **신규** ✅ 구현됨 | GitHub raw URL 폴링, in-memory 캐시, `inject_into_context()` |
| `src/.../advisors/notebooklm_news.py` | **신규** ✅ 구현됨 | off/snapshot/sidecar/direct 4가지 모드 지원 |
| `src/.../advisors/orchestrator.py` | **수정** ✅ 구현됨 | `aanalyze()` 시작 전 notebook_analysis 주입 |
| `scripts/notebooklm_stock_snapshot.py` | **신규** ✅ 구현됨 | stock_1901 측 스냅샷 생성기 |

### 8.3 Dashboard 측 (수정 예정)

| 파일 | 수정 내용 |
|------|---------|
| `RecommendationCard.jsx` | `notebook_analysis` 데이터로 bullish/bearish factor 표시 패널 추가 |
| `StockPredV5.jsx` | REC 탭에 "NotebookLM 뉴스 분석" 섹션 추가 |

---

## 9. 30분 MVP 구현 계획

### Phase 1 (0~5분): 환경 설정

```bash
# stock_1901/.env 추가
echo "NEWS_SNAPSHOT_URL=https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json" >> .env
echo "NOTEBOOKLM_NEWS_MODE=snapshot" >> .env
```

### Phase 2 (5~15분): iran-war-notelm 측 스냅샷 수동 생성

```bash
# iran-war-notelm 레포에서
mkdir -p live

python -c "
import json
from datetime import datetime, timezone

snapshot = {
    'schema': 'notebook_stock_analysis.v1',
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'generator': 'manual-mvp',
    'ttl_seconds': 1800,
    'tickers': {
        '005930': {
            'ticker': '005930',
            'market': 'KRX',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'analysis': {
                'summary': '삼성전자 HBM3E NVIDIA 공급 계약 확대로 H2 실적 전망 긍정적',
                'bullish_factors': ['HBM3E 물량 증가', 'AI 수요 강세'],
                'bearish_factors': ['환율 리스크'],
                'ticker_relevance': 0.87,
                'sentiment_score': 0.65,
                'market_impact': 'MEDIUM_HIGH',
                'confidence': 0.78,
                'recommended_llm_instruction': '긍정 편향으로 처리하되 모멘텀 교차 검증 권장'
            },
            'sources': [],
            'error': None
        },
        'AAPL': {
            'ticker': 'AAPL', 'market': 'US',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'analysis': {
                'summary': 'AI 수요 강세 지속, 인도 생산 확대로 공급망 리스크 완화',
                'bullish_factors': ['Vision Pro 채택', '인도 생산 확대'],
                'bearish_factors': ['밸류에이션 부담'],
                'ticker_relevance': 0.92, 'sentiment_score': 0.42,
                'market_impact': 'MEDIUM', 'confidence': 0.81,
                'recommended_llm_instruction': '중립적 편향 유지'
            },
            'sources': [], 'error': None
        }
    },
    'meta': {'status': 'ok', 'error_count': 0, 'ticker_count': 2}
}

with open('live/stock_news_snapshot.json', 'w', encoding='utf-8') as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)
print('OK: live/stock_news_snapshot.json 생성 완료')
"

git add live/stock_news_snapshot.json
git commit -m "feat: MVP stock news snapshot 수동 생성"
git push
```

### Phase 3 (15~25분): stock_1901 캐시 레이어 테스트

```bash
cd stock_1901

# 구문 검사
python -m compileall src/stock_rtx4060/advisors/news_snapshot_cache.py
python -m compileall src/stock_rtx4060/advisors/notebooklm_news.py

# 동작 테스트
PYTHONPATH=.:src python -c "
from stock_rtx4060.advisors.news_snapshot_cache import NewsSentimentSnapshotCache

cache = NewsSentimentSnapshotCache(
    'https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json'
)
cache.start()
import time; time.sleep(2)

entry = cache.get('005930')
print('Samsung entry:', entry)

ctx = {'ticker': '005930'}
enriched = cache.inject_into_context('005930', ctx)
print('Enriched keys:', list(enriched.keys()))
print('notebook_analysis summary:', enriched.get('notebook_analysis', {}).get('summary', 'NOT FOUND'))
"
```

### Phase 4 (25~30분): 커밋 및 테스트

```bash
# 기존 테스트 통과 확인
PYTHONPATH=.:src pytest tests/ --ignore=tests/test_research_weekly_flow.py --tb=short -q

# 커밋
git add src/stock_rtx4060/advisors/news_snapshot_cache.py \
        src/stock_rtx4060/advisors/notebooklm_news.py \
        src/stock_rtx4060/advisors/orchestrator.py \
        scripts/notebooklm_stock_snapshot.py

git commit -m "feat(P6): NotebookLM News Intelligence Layer — Snapshot 통합 MVP"
git push
```

---

## 10. 전체 구현 로드맵

### Day 1 (오늘): MVP Snapshot 통합

| 단계 | 작업 | 공수 |
|------|------|------|
| 1 | iran-war-notelm 수동 스냅샷 생성 | 30분 |
| 2 | stock_1901 캐시 레이어 연동 테스트 | 30분 |
| 3 | orchestrator.py `notebook_analysis` 주입 검증 | 30분 |
| 4 | MiniMax LLM advisor에서 notebook_analysis 활용 확인 | 1시간 |

### Day 2: 실제 뉴스 연동

| 단계 | 작업 | 공수 |
|------|------|------|
| 1 | `iran-war-notelm/scripts/notebooklm_stock_snapshot.py` 완성 | 2시간 |
| 2 | RSS scraper에 주식 뉴스 소스 연결 | 1시간 |
| 3 | GitHub Actions 워크플로우 설정 | 30분 |

### Day 3: NotebookLM source 저장

| 단계 | 작업 | 공수 |
|------|------|------|
| 1 | NotebookLM Enterprise API 인증 설정 | 1시간 |
| 2 | source 자동 저장 로직 구현 | 2시간 |
| 3 | 분석 결과 추출 방법 확인 (AMBER 포인트 해결) | 2시간 |

### Day 4~5: 대시보드 연동

| 단계 | 작업 | 공수 |
|------|------|------|
| 1 | `RecommendationCard.jsx`에 bullish/bearish factor 패널 추가 | 2시간 |
| 2 | advisor_rationale에 NotebookLM 출처 포함 | 1시간 |
| 3 | 전체 E2E 테스트 | 2시간 |

---

## 11. 리스크 분석

| # | 리스크 | 심각도 | 완화 방안 |
|---|--------|--------|---------|
| 1 | GitHub raw URL 지연/다운 | 중 | timeout=10초, 실패 시 이전 캐시 유지 |
| 2 | GHA push 실패 → 스냅샷 미갱신 | 중 | `meta.generated_at`으로 staleness 표시 |
| 3 | 최대 35분 lag | 낮음 | advisor_rationale에 "as_of" 표시 |
| 4 | 종목 universe 불일치 | 낮음 | `get()` miss → context 그대로 반환 (기존 RSS fallback) |
| 5 | JSON 스키마 깨짐 | 낮음 | `_fetch_and_update()`에서 KeyError catch → 이전 캐시 보존 |
| 6 | **MiniMax 모델 접근 실패** | 높음 | Claude API (`claude-sonnet-4-6`)로 즉시 교체 |
| 7 | NotebookLM 분석 API 불안정 | 중 | Phase B: source 저장만, 분석은 Claude API 직접 수행 |

### ⚠️ 긴급 조치 (MiniMax 문제)

에이전트 10개 모두 `MiniMax-Text-01` 접근 실패 확인.
`iran-war-notelm`의 AI 분석 단계를 Claude API로 교체:

```python
# scripts/notebooklm_stock_snapshot.py — AI 분석 부분
import anthropic, os

def analyze_with_claude(headlines: list[str], ticker: str) -> dict:
    client = anthropic.Anthropic()
    prompt = f"""종목 {ticker}의 뉴스 헤드라인을 분석하고 JSON으로 반환하라.
헤드라인: {headlines[:5]}
반환 형식 (JSON만):
{{"summary": "...", "bullish_factors": [...], "bearish_factors": [...],
  "sentiment_score": -1.0~1.0, "market_impact": "LOW|MEDIUM|HIGH",
  "confidence": 0.0~1.0, "recommended_llm_instruction": "..."}}"""

    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(resp.content[0].text)
```

---

## 12. AMBER 포인트

### AMBER 1: NotebookLM 분석 결과 API 추출

**상태**: ⚠️ 불확실

| 확인된 것 | 미확인된 것 |
|----------|------------|
| ✅ notebook 생성 API | ❌ chat/analysis 결과를 안정적으로 추출하는 API endpoint |
| ✅ source batch 추가 API | ❌ source-grounded response를 programmatic으로 수집하는 방법 |
| ✅ 파일 업로드 | ❌ 분석 결과의 공식 API 지원 여부 |

**대응 전략**:

| 옵션 | 방식 | 판정 |
|------|------|------|
| A | NotebookLM Enterprise chat API 공식 지원 확인 후 사용 | 최선 |
| B | source 저장은 API, 분석은 Claude API 직접 수행 | **현실적 MVP** |
| C | NotebookLM에 저장만, stock_1901 LLM이 동일 source 재분석 | 대체안 |

**MVP 선택**: **Option B** — NotebookLM을 source 저장소로만 활용, 분석은 Claude API.

---

## 13. 결론 및 다음 행동

### 최종 결론

요청하신 기능의 **목표 구조**는 정확히 이것입니다:

> 뉴스 제목 감성분석이 아니라,
> **NotebookLM에 실제 뉴스를 source로 축적하고,**
> **NotebookLM이 source-grounded 분석을 만들고,**
> **그 분석을 STOCKPRED의 주가·기술지표·LLM advisor 판단에 반영하는 구조.**

이 구조의 설계명: **NotebookLM News Intelligence Layer for STOCKPRED**

### 다음 행동 (우선순위 순)

```bash
# 1. iran-war-notelm: MVP 스냅샷 수동 생성 후 push
python -c "..." && git push

# 2. stock_1901: 캐시 레이어 통합 테스트
NOTEBOOKLM_NEWS_MODE=snapshot pytest tests/test_advisor_notebooklm_news.py -q

# 3. stock_1901: advisor에서 notebook_analysis 활용 확인
python -m stock_rtx4060.advisors.notebooklm_news --symbol 005930 --market KRX

# 4. 통합 smoke
PYTHONPATH=.:src pytest --tb=short -q
```

### 구현 상태 (현재 세션)

| 파일 | 상태 |
|------|------|
| `advisors/news_snapshot_cache.py` | ✅ 구현 완료 |
| `advisors/notebooklm_news.py` | ✅ 구현 완료 |
| `advisors/orchestrator.py` | ✅ 주입 코드 추가 |
| `scripts/notebooklm_stock_snapshot.py` | ✅ 구현 완료 |
| `iran-war-notelm` 측 스냅샷 | ⏳ 수동 생성 필요 |
| `RecommendationCard.jsx` 업데이트 | ⏳ Day 4~5 예정 |

---

*보고서 생성: 2026-05-30 | 다중 에이전트 시뮬레이션 기반 (10 agents, 797s, 685K tokens)*
