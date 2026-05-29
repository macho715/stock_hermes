# PLAN_DOC — OpenBB ODP + MCP Tool as LLM Tool-Use
**v1.0 | 2026-05-29 | skill: project-plan v2.2 | project: stock_1901 / stock_rtx4060**

---

## A. Executive Summary

### 목표
LLM 어드바이저(NewsSentiment, MacroRegime, DevilsAdvocate)가 **추론 중 실시간으로** OpenBB 데이터를 tool_use로 호출할 수 있게 한다. 현재 `load_ohlcv_with_provider()`는 분석 *전에* 데이터를 정적으로 로드하지만, AI-native 패턴은 LLM이 필요한 데이터를 *스스로 결정해서 그 시점에* 쿼리하는 것이다. `ClaudeClient`가 이미 `tools=` 파라미터를 지원하지만 **tool_use 응답 처리 loop가 없는 것**이 핵심 갭이다.

### 핵심 발견 (Benchmark Research)

| 발견 | 설계 결정 |
|------|----------|
| `ClaudeClient.acall(tools=...)` 지원하지만 `stop_reason == "tool_use"` 처리 없음 | `acall_with_tools()` 신규 메서드 — agentic loop 추가 |
| openbb-mcp-server v1.4.1 (2026-05-26) 존재하지만 별도 HTTP 서버 필요 | **Option A: Native tool_use** — 서버 없이 직접 함수 호출 |
| Anthropic 공식: 알려진 고정 툴셋은 native tool_use가 MCP보다 효율적 | tool_use JSON 스키마 정의 + executor 패턴 |
| PIT 가드 불변 규칙 | tool executor에서 `as_of` 이후 날짜 쿼리 차단 |
| OpenBB `obb.equity.price.historical()`, `news.company()`, `fundamental.metrics()` | 4개 핵심 tools 정의 |

### KPI

| Metric | 현재 | 목표 |
|--------|------|------|
| 어드바이저 실시간 데이터 쿼리 | 불가 | `get_price_history` tool call 가능 |
| 어드바이저 뉴스 on-demand 쿼리 | RSS only (정적) | `get_company_news` tool call 가능 |
| 어드바이저 펀더멘털 on-demand 쿼리 | 불가 | `get_fundamental_metrics` tool call 가능 |
| OpenBB 미설치 시 동작 | N/A | graceful fallback (tool returns "openbb not installed") |
| PIT 가드 | `as_of` 엄격 적용 | tool executor `end_date ≤ as_of` 강제 |
| 기존 테스트 통과 | N/A | `OPENBB_TOOLS_ENABLED=false` 시 100% 동일 |

### 범위
- **In-scope**: `advisors/openbb_tools/` 신규 패키지, `ClaudeClient.acall_with_tools()`, PIT-aware tool executor, 4개 tool 스키마, NewsSentiment/MacroRegime 통합, MLflow 비용 추적
- **Out-of-scope**: `openbb-mcp-server` HTTP 서버, `defer_loading` 베타 기능, OpenBB Workspace, KIS/pykrx OpenBB 랩핑, 브로커 연동

### 핵심 결정

| # | 결정 | 근거 |
|---|------|------|
| D1 | Native Anthropic tool_use (Option A), MCP 서버 없음 | "알려진 고정 툴셋은 native가 효율적" — Anthropic 공식 2025-11-24 |
| D2 | `acall_with_tools()` 신규 메서드 (기존 `acall()` 보존) | backward compatibility 100% 유지 |
| D3 | `max_tool_rounds=5` guard — 무한 루프 방지 | Augment Code 패턴 — `RuntimeError` on overflow |
| D4 | tool executor PIT 가드: `end_date ≤ as_of` 강제 | 기존 PIT 불변 규칙 보존 |
| D5 | `OPENBB_TOOLS_ENABLED=false` 기본값 | 기존 어드바이저 동작 100% 보존 |
| D6 | tool executor 응답은 JSON string (≤ 2000자 truncation) | 토큰 예산 50k in / 4k out 초과 방지 |

### 마일스톤

| 마일스톤 | 기간 | 완료 기준 |
|----------|------|-----------|
| M1: Tool 스키마 + Executor | Week 1 | 4개 tool 스키마 + OpenBB executor mock 테스트 통과 |
| M2: ClaudeClient agentic loop | Week 1~2 | `acall_with_tools()` 단위 테스트 통과 |
| M3: 어드바이저 통합 | Week 2~3 | NewsSentiment + MacroRegime tool-augmented 테스트 |
| M4: 테스트 + CI + 문서 | Week 3~4 | 커버리지 ≥80% (openbb_tools), CLAUDE.md 업데이트 |

---

## B. Context & Requirements

### B1. 문제 정의

**현재 패턴 (static pre-load):**
```python
# 분석 전에 데이터 로드 — LLM이 무엇을 볼지 미리 결정됨
ohlcv = load_ohlcv_with_provider("005930.KS", "1y")
advisor_result = await orchestrator.aanalyze("005930.KS", {"ohlcv": ohlcv})
```

