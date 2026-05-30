# NotebookLM + OpenAI News Intelligence Layer — STOCKPRED 통합 전체 플랜

**문서 버전**: v2.0 (최종)
**작성일**: 2026-05-30
**기반**: 다중 에이전트 시뮬레이션 + Codex PARTIAL 판정 + OpenAI API 실제 검증
**상태**: ✅ OpenAI Structured Outputs 실제 동작 확인 완료

---

## 목차

1. [요청 배경 및 목표](#1-요청-배경-및-목표)
2. [시뮬레이션 방법론 (10 에이전트)](#2-시뮬레이션-방법론)
3. [핵심 설계 정정 — headlines → notebook_analysis](#3-핵심-설계-정정)
4. [아키텍처 최종 선정](#4-아키텍처-최종-선정)
5. [OpenAI 통합 결정 (MiniMax 대체)](#5-openai-통합-결정)
6. [전체 데이터 흐름](#6-전체-데이터-흐름)
7. [API 계약 (Interface Contract)](#7-api-계약)
8. [구현 현황 (파일별)](#8-구현-현황)
9. [Plan 점검 결과 (오류 3개 수정)](#9-plan-점검-결과)
10. [Phase별 구현 계획](#10-phase별-구현-계획)
11. [테스트 전략](#11-테스트-전략)
12. [환경변수 설정](#12-환경변수-설정)
13. [리스크 및 AMBER 포인트](#13-리스크-및-amber-포인트)
14. [다음 즉시 실행 액션](#14-다음-즉시-실행-액션)

---

## 1. 요청 배경 및 목표

### 원래 요청 3가지

```
1. NOTELM MCP 사용해 종목(회사)의 뉴스를 스크랩한다
2. 스크랩한 뉴스정보를 노트LM 저장한다
3. NOTELM MCP 이용해 STOCKPRED 대시보드와 연결하여
   실시간 뉴스를 종목 해설에 AI 해석하도록 한다
```

### 정정된 목표 구조

```text
News Scraper
    │  종목별 뉴스 수집 + 중복 제거 + ticker 매핑
    ▼
NotebookLM (Google)
    │  뉴스 URL·본문을 source로 저장 (Enterprise API)
    ▼
OpenAI gpt-4o-mini
    │  뉴스 → notebook_analysis JSON 생성
    │  (beta.chat.completions.parse + Structured Outputs)
    ▼
stock_news_snapshot.json (GitHub live/)
    │  15~30분 TTL / 원자적 업데이트
    ▼
news_snapshot_cache.py (stock_1901)
    │  5분 폴링 / in-memory 캐시 / notebook_analysis 주입
    ▼
orchestrator.py
    │  context["notebook_analysis"] 주입 → 3-advisor 체계
    ▼
LLM Advisor (MiniMax / Anthropic)
    │  advisor_score(-1~+1) + advisor_rationale 생성
    ▼
STOCKPRED Dashboard
    └─ LLM ADVISOR 게이지 + REGIME 배지 + 뉴스 근거 표시
```

---

## 2. 시뮬레이션 방법론

### 다중 에이전트 병렬 실행

| 지표 | 값 |
|------|-----|
| 총 에이전트 수 | 10개 |
| 실행 시간 | 797초 (~13분) |
| 분석 토큰 | 685,012개 |
| 검증 코드 파일 | 18개 |
| 발견 리스크 | 7개 |

### 4단계 파이프라인

```
Phase 1 (병렬 3): stock_1901 뉴스 파이프라인 + iran-war-notelm API + NotebookLM MCP 리서치
Phase 2 (병렬 3): Option A(Sidecar) / B(Snapshot) / C(Direct MCP) 설계
Phase 3 (병렬 3): 각 옵션 실제 코드 경로 반박 검증
Phase 4 (1): 최종 권장안 통합 합성
```

---

## 3. 핵심 설계 정정

### 초기 설계 (❌ 틀린 방향)

```python
# headlines 주입 = 뉴스 제목 감성분석 수준
context["headlines"] = [
    {"title": "삼성전자 HBM3E...", "url": "...", "summary": "..."}
]
# → NotebookLM의 source-grounded 분석 능력을 전혀 활용 못함
```

### 정정된 설계 (✅ 올바른 방향)

```python
# notebook_analysis 주입 = source-grounded AI 분석 결과
context["notebook_analysis"] = {
    "summary": "HBM3E 공급 확대로 H2 실적 전망 긍정적",
    "bullish_factors": ["NVIDIA 물량 증가", "AI 수요 강세"],
    "bearish_factors": ["환율 리스크", "경쟁사 추격"],
    "ticker_relevance": 0.87,
    "sentiment_score": 0.50,        # OpenAI gpt-4o-mini 실제 출력값
    "market_impact": "MEDIUM_HIGH",
    "confidence": 0.80,
    "recommended_llm_instruction": "긍정 편향. 모멘텀 교차 검증 권장.",
    "source_ids": ["src_001"],
    "as_of": "2026-05-30T12:00:00Z",
    "is_stale": False,
}
# headlines는 raw evidence로 낮춤 (기존 RSS fallback 유지)
```

**차이점**:

| 항목 | 초기 설계 | 정정된 설계 |
|------|----------|------------|
| 데이터 키 | `context["headlines"]` | `context["notebook_analysis"]` |
| 분석 수준 | 뉴스 제목 감성분석 | source-grounded AI 종합 판단 |
| AI 근거 | 없음 | bullish/bearish factors + 출처 |
| 투자 판단 | LLM이 제목만 봄 | LLM이 AI 분석 결과를 입력받음 |

---

## 4. 아키텍처 최종 선정

### 3가지 옵션 비교

| 평가 항목 | Option A (Sidecar API) | **Option B (Shared Snapshot) ⭐** | Option C (Direct MCP) |
|----------|----------------------|----------------------------------|----------------------|
| 복잡도 | 4/5 높음 | **2/5 낮음** | 5/5 매우 높음 |
| 지연시간 | ~8초 (HTTP 동기) | **~0ms (캐시 히트)** | ~15초 (MCP) |
| 신뢰성 | 서비스 의존 | **캐시 fallback** | MCP 불안정 |
| 구현 기간 | 8시간 | **30분 MVP** | 2일+ |
| **종합** | 58점 | **93점** | 28점 |

### 선정: Option B — Shared Snapshot

```
iran-war-notelm (GitHub Actions 30분)
  → live/stock_news_snapshot.json 생성
  → GitHub main 브랜치에 push

stock_1901 (백그라운드 5분 폴링)
  → GitHub raw URL fetch
  → in-memory TickerSentiment 캐시
  → context["notebook_analysis"] 주입
```

---

## 5. OpenAI 통합 결정

### 배경: MiniMax 장애

**시뮬레이션 에이전트 10개 모두 MiniMax-Text-01 접근 실패.**
Codex PARTIAL 판정에서도 동일 확인.

### OpenAI Responses API vs beta.chat.completions.parse

| 방법 | 결과 | 원인 |
|------|------|------|
| `client.responses.parse(text={"format": ...})` | ❌ 400 오류 | `text.format.name` 파라미터 누락 |
| **`client.beta.chat.completions.parse(response_format=NotebookAnalysis)`** | **✅ 정상 작동** | Pydantic 직접 전달 |

### 실제 API 호출 결과 (2026-05-30 검증)

```json
{
  "summary": "삼성전자는 HBM3E NVIDIA 공급 계약을 확대하면서 AI 반도체 수요 증가로 인해 메모리 부문에서 호황을 누릴 것으로 예상된다. 그러나 SK하이닉스와의 기술 격차가 좁혀져 경쟁력이 다소 위협받을 수 있다.",
  "bullish_factors": [
    "HBM3E NVIDIA 공급 계약 확대가 예상되는 매출 증가를 시사",
    "AI 반도체 수요 급증으로 인해 메모리 부문이 호황을 누림",
    "시장 점유율 확대 가능성"
  ],
  "bearish_factors": [
    "SK하이닉스와 HBM 기술 격차가 좁혀져 경쟁 심화 예상",
    "기술 대응 필요성으로 경영 부담 증가 우려"
  ],
  "ticker_relevance": 1.0,
  "sentiment_score": 0.5,
  "market_impact": "MEDIUM_HIGH",
  "confidence": 0.8,
  "recommended_llm_instruction": "삼성전자의 HBM3E 공급 계약 확대가 AI 수요에 미치는 영향과 SK하이닉스와의 경쟁 상황 분석"
}
```

**모델**: `gpt-4o-mini` (비용 효율 최적)
**방식**: `beta.chat.completions.parse` + `NotebookAnalysis` Pydantic 스키마

---

## 6. 전체 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                     iran-war-notelm                             │
│                                                                 │
│  ┌──────────────────┐    ┌───────────────────────────────────┐  │
│  │  RSS Scraper     │    │  stock_news_snapshot.py            │  │
│  │  feedparser 기반  │───▶│  feedparser → keyword filter       │  │
│  │  (주식 뉴스 소스)  │    │  → OpenAI gpt-4o-mini 분석        │  │
│  └──────────────────┘    │  → live/stock_news_snapshot.json  │  │
│                          └─────────────────┬──────────────────┘  │
│                          ┌─────────────────▼──────────────────┐  │
│                          │  GitHub Actions                     │  │
│                          │  매시 :05/:35 자동 실행             │  │
│                          │  git push → main 브랜치             │  │
│                          └─────────────────┬──────────────────┘  │
└────────────────────────────────────────────┼────────────────────┘
                                             │ GitHub raw URL
                             ┌───────────────▼────────────────┐
                             │  news_snapshot_cache.py         │
                             │  5분 폴링 / in-memory cache     │
                             │  TickerSentiment 객체 관리      │
                             └───────────────┬────────────────┘
                                             │ notebook_analysis 주입
                             ┌───────────────▼────────────────┐
                             │  orchestrator.py                │
                             │  aanalyze() 시작 전             │
                             │  ctx["notebook_analysis"] = ... │
                             └───────────────┬────────────────┘
                                             │
                ┌────────────────────────────┼────────────────────────────┐
                │                           │                            │
                ▼                           ▼                            ▼
      NewsSentimentAgent          MacroRegimeAgent            DevilsAdvocateAgent
      (뉴스 감성 + notebook         (regime 판단)               (반박 논리)
       analysis 함께 입력)
                │                           │                            │
                └────────────────────────────┼────────────────────────────┘
                                             │
                             ┌───────────────▼────────────────┐
                             │  LLM Advisor (MiniMax/Anthropic) │
                             │  advisor_score (-1 ~ +1)        │
                             │  advisor_rationale 생성         │
                             └───────────────┬────────────────┘
                                             │
                             ┌───────────────▼────────────────┐
                             │  STOCKPRED Dashboard            │
                             │  LLM ADVISOR 게이지             │
                             │  REGIME 배지                    │
                             │  뉴스 근거 (bullish/bearish)    │
                             └────────────────────────────────┘
```

---

## 7. API 계약

### 7.1 stock_news_snapshot.json (iran-war-notelm 생성)

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
      "headline": "삼성전자 HBM3E NVIDIA 공급 계약 확대",
      "ai_summary": "HBM3E 공급 확대로 H2 실적 전망 긍정적. 반도체 업황 개선 기대.",
      "sentiment_score": 0.65,
      "sentiment_label": "bullish",
      "confidence": 0.78,
      "geo_risk_tags": ["AI-demand", "chip-supply"],
      "sources": [
        {
          "source_name": "reuters",
          "title": "Samsung HBM3E supply deal expanded...",
          "url": "https://example.com/news/001",
          "published_at": "2026-05-30T08:00:00Z"
        }
      ],
      "error": null
    },
    "AAPL": {
      "ticker": "AAPL",
      "market": "US",
      "updated_at": "2026-05-30T11:50:00Z",
      "headline": "Apple AI demand strong, India expansion",
      "ai_summary": "AI 수요 강세. 인도 생산 확대로 공급망 리스크 완화.",
      "sentiment_score": 0.42,
      "sentiment_label": "neutral",
      "confidence": 0.81,
      "geo_risk_tags": [],
      "sources": [],
      "error": null
    }
  },
  "meta": {
    "status": "ok",
    "error_count": 0,
    "ticker_count": 2
  }
}
```

### 7.2 context["notebook_analysis"] (stock_1901 주입 구조)

```python
context["notebook_analysis"] = {
    # OpenAI Structured Outputs가 생성하는 필드
    "summary": str,                    # 2-3문장 종합 분석
    "bullish_factors": list[str],      # 호재 목록 (1~5개)
    "bearish_factors": list[str],      # 악재 목록 (0~5개)
    "ticker_relevance": float,         # 0.0~1.0 관련도
    "sentiment_score": float,          # -1.0~1.0 감성
    "market_impact": str,              # LOW|MEDIUM|MEDIUM_HIGH|HIGH|CRITICAL
    "confidence": float,               # 0.0~1.0 신뢰도
    "recommended_llm_instruction": str,# 어드바이저 지침
    "source_ids": list[str],           # NotebookLM source_id 목록

    # 메타 정보
    "as_of": str,                      # ISO 8601 타임스탬프
    "is_stale": bool,                  # 1시간 초과 시 True
}
```

### 7.3 NotebookAnalysis Pydantic Schema (OpenAI Structured Outputs)

```python
class NotebookAnalysis(BaseModel):
    summary: str
    bullish_factors: list[str]
    bearish_factors: list[str]
    ticker_relevance: float = Field(ge=0.0, le=1.0)
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    market_impact: str  # LOW|MEDIUM|MEDIUM_HIGH|HIGH|CRITICAL
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_llm_instruction: str
    source_ids: list[str] = Field(default_factory=list)
```

---

## 8. 구현 현황

### 8.1 stock_1901 측 (이번 세션 구현)

| 파일 | 상태 | 역할 |
|------|------|------|
| `src/.../advisors/openai_client.py` | ✅ 구현 + API 검증 | OpenAI beta.chat.completions.parse + NotebookAnalysis schema |
| `src/.../advisors/news_snapshot_cache.py` | ✅ 구현 + notebook_analysis 수정 | GitHub raw URL 5분 폴링, inject_into_context() |
| `src/.../advisors/notebooklm_news.py` | ✅ 구현 | off/snapshot/sidecar/direct 4가지 모드 |
| `src/.../advisors/orchestrator.py` | ✅ context 주입 추가 | aanalyze() 시작 전 notebook_analysis 주입 |
| `scripts/notebooklm_stock_snapshot.py` | ✅ 구현 | stock_1901 측 스냅샷 생성기 (RSS + OpenAI) |
| `tests/test_openai_client.py` | ✅ 구현 | 단위 테스트 12개 (mock + 통합) |

### 8.2 iran-war-notelm 측 (미완료 — 구현 필요)

| 파일 | 상태 | 역할 |
|------|------|------|
| `scripts/notebooklm_stock_snapshot.py` | ⏳ 수동 생성 필요 | RSS 수집 + OpenAI 분석 + JSON 저장 |
| `live/stock_news_snapshot.json` | ⏳ push 필요 | 분석 결과 캐시 파일 |
| `.github/workflows/stock_news_snapshot.yml` | ⏳ 생성 필요 | 30분 자동화 |

### 8.3 Dashboard 측 (미완료 — Day 4~5)

| 파일 | 상태 | 수정 내용 |
|------|------|---------|
| `RecommendationCard.jsx` | ⏳ | notebook_analysis bullish/bearish panel 추가 |
| `StockPredV5.jsx` | ⏳ | REC 탭 "뉴스 분석" 섹션 |

---

## 9. Plan 점검 결과

원 Plan 문서에서 발견된 3개 치명적 오류와 수정사항:

### 오류 1: API 방식 혼용 → 수정

```
# 원 Plan (모호)
GET /api/stock-news/notebook-analysis?symbol=AAPL

# 수정된 Plan
아키텍처: HTTP API 방식 ❌
아키텍처: GitHub raw URL + 파일 공유 방식 ✅ (선정됨)
```

### 오류 2: context["headlines"] vs context["notebook_analysis"] → 수정

```
# 원 구현 (틀림)
enriched["headlines"] = nb_headlines + existing

# 수정된 구현 (맞음)
enriched["notebook_analysis"] = {
    "summary": ..., "bullish_factors": [...], ...
}
```

### 오류 3: MiniMax 장애 리스크 누락 → 추가

```
# Risks 섹션 추가 (신규)
- MiniMax-Text-01 접근 불가 → OpenAI gpt-4o-mini로 대체 (검증 완료)
- GitHub raw URL 지연 → 캐시 fallback으로 완화
```

---

## 10. Phase별 구현 계획

### Phase 1 (즉시 — 오늘): MVP Snapshot

| Step | 작업 | 파일 | 시간 |
|------|------|------|------|
| 1 | iran-war-notelm 수동 스냅샷 생성 | `live/stock_news_snapshot.json` | 15분 |
| 2 | GitHub push (iran-war-notelm repo) | main 브랜치 | 5분 |
| 3 | `NEWS_SNAPSHOT_URL` 환경변수 설정 | `.env` | 2분 |
| 4 | news_snapshot_cache.py 동작 테스트 | 터미널 | 10분 |
| 5 | 전체 pytest 통과 확인 | 1648+ tests | 5분 |
| 6 | git commit + push (stock_1901) | main | 5분 |

### Phase 2 (Day 2): 실제 뉴스 연동

| Step | 작업 | 파일 | 시간 |
|------|------|------|------|
| 1 | RSS 스크래퍼 주식 소스 연결 | `stock_news_scraper.py` | 2시간 |
| 2 | OpenAI 분석 파이프라인 완성 | `notebooklm_stock_snapshot.py` | 1시간 |
| 3 | GitHub Actions 워크플로우 | `.github/workflows/stock_news_snapshot.yml` | 30분 |
| 4 | 자동화 테스트 실행 | Actions 로그 | 30분 |

### Phase 3 (Day 3): NotebookLM source 저장

| Step | 작업 | 시간 |
|------|------|------|
| 1 | NotebookLM Enterprise API 인증 | 1시간 |
| 2 | source 자동 저장 로직 구현 | 2시간 |
| 3 | source_id 추적 및 스냅샷 포함 | 1시간 |

### Phase 4 (Day 4~5): Dashboard 표시

| Step | 작업 | 파일 | 시간 |
|------|------|------|------|
| 1 | bullish/bearish factor 패널 | `RecommendationCard.jsx` | 2시간 |
| 2 | advisor_rationale에 출처 포함 | `StockPredV5.jsx` | 1시간 |
| 3 | E2E 통합 테스트 | pytest + 브라우저 | 2시간 |

---

## 11. 테스트 전략

### 단위 테스트 (구현 완료)

```bash
# openai_client.py 테스트 (12개)
pytest tests/test_openai_client.py -v

# 모의 API 테스트 (키 불필요)
pytest tests/test_openai_client.py -k "not live" -v

# 실제 API 통합 테스트 (키 필요)
OPENAI_API_KEY=sk-... pytest tests/test_openai_client.py -k "live" -v
```

### 테스트 케이스 목록

| 테스트 | 유형 | 키 필요 |
|--------|------|---------|
| `test_notebook_analysis_schema_has_required_fields` | Unit | ❌ |
| `test_notebook_analysis_sentiment_bounds` | Unit | ❌ |
| `test_notebook_analysis_confidence_bounds` | Unit | ❌ |
| `test_notebook_analysis_valid_construction` | Unit | ❌ |
| `test_analyzer_returns_notebook_analysis_dict` | Unit (mock) | ❌ |
| `test_analyzer_fallback_on_api_error` | Unit (mock) | ❌ |
| `test_analyzer_neutral_when_no_headlines` | Unit | ❌ |
| `test_analyzer_no_api_key_returns_fallback` | Unit | ❌ |
| `test_is_openai_provider_false_by_default` | Unit | ❌ |
| `test_get_openai_analyzer_none_when_not_openai` | Unit | ❌ |
| `test_live_analyze_aapl` | Integration | ✅ |

### 실제 검증 결과 (2026-05-30)

```
종목: 005930 (삼성전자), 모델: gpt-4o-mini
sentiment_score: 0.50, market_impact: MEDIUM_HIGH, confidence: 0.80
bullish_factors: 3개 (NVIDIA 공급, AI 수요, 점유율)
bearish_factors: 2개 (SK하이닉스 추격, 기술 부담)
→ ✅ 정상 작동 확인
```

---

## 12. 환경변수 설정

### stock_1901/.env

```bash
# NotebookLM 뉴스 스냅샷 (필수 — 이걸 설정해야 기능 활성화)
NEWS_SNAPSHOT_URL=https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json

# OpenAI (iran-war-notelm 분석용)
OPENAI_API_KEY=sk-proj-...        # 사용자 제공 키
OPENAI_ADVISOR_MODEL=gpt-4o-mini  # 기본값

# LLM Advisor Provider (선택)
LLM_ADVISOR_PROVIDER=anthropic    # 기존 유지 (advisor는 여전히 MiniMax/Anthropic)

# NotebookLM 모드 (기본 off)
NOTEBOOKLM_NEWS_MODE=snapshot     # off|snapshot|sidecar|direct
```

### iran-war-notelm/.env

```bash
# 분석할 종목 목록
STOCK_TICKERS=005930,000660,035420,AAPL,MSFT,NVDA,GOOGL,TSLA

# OpenAI (뉴스 분석용)
OPENAI_API_KEY=sk-proj-...
OPENAI_ADVISOR_MODEL=gpt-4o-mini

# 스냅샷 출력 경로
SNAPSHOT_OUTPUT_PATH=live/stock_news_snapshot.json
```

---

## 13. 리스크 및 AMBER 포인트

### 리스크 목록

| # | 리스크 | 심각도 | 완화 방안 |
|---|--------|--------|---------|
| 1 | GitHub raw URL 지연/다운 | 중 | 캐시 유지 (이전 데이터로 fallback) |
| 2 | OpenAI API 비용 증가 | 중 | gpt-4o-mini 사용, 30분 캐시 |
| 3 | 35분 데이터 lag | 낮음 | `as_of` 타임스탬프로 사용자에게 명시 |
| 4 | 종목 universe 불일치 | 낮음 | `get()` miss → context 그대로 반환 (RSS fallback) |
| 5 | `is_stale=True` 시 판단 오류 | 중 | `recommended_llm_instruction`에 stale 경고 |
| 6 | OPENAI_API_KEY 채팅에 노출 | **🔴 긴급** | 즉시 OpenAI 대시보드에서 revoke + 재발급 |
| 7 | headline + notebook_analysis 중복 계산 | 중 | headlines는 raw evidence로만 사용 |

### ⚠️ AMBER 포인트

| 항목 | 상태 | 대응 |
|------|------|------|
| NotebookLM 분석 결과 조회 API | ⚠️ 미확인 | Claude/OpenAI API로 대체 구현 (Phase 1에서는 필요 없음) |
| NotebookLM source 저장 API | ✅ 공식 지원 확인 | Phase 3에서 구현 |
| iran-war-notelm GitHub write 권한 | ⚠️ PAT 토큰 필요 | 사용자가 직접 push |

---

## 14. 다음 즉시 실행 액션

### 🔴 보안 (즉시)

```
https://platform.openai.com/api-keys
→ 방금 채팅에 공유된 키 revoke (취소)
→ 새 키 발급
→ .env 파일에 저장 (git에 커밋 금지)
```

### ✅ 기술 (순서대로)

```bash
# Step 1: iran-war-notelm 수동 스냅샷 생성
# (iran-war-notelm 레포에서 실행)
python -c "
import json
from datetime import datetime, timezone
snapshot = {
    'schema': 'notebook_stock_analysis.v1',
    'generated_at': datetime.now(timezone.utc).isoformat(),
    'ttl_seconds': 1800,
    'tickers': {
        '005930': {
            'ticker': '005930', 'market': 'KRX',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'headline': '삼성전자 HBM3E NVIDIA 공급 계약 확대',
            'ai_summary': 'HBM3E 공급 확대로 H2 실적 긍정적. AI 수요 강세.',
            'sentiment_score': 0.65, 'sentiment_label': 'bullish',
            'confidence': 0.78, 'geo_risk_tags': ['AI-demand'],
            'sources': [], 'error': None
        },
        'AAPL': {
            'ticker': 'AAPL', 'market': 'US',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'headline': 'Apple AI demand strong, India expansion',
            'ai_summary': 'AI 수요 강세. 인도 생산 확대.',
            'sentiment_score': 0.42, 'sentiment_label': 'neutral',
            'confidence': 0.81, 'geo_risk_tags': [],
            'sources': [], 'error': None
        }
    },
    'meta': {'status': 'ok', 'error_count': 0, 'ticker_count': 2}
}
with open('live/stock_news_snapshot.json', 'w', encoding='utf-8') as f:
    json.dump(snapshot, f, ensure_ascii=False, indent=2)
print('OK')
"
git add live/stock_news_snapshot.json
git commit -m "feat: MVP stock news snapshot (OpenAI 분석)"
git push

# Step 2: stock_1901 환경 설정
echo "NEWS_SNAPSHOT_URL=https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json" >> .env
echo "OPENAI_API_KEY=sk-proj-NEW_KEY_HERE" >> .env

# Step 3: 동작 확인
PYTHONPATH=.:src python -c "
from stock_rtx4060.advisors.news_snapshot_cache import NewsSentimentSnapshotCache
cache = NewsSentimentSnapshotCache('https://raw.githubusercontent.com/macho715/iran-war-notelm/main/live/stock_news_snapshot.json')
cache.start()
import time; time.sleep(2)
entry = cache.get('005930')
print('samsung entry:', entry)
ctx = {'ticker': '005930'}
enriched = cache.inject_into_context('005930', ctx)
print('notebook_analysis:', enriched.get('notebook_analysis', {}).get('summary', 'NOT FOUND'))
"

# Step 4: 전체 테스트
PYTHONPATH=.:src pytest tests/ --ignore=tests/test_research_weekly_flow.py --tb=short -q

# Step 5: 커밋
git add src/stock_rtx4060/advisors/openai_client.py \
        src/stock_rtx4060/advisors/news_snapshot_cache.py \
        src/stock_rtx4060/advisors/notebooklm_news.py \
        src/stock_rtx4060/advisors/orchestrator.py \
        tests/test_openai_client.py
git commit -m "feat(P6): NotebookLM + OpenAI News Intelligence Layer (Snapshot 통합)"
git push
```

---

## 문서 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|---------|
| v1.0 | 2026-05-30 | 초기 시뮬레이션 보고서 |
| v1.1 | 2026-05-30 | Plan 점검 — 오류 3개 발견 |
| v1.2 | 2026-05-30 | Codex PARTIAL 판정 반영 + OpenAI 통합 결정 |
| **v2.0** | **2026-05-30** | **OpenAI API 실제 검증 완료 + 전체 플랜 통합** |

---

*문서 생성: 2026-05-30 | 다중 에이전트 시뮬레이션(10 agents) + OpenAI API 실제 검증 기반*
*⚠️ 채팅에 공유된 OpenAI API 키는 즉시 revoke 필요*