**AI-native 패턴 (tool-use):**
```python
# LLM이 추론 중 필요한 데이터를 스스로 결정
system = "You are a news sentiment advisor. Use tools to fetch real-time data."
tools = [GET_PRICE_HISTORY, GET_COMPANY_NEWS, GET_FUNDAMENTALS]

# Round 1: Claude decides to call get_company_news
# Round 2: Claude decides to call get_fundamental_metrics
# Round 3: end_turn → advisory verdict
advisor_result = await claude.acall_with_tools(system, messages, tools)
```

**현재 `ClaudeClient`의 갭:**
```python
# 현재: tools= 전달은 되지만 tool_use 응답을 처리하지 못함
async def acall(self, *, system, messages, tools=None, ...) -> CallResult:
    message = await client.messages.create(..., tools=tools)
    return self._build_call_result(message, prompt_hash)
    # ← tool_use stop_reason 무시! text block만 추출
```

### B2. Cross-Domain Rationale (Novelty: 4)

**수술실 AR 글래스 → LLM 어드바이저**

전통적 의사는 수술 전 차트를 읽고 수술한다(static pre-load). 현대 AR 수술 시스템은 수술 *중* 필요한 데이터를 음성 명령으로 쿼리한다 — "혈압 지금 보여줘", "약물 상호작용 체크해줘."

현재 어드바이저는 분석 전에 `load_ohlcv_with_provider()`로 OHLCV를 로드하는 전통적 방식이다. AI-native 패턴은 어드바이저가 "이 뉴스 분석에 펀더멘털이 필요하다"고 판단할 때 그 순간 `get_fundamental_metrics("AAPL")` tool을 호출하는 것이다.

이 패턴이 현재 시스템에 맞는 이유: `ClaudeClient`가 이미 `tools=` 파라미터를 가지고 있고, OpenBB는 이미 `data_providers.py`의 `ALLOWED_PROVIDERS`에 있으며, 우리는 agentic loop만 추가하면 된다.

### B3. 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-1 | `ClaudeClient.acall_with_tools()` — tool_use agentic loop (max_tool_rounds=5) | P0 |
| FR-2 | `tool_schemas.py` — 4개 OpenBB tool 정의 (JSON schema) | P0 |
| FR-3 | `tool_executor.py` — OpenBB 함수 호출, PIT 가드, 결과 JSON 직렬화 | P0 |
| FR-4 | `OPENBB_TOOLS_ENABLED=false` 기본값 — 기존 동작 보존 | P0 |
| FR-5 | NewsSentimentAgent — `OPENBB_TOOLS_ENABLED=true` 시 news/price tools 주입 | P1 |
| FR-6 | MacroRegimeAgent — `OPENBB_TOOLS_ENABLED=true` 시 macro/economic tools 주입 | P1 |
| FR-7 | tool result 길이 ≤ 2000자 truncation (token 예산 보호) | P0 |
| FR-8 | OpenBB 미설치 시 tool 반환: `{"status": "unavailable", "error": "openbb not installed"}` | P0 |
| FR-9 | PIT 가드: `as_of` 지정 시 `end_date > as_of`인 tool call 차단 | P0 |
| FR-10 | tool call 비용을 `AdvisoryOutput.cost_usd`에 합산 | P1 |

### B4. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-1 | `OPENBB_TOOLS_ENABLED=false` 시 기존 `acall()` 코드 경로 100% 동일 |
| NFR-2 | 어드바이저 추론 지연 증가 ≤ 500ms (tool call round-trip 허용 범위) |
| NFR-3 | `advisory_score ∈ [-1,+1]` 불변 — tool call이 score 계산 로직에 영향 없음 |
| NFR-4 | `screening_output_only=True` 유지 |
| NFR-5 | PIT `as_of` 가드 보존 — tool executor에서 `end_date ≤ as_of` 강제 |

---

## C. UI/UX Plan

### C1. Information Architecture

```
어드바이저 Tool Call 추적 (운영자)
  ├─ audit_log/advisor.jsonl (기존) + tool_call 이벤트 추가
  ├─ MLflow span: advisor_call → tool_call (nested span)
  └─ 로그: "[OpenBB Tool] name=get_company_news ticker=AAPL elapsed=234ms"
```

### C2. 어드바이저 Tool-Use 흐름

```
NewsSentimentAgent.analyze("AAPL", ctx)
  1. ctx에 as_of="2026-05-29" 포함
  2. ClaudeClient.acall_with_tools(
         system=news_system_prompt,
         messages=[{"role":"user","content":...}],
         tools=NEWS_TOOLS,       ← [get_company_news, get_price_history]
         as_of="2026-05-29"      ← PIT 가드 전달
     )

  Round 1: Claude → {"type":"tool_use","name":"get_company_news","input":{"symbol":"AAPL","limit":10}}
    ToolExecutor: obb.news.company("AAPL", limit=10, end_date="2026-05-29")
    Result: {"articles":[{"title":"...", "date":"2026-05-28"},...]}

  Round 2: Claude → {"type":"tool_use","name":"get_price_history","input":{"symbol":"AAPL","start_date":"2026-05-01"}}
    ToolExecutor: obb.equity.price.historical("AAPL", start_date="2026-05-01", end_date="2026-05-29")
    Result: {"ohlcv":[...last 20 rows...]}

  Round 3: stop_reason="end_turn"
    → AdvisoryOutput(score=0.3, confidence=0.7, rationale="...based on news and price data...", tool_calls_made=2, cost_usd=0.004)
```

### C3. Screens (로그/출력)

| Screen | 출력 예시 |
|--------|----------|
| 도구 활성 로그 | `[OpenBB Tool] get_company_news AAPL limit=10 elapsed=187ms status=ok` |
| PIT 가드 차단 | `[OpenBB Tool] BLOCKED: end_date 2026-06-01 > as_of 2026-05-29` |
| 미설치 fallback | `[OpenBB Tool] get_company_news: openbb not installed → fallback` |
| max_rounds 초과 | `[ClaudeClient] max_tool_rounds=5 exceeded — forcing end_turn` |
| tool_call audit_log | `{"ts":"...","event":"tool_call","name":"get_company_news","ticker":"AAPL","elapsed_ms":187,"cost_usd":0.0}` |

---

## D. System Architecture

### D1. 전체 구성도

```
Advisor.analyze(ticker, ctx)
  │
  ├─ OPENBB_TOOLS_ENABLED=false (기본)
  │    └─ ClaudeClient.acall(system, messages)
  │         → CallResult (기존 동일)
  │
  └─ OPENBB_TOOLS_ENABLED=true
       └─ ClaudeClient.acall_with_tools(system, messages, tools, as_of)
            │
            ├─ Round 1: messages.create(tools=[...])
            │    stop_reason="tool_use"
            │    └─ ToolExecutor.dispatch(name, input, as_of)
            │         └─ OpenBBProvider.call(name, **input)
            │              └─ obb.equity.price.historical(...) / obb.news.company(...)
            │
            ├─ Round 2: messages.create(messages + tool_results)
            │    stop_reason="end_turn"
            │
            └─ CallResult (acall과 동일 타입, tool_calls_metadata 추가)
```

### D2. 컴포넌트 경계

| 컴포넌트 | 책임 | 의존성 |
|----------|------|--------|
| `tool_schemas.py` | 4개 Anthropic JSON tool 정의 | 없음 (pure Python dict) |
| `tool_executor.py` | OpenBB 함수 호출, PIT 가드, JSON 직렬화, truncation | openbb (optional) |
| `agentic_loop.py` | tool_use 응답 처리 루프, max_rounds guard | ClaudeClient, tool_executor |
| `claude_client.py` (수정) | `acall_with_tools()` 신규 메서드 추가 | agentic_loop |
| `news_sentiment.py` (수정) | OPENBB_TOOLS_ENABLED 시 NEWS_TOOLS 주입 | tool_schemas |
| `macro_regime.py` (수정) | OPENBB_TOOLS_ENABLED 시 MACRO_TOOLS 주입 | tool_schemas |

### D3. agentic loop 상세 (Canonical Anthropic Pattern)

```python
# agentic_loop.py
async def run_tool_loop(
    client: Any,           # anthropic.AsyncAnthropic
    *,
    messages: list[dict],
    model: str,
    system: Any,
    tools: list[dict],
    executor: ToolExecutor,
    as_of: str | None = None,
    max_tool_rounds: int = 5,
    max_tokens: int = 4096,
) -> tuple[str, int, int, float]:  # text, tokens_in, tokens_out, cost_usd
    """Canonical Anthropic tool_use loop.

    Ordering invariant (API requirement):
    - tool_result blocks MUST appear before text in the same user message.
    """
    total_in = total_out = total_cost = 0
    for _round in range(max_tool_rounds + 1):
        response = await client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=messages, tools=tools,
        )
        total_in += _count_tokens(response.usage, "input_tokens")
        total_out += _count_tokens(response.usage, "output_tokens")

        if response.stop_reason == "end_turn":
            text = _extract_text_blocks(response.content)
            return text, total_in, total_out, total_cost

        if response.stop_reason == "tool_use":
            # Append assistant content first
            messages.append({"role": "assistant", "content": _serialize_content(response.content)})
            # Collect and execute all tool calls
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    result_str, cost = await executor.dispatch(
                        name=block.name,
                        input_params=block.input,
                        as_of=as_of,
                    )
                    total_cost += cost
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,   # JSON string ≤ 2000 chars
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break  # max_tokens, error, etc.

    # max_rounds exceeded — force end by returning accumulated text
    logger.warning("[ClaudeClient] max_tool_rounds=%d exceeded", max_tool_rounds)
    return _extract_text_blocks(response.content), total_in, total_out, total_cost
```

---

## E. Data Model & API Contract

### E1. Tool 스키마 (4개)

#### Tool 1: `get_price_history`
```python
GET_PRICE_HISTORY = {
    "name": "get_price_history",
    "description": (
        "Fetch OHLCV price history for a stock symbol. "
        "Use when you need recent price trends, volatility, or momentum. "
        "Returns up to 60 trading days of daily OHLCV data."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock ticker (e.g. 'AAPL', '005930.KS')"
            },
            "start_date": {
                "type": "string",
                "description": "Start date YYYY-MM-DD. Max 60 days before today."
            },
        },
        "required": ["symbol"],
    },
}
```

#### Tool 2: `get_company_news`
```python
GET_COMPANY_NEWS = {
    "name": "get_company_news",
    "description": (
        "Fetch recent news headlines for a stock symbol. "
        "Use when you need to assess current sentiment, events, or announcements. "
        "Returns up to 15 most recent articles."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock ticker"},
            "limit": {"type": "integer", "description": "Max articles, 1-15", "default": 10},
        },
        "required": ["symbol"],
    },
}
```

#### Tool 3: `get_fundamental_metrics`
```python
GET_FUNDAMENTAL_METRICS = {
    "name": "get_fundamental_metrics",
    "description": (
        "Fetch key fundamental metrics: P/E, P/B, debt_to_equity, "
        "gross_margin, ROE, dividend_yield. "
        "Use when evaluating valuation or financial health."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock ticker"},
            "period": {"type": "string", "enum": ["annual", "quarter"], "default": "annual"},
        },
        "required": ["symbol"],
    },
}
```

#### Tool 4: `get_macro_indicators`
```python
GET_MACRO_INDICATORS = {
    "name": "get_macro_indicators",
    "description": (
        "Fetch macro economic indicators: VIX, T10Y2Y (yield curve), "
        "DXY (dollar index). Use when assessing macro regime context."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "indicators": {
                "type": "array",
                "items": {"type": "string", "enum": ["vix", "t10y2y", "dxy"]},
                "description": "Which indicators to fetch",
                "default": ["vix", "t10y2y"],
            },
        },
        "required": [],
    },
}
```

### E2. Tool Response 형식

모든 tool responses는 JSON string (≤ 2000자):

```python
# 성공
'{"status": "ok", "symbol": "AAPL", "rows": 20, "data": [{"date":"2026-05-28","close":212.5,...}]}'

# OpenBB 미설치
'{"status": "unavailable", "error": "openbb not installed. Install with: pip install openbb"}'

# PIT 가드 차단
'{"status": "blocked", "reason": "end_date 2026-06-01 exceeds as_of 2026-05-29"}'

# 데이터 없음
'{"status": "no_data", "symbol": "AAPL", "message": "No data returned for period"}'

# 오류
'{"status": "error", "error": "rate limit exceeded"}'
```

### E3. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OPENBB_TOOLS_ENABLED` | `false` | `true` → tool-use 활성화 |
| `OPENBB_TOOL_TIMEOUT_SEC` | `10` | 단일 tool call 타임아웃 |
| `OPENBB_MAX_TOOL_ROUNDS` | `5` | agentic loop 최대 반복 |
| `OPENBB_TOOL_RESULT_MAX_CHARS` | `2000` | tool result 최대 문자 수 |
| `OPENBB_NEWS_TOOLS_ENABLED` | `true` (if OPENBB_TOOLS_ENABLED=true) | NewsSentimentAgent tools |
| `OPENBB_MACRO_TOOLS_ENABLED` | `true` (if OPENBB_TOOLS_ENABLED=true) | MacroRegimeAgent tools |

### E4. `ClaudeClient` API 확장

```python
# claude_client.py 신규 메서드
async def acall_with_tools(
    self,
    *,
    system: str | list[dict[str, Any]] | None,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    as_of: str | None = None,
    max_tool_rounds: int = 5,
    max_tokens: int | None = None,
) -> CallResult:
    """Async call with Anthropic tool_use agentic loop.

    기존 acall()과 동일한 CallResult를 반환. tool_use 응답을 처리하는
    agentic loop를 추가. OPENBB_TOOLS_ENABLED=false일 때는 acall()로 fallback.
    """
```

---

## F. Repo/Package Structure

### F1. Target Tree

```
src/stock_rtx4060/advisors/
├── claude_client.py              ← acall_with_tools() 신규 메서드 추가
├── news_sentiment.py             ← OPENBB_TOOLS_ENABLED 시 NEWS_TOOLS 주입
├── macro_regime.py               ← OPENBB_TOOLS_ENABLED 시 MACRO_TOOLS 주입
└── openbb_tools/
    ├── __init__.py               ← 공개 API: OPENBB_TOOLS, tool_sets
    ├── tool_schemas.py           ← 4개 Anthropic tool JSON 스키마
    ├── tool_executor.py          ← OpenBB 함수 호출 + PIT 가드 + truncation
    └── agentic_loop.py           ← tool_use 응답 처리 루프

tests/
├── test_openbb_tool_schemas.py   ← 신규: schema 유효성 검증
├── test_openbb_tool_executor.py  ← 신규: PIT 가드, truncation, graceful
├── test_openbb_agentic_loop.py   ← 신규: 루프 동작, max_rounds 초과
├── test_claude_client_tools.py   ← 신규: acall_with_tools 통합
└── test_news_sentiment_tools.py  ← 신규: tools 주입 시 어드바이저 동작
```

### F2. 벤치마크 기반 패턴

| 패턴 | 출처 | 적용 |
|------|------|------|
| tool_use agentic loop | Anthropic 공식 docs (platform.claude.com, 2025-current) | `agentic_loop.py` canonical pattern |
| max_iterations guard | Augment Code Claude Agent SDK (2025) | `max_tool_rounds=5` + RuntimeError |
| tool_result ordering | Temporal AI cookbook (2026-01-16) | `tool_result` before `text` invariant |
| tool description quality | Anthropic Engineering (2025-09-11) | tool descriptions에 "When to use" 명시 |
| Native vs MCP 선택 | Anthropic Advanced Tool Use (2025-11-24) | 고정 툴셋 → native tool_use 선택 근거 |
| defer_loading (미래) | Anthropic Engineering (2025-11-24) | Phase 2: 대규모 tool 카탈로그 확장 시 |

---

## G. Implementation Plan

### G0. Why This Works (Cross-Domain Rationale — Novelty: 4)

**수술실 AR 글래스 → 추론 중 tool call**

전통 의사(현재 어드바이저)는 수술 전 차트를 읽고 들어가서 기억에 의존해 수술한다. 현대 수술 로봇(AI-native 어드바이저)는 수술 *중* "이 부위 혈관 지도 표시해" 같은 명령을 실시간 발행한다.

현재 시스템은 분석 실행 전 `load_ohlcv_with_provider()`로 데이터를 고정 주입하지만, tool_use 패턴에서는 뉴스 어드바이저가 "5월 AAPL 관련 리콜 뉴스 있나?" 또는 "지난주 삼성전자 주가 흐름 보여줘"를 추론 *중간에* 결정한다. 이는 분석의 맥락 민감도(context-sensitivity)를 근본적으로 높인다.

### G1. Epics

| Epic | 제목 | 기간 |
|------|------|------|
| E1 | Tool 스키마 + Executor 기초 | Week 1 |
| E2 | ClaudeClient agentic loop | Week 1~2 |
| E3 | 어드바이저 통합 | Week 2~3 |
| E4 | 테스트 + CI + 문서 | Week 3~4 |

### G2. Stories

**E1: Tool 스키마 + Executor**
- S1.1: `tool_schemas.py` — 4개 tool JSON 스키마 정의
- S1.2: `tool_executor.py` — `dispatch(name, input_params, as_of)` 메서드
- S1.3: `tool_executor.py` — OpenBB provider wrappers (price/news/fundamentals/macro)
- S1.4: `tool_executor.py` — PIT 가드 (`end_date > as_of` → blocked status)

**E2: ClaudeClient agentic loop**
- S2.1: `agentic_loop.py` — `run_tool_loop()` 구현 (canonical Anthropic pattern)
- S2.2: `agentic_loop.py` — `max_tool_rounds` guard + WARNING 로그
- S2.3: `claude_client.py` — `acall_with_tools()` 신규 메서드 추가
- S2.4: `claude_client.py` — `acall_with_tools()` MLflow span 통합 (기존 `_wrap_with_mlflow_span` 패턴)

**E3: 어드바이저 통합**
- S3.1: `news_sentiment.py` — `OPENBB_TOOLS_ENABLED` 환경변수 체크, NEWS_TOOLS 주입
- S3.2: `macro_regime.py` — `OPENBB_TOOLS_ENABLED` 체크, MACRO_TOOLS 주입
- S3.3: `news_sentiment.py` — tool call 비용을 `AdvisoryOutput.cost_usd`에 합산
- S3.4: `audit_log` — `tool_call` 이벤트 기록 (name, ticker, elapsed_ms)

**E4: 테스트 + CI**
- S4.1~S4.5: 5개 테스트 파일 작성

### G3. PR Plan

| PR | 번호 | 제목 | 파일 | 롤백 |
|----|------|------|------|------|
| PR-1 | `chore(P6): pin openbb>=4.3 as optional dep in requirements.in` | `requirements.in` | 줄 삭제 |
| PR-2 | `feat(P6): add advisors/openbb_tools/ — tool_schemas.py with 4 tool definitions` | `advisors/openbb_tools/tool_schemas.py` | 파일 삭제 |
| PR-3 | `feat(P6): add tool_executor.py — OpenBB dispatch + PIT guard + truncation` | `advisors/openbb_tools/tool_executor.py` | 파일 삭제 |
| PR-4 | `feat(P6): add agentic_loop.py — canonical Anthropic tool_use loop (max_rounds=5)` | `advisors/openbb_tools/agentic_loop.py` | 파일 삭제 |
| PR-5 | `feat(P6): add ClaudeClient.acall_with_tools() — agentic loop entry point` | `advisors/claude_client.py` | `git revert` |
| PR-6 | `feat(P6): update NewsSentimentAgent — inject NEWS_TOOLS when OPENBB_TOOLS_ENABLED=true` | `advisors/news_sentiment.py` | `git revert` |
| PR-7 | `feat(P6): update MacroRegimeAgent — inject MACRO_TOOLS when OPENBB_TOOLS_ENABLED=true` | `advisors/macro_regime.py` | `git revert` |
| PR-8 | `feat(P0): audit_log tool_call events + MLflow span for tool calls` | `advisors/openbb_tools/tool_executor.py`, `advisors/claude_client.py` | `git revert` |
| PR-9 | `test(P6): comprehensive tests — schemas, executor, loop, advisor integration` | `tests/test_openbb_*.py` (5개) | 파일 삭제 |
| PR-10 | `docs: CLAUDE.md + README — OpenBB tool-use guide + Key Invariants update` | `CLAUDE.md`, `README.md` | `git revert` |

### G4. Feature Flags

| 플래그 | 기본값 | 효과 |
|--------|--------|------|
| `OPENBB_TOOLS_ENABLED=false` | `false` | 기존 `acall()` 경로 100% 유지 |
| `OPENBB_MAX_TOOL_ROUNDS=5` | `5` | 루프 상한 (비용 제어) |
| `OPENBB_TOOL_RESULT_MAX_CHARS=2000` | `2000` | 토큰 예산 보호 |

---

## H. Testing Strategy

### H1. Test Pyramid

```
E2E (1개)
  └─ test_news_sentiment_tools.py::test_news_advisor_with_mock_tool_call
       └─ respx mock + tool_use 응답 fixture → AdvisoryOutput 전체 흐름

Integration (3개)
  ├─ test_claude_client_tools.py (acall_with_tools 통합)
  ├─ test_openbb_agentic_loop.py (루프 동작)
  └─ test_openbb_tool_executor.py (PIT 가드 + OpenBB mock)

Unit (6개)
  ├─ test_openbb_tool_schemas.py (스키마 유효성)
  ├─ test_openbb_tool_executor_pit_guard.py (PIT 블로킹)
  ├─ test_openbb_tool_executor_graceful.py (미설치 fallback)
  ├─ test_openbb_tool_executor_truncation.py (2000자 제한)
  ├─ test_openbb_agentic_loop_max_rounds.py (max_rounds 초과)
  └─ test_acall_with_tools_disabled.py (OPENBB_TOOLS_ENABLED=false)
```

### H2. 핵심 테스트 케이스

| 테스트 | 검증 내용 |
|--------|----------|
| `test_tool_schemas_valid_anthropic_format` | `name`, `description`, `input_schema` 필드 존재 + required schema |
| `test_acall_with_tools_disabled_uses_acall` | `OPENBB_TOOLS_ENABLED=false` → `acall()` 코드 경로 동일 |
| `test_agentic_loop_single_round` | tool_use 1회 + end_turn → `CallResult.text` 반환 |
| `test_agentic_loop_max_rounds_exceeded` | 5회 tool_use 후 WARNING + 강제 종료 |
| `test_executor_pit_guard_blocks_future` | `as_of="2026-05-29"`, `end_date="2026-06-01"` → `status=blocked` |
| `test_executor_graceful_no_openbb` | openbb 미설치 → `status=unavailable` (예외 없음) |
| `test_executor_truncation` | 응답 3000자 → 2000자 truncation |
| `test_news_agent_injects_tools_when_enabled` | `OPENBB_TOOLS_ENABLED=true` → `acall_with_tools` 호출 |
| `test_news_agent_no_tools_when_disabled` | `OPENBB_TOOLS_ENABLED=false` → `acall` 호출 |
| `test_tool_result_ordering_invariant` | tool_result 블록이 text 블록보다 먼저 messages에 추가 |

### H3. CI Gates

| Gate | 조건 |
|------|------|
| `OPENBB_TOOLS_ENABLED=false` | CI 기본값 — OpenBB 미설치 시 통과 |
| `test_acall_with_tools_disabled_uses_acall` | CI 필수 통과 |
| `test_executor_graceful_no_openbb` | CI 필수 통과 |
| `pytest --cov-fail-under=75` | 기존 유지 |

### H4. 테스트 데이터 (fixtures)

```python
# tests/fixtures/openbb_tools/
# tool_use_response.json  — Anthropic tool_use 응답 fixture
# tool_end_turn.json      — stop_reason="end_turn" 응답 fixture
# openbb_price_result.json — mock OpenBB price data
# openbb_news_result.json  — mock OpenBB news data
```

---

## I. Observability & Operations

### I1. 로깅

```python
# tool_executor.py
_LOGGER = get_logger("advisors.openbb_tools")

_LOGGER.info(
    "[OpenBB Tool] name=%s symbol=%s elapsed_ms=%.0f status=%s",
    name, symbol, elapsed * 1000, status
)
_LOGGER.warning("[OpenBB Tool] PIT guard: end_date %s > as_of %s", end_date, as_of)
_LOGGER.debug("[OpenBB Tool] result truncated: %d → 2000 chars", original_len)
```

### I2. audit_log/advisor.jsonl (tool_call 이벤트 추가)

```json
{
  "ts": "2026-05-29T10:00:00Z",
  "ticker": "AAPL",
  "agent": "news_sentiment",
  "event": "tool_call",
  "tool_name": "get_company_news",
  "tool_input": {"symbol": "AAPL", "limit": 10},
  "elapsed_ms": 187,
  "status": "ok",
  "result_chars": 1843
}
```

### I3. MLflow 트레이싱 (기존 span 확장)

```python
# claude_client.py — _wrap_with_mlflow_span 확장
with mlflow.start_span(name="advisor_call", span_type="LLM") as span:
    # 기존 span inputs/outputs 유지
    span.set_attributes({
        "tool_rounds": tool_rounds,
        "tool_calls_made": tool_calls_count,
        "openbb_tools_enabled": _OPENBB_TOOLS_ENABLED,
    })
```

### I4. 런북

```bash
# OpenBB tools 활성화
export OPENBB_TOOLS_ENABLED=true

# 단일 어드바이저 테스트
python -c "
import asyncio
from stock_rtx4060.advisors.news_sentiment import NewsSentimentAgent
agent = NewsSentimentAgent()
result = asyncio.run(agent.analyze('AAPL', {}))
print(f'score={result.score} cost={result.cost_usd:.4f}')
"

# tool call 로그 확인
tail -f audit_log/advisor.jsonl | python -m json.tool | grep tool_call

# 비용 모니터링
python -c "
import json
total = sum(e.get('cost_usd', 0) for l in open('audit_log/advisor.jsonl') for e in [json.loads(l)])
print(f'Total advisor cost: \${total:.4f}')
"

# OpenBB tools 비활성화 (롤백)
export OPENBB_TOOLS_ENABLED=false
```

---

## J. Error Handling & Recovery

### J1. 오류 분류

| 오류 | 처리 방식 |
|------|----------|
| OpenBB 미설치 | `{"status": "unavailable"}` 반환 (예외 없음) |
| OpenBB rate limit | `{"status": "error", "error": "rate limit"}` + WARNING 로그 |
| PIT 가드 차단 | `{"status": "blocked"}` 반환 + WARNING 로그 |
| tool result 2000자 초과 | truncation + DEBUG 로그 |
| max_tool_rounds 초과 | WARNING + 강제 end_turn + 마지막 텍스트 반환 |
| `tool_result` 순서 오류 (API 400) | agentic_loop에서 `tool_result` blocks를 항상 먼저 정렬 |
| 어드바이저 API 오류 | 기존 `_retryable_error_classes()` 재시도 동작 유지 |

### J2. PIT 가드 강제 로직

```python
# tool_executor.py — PIT guard
def _enforce_pit(params: dict, as_of: str | None) -> str | None:
    """Returns an error string if the request violates PIT constraints."""
    if as_of is None:
        return None
    end_date = params.get("end_date") or params.get("date")
    if end_date and end_date > as_of:
        return json.dumps({
            "status": "blocked",
            "reason": f"end_date {end_date} exceeds as_of {as_of}"
        })
    # Always inject end_date <= as_of even if not provided
    params["end_date"] = as_of
    return None
```

### J3. 멱등성

- `acall_with_tools()`: 동일한 messages + tools로 재호출 → 동일 결과 (LLM 확률적 특성 제외)
- `tool_executor.dispatch()`: 동일한 입력 → 동일한 OpenBB 응답 (market data는 시점 의존)
- audit log: `ts + event + tool_name` 조합으로 중복 체크 가능

---

## K. Dependencies, Security, Risks

### K1. 의존성

| 패키지 | 버전 | 용도 | 비고 |
|--------|------|------|------|
| `openbb` | `>=4.3` (optional) | tool executor backend | 미설치 시 graceful fallback |
| `anthropic` | `>=0.40` (기존) | tool_use API | 버전 업 없음 |
| `httpx` | `>=0.27` (기존) | async HTTP | 버전 업 없음 |

**신규 필수 의존성: 없음** — openbb는 optional.

### K2. 보안

| 위험 | 대응 |
|------|------|
| LLM이 임의 데이터 소스 쿼리 가능 | tool 화이트리스트 4개만 — 새 tool 추가 시 PR 필요 |
| tool call로 as_of 이후 데이터 노출 | PIT 가드 — tool executor에서 `end_date ≤ as_of` 강제 |
| tool result에 내부 API 키 노출 | tool executor는 OpenBB 공개 데이터만 (무료 provider 우선) |
| max_tool_rounds 없으면 무한 루프 | `max_tool_rounds=5` 하드 제한 |
| tool call 비용 폭증 | `OPENBB_MAX_TOOL_ROUNDS=5` + 비용 audit 로그 |

### K3. Risk Register

| # | 위험 | 확률 | 영향 | 대응 |
|---|------|------|------|------|
| R1 | OpenBB API 변경 (v4.x → v5.x) | 중 | 중 | `openbb>=4.3` 핀 + tool_executor의 OpenBB 호출만 교체 필요 |
| R2 | Anthropic tool_use API 변경 (agentic loop) | 낮음 | 중 | `agentic_loop.py` 분리 → 수정 범위 최소화 |
| R3 | tool call 비용 증가로 예산 초과 | 중 | 중 | `max_tool_rounds=5` + `OPENBB_TOOLS_ENABLED=false` 즉시 롤백 |
| R4 | OpenBB free tier rate limit | 중 | 낮음 | `status=error` graceful fallback → LLM이 데이터 없이 계속 진행 |
| R5 | `tool_result` ordering 실수 → API 400 | 낮음 | 높음 | `agentic_loop.py` sorting guard + 테스트 |
| R6 | KRX 티커 (005930.KS) OpenBB 미지원 | 중 | 중 | `get_company_news` KRX 응답 없으면 `no_data` fallback |

### K4. Change Control

- `ClaudeClient`: additive `acall_with_tools()` 신규 메서드 — 기존 `call()`, `acall()` 변경 없음
- `NewsSentimentAgent`, `MacroRegimeAgent`: flag-gated, `OPENBB_TOOLS_ENABLED=false` 기본
- Key Invariants 전부 보존

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| OpenBB MCP server | PyPI | openbb-mcp-server v1.4.1 | pypi.org/project/openbb-mcp-server | 2026-05-26 | OpenBB 38k stars | MCP server package, option B reference |
| OpenBB v4.7 | GitHub | OpenBB releases | github.com/OpenBB-finance/OpenBB | 2025-10-08 | 38k+ stars | MCP configurability, Python 3.13 |
| tool_use agentic loop | Anthropic | Handling stop reasons docs | platform.claude.com | 2025 (current) | Official | Canonical while-loop pattern |
| max_rounds guard | Augment | Claude Agent SDK Python | augmentcode.com | 2025 | — | `max_iterations` guard pattern |
| tool_result ordering | Temporal | AI cookbook | docs.temporal.io | 2026-01-16 | — | `tool_result` before `text` invariant |
| Native vs MCP | Anthropic Engineering | Advanced Tool Use | anthropic.com/engineering | 2025-11-24 | Official | Native tool_use better for fixed toolsets |
| Tool description quality | Anthropic Engineering | Writing Effective Tools | anthropic.com/engineering | 2025-09-11 | Official | "When to use" 명시 가이드 |
| OpenBB price API | OpenBB Docs | equity/price/historical | docs.openbb.co | 2025 (current) | — | OHLCV endpoint signature |
| OpenBB news API | OpenBB Docs | news/company | docs.openbb.co | 2025 (current) | — | news endpoint signature |
| OpenBB fundamentals | OpenBB Docs | equity/fundamental/metrics | docs.openbb.co | 2025 (current) | — | P/E, P/B, ROE endpoint |
| Wave 4 리포트 (내부) | Internal | 20260529_project-upgrade-report-wave4.md | 내부 파일 | 2026-05-29 | — | Surprise Pick ★3, SurpriseScore 5.33 |

### ㅋ2. AMBER_BUCKET

없음 — 모든 핵심 evidence 날짜/출처 확인.

### ㅋ3. Benchmarked Repo Notes

| Repo | Stars | 패턴 | 적용 |
|------|-------|------|------|
| OpenBB-finance/OpenBB | 38k | `obb.equity.price.historical()` API | tool executor 구현 |
| anthropic/anthropic-sdk-python | 10k+ | `tools=`, tool_use handling | agentic_loop.py 설계 |
| anthropic.com Engineering | Official | Advanced tool use, defer_loading | Phase 2 로드맵 |
| NirDiamant/Agent_Memory_Techniques | — | agentic patterns (ref) | tool loop 패턴 비교 |

### ㅋ4. 용어집

| 용어 | 설명 |
|------|------|
| tool_use | Anthropic API의 function calling 기능 — LLM이 도구 호출을 요청 |
| stop_reason | LLM 응답 종료 이유: `"end_turn"` (완료) 또는 `"tool_use"` (도구 호출 요청) |
| agentic loop | tool_use → execute → continue를 반복하는 while 루프 |
| MCP | Model Context Protocol — Anthropic의 도구 프로토콜 표준 (이 플랜에서는 native tool_use 사용) |
| PIT 가드 | Point-in-Time 가드: `as_of` 이후 데이터 조회 차단 |
| Native tool_use | OpenBB를 직접 Python 함수로 래핑 (MCP server 없이) |
| CallResult | `ClaudeClient.call()` / `acall()` 반환 타입 |

---

## Verification Gate

| Gate | 항목 | 상태 |
|------|------|------|
| Gate 0 (Dry-run) | 코드 변경 없음 | ✅ |
| Gate 1 (Evidence) | Anthropic 공식 2025-11-24 + OpenBB 2026-05-26 — 2개 이상 확인 | ✅ |
| Gate 2 (PR plan ≥6) | PR 10개 | ✅ |
| Gate 3 (Tests) | 테스트 케이스 명세 완비 (10개 핵심) | ✅ |
| Gate 4 (Rollout/Rollback) | `OPENBB_TOOLS_ENABLED=false` + `git revert` | ✅ |
| Gate 5 (KPI 정의) | tool call 비용, PIT 준수, 기존 테스트 100% | ✅ |
| Gate 6 (Safety) | `advisory_score` 불변, PIT 가드, `screening_output_only=True` | ✅ |
| AMBER check | 없음 | ✅ ZERO 없음 |

**최종 판정: Go ✅**

### Apply Gates

- **Gate 0**: 현재 플랜 문서. 코드 수정 없음.
- **Gate 1**: 변경 파일 — `claude_client.py`, `news_sentiment.py`, `macro_regime.py` + 신규 4개 파일
- **Gate 2**: PR-1 시작 전 사용자 승인 필요
- **Gate 3**: `OPENBB_TOOLS_ENABLED=false` 모든 환경 기본값
- **Gate 4**: Rollback = `OPENBB_TOOLS_ENABLED=false` (즉시) 또는 `git revert` PR-5,6,7
