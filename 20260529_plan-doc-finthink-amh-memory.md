# PLAN_DOC — FinThink AMH-Grounded Hierarchical Memory (R-Mem)
**v1.0 | 2026-05-29 | skill: project-plan v2.2 | project: stock_1901 / stock_rtx4060**

> ⚠️ **AMBER 주의**: FinThink(openreview.net/forum?id=vm7xqrU345)는 ICLR 2026 *제출* 상태 (2025-09-19, 아직 채택 미확인).
> R-Mem 아키텍처는 설계 *영감*으로만 활용. **실제 구현은 LangMem(confirmed 2025-02-20) + DuckDB + LangGraph**로 수행.
> AMBER 2개 이상 동시 발생 없음 → ZERO 미발동, 플랜 진행.

---

## A. Executive Summary

### 목표
현재 **stateless** 3-advisor 오케스트레이터에 **AMH(Adaptive Markets Hypothesis) 기반 계층 메모리 레이어**를 추가한다. 적응적 시장 가설 핵심 원리: "무엇이 한 regime에서 효과적이었는지를 기억하고, regime이 바뀌면 그 기억을 교체한다." 이를 통해 어드바이저가 bull/bear/sideways 각 체제에 맞는 과거 추론 체인을 참조하여 맥락 없는 반복 오류를 제거한다.

### 핵심 제약

| 제약 | 현황 | 해결책 |
|------|------|--------|
| FinThink AMBER | ICLR 2026 제출, 미채택 | R-Mem 구조 영감만 활용, LangMem으로 구현 |
| `AdvisoryOutput` frozen dataclass | 새 필드 추가 시 기존 코드 호환 필요 | 끝에 `default=""` optional 필드 additive 추가 |
| Orchestrator stateless 설계 | 매 호출 독립 | `memory_layer: MemoryLayer \| None = None` optional field |
| 기존 `advisory_score ∈ [-1,+1]` 불변 | 메모리가 점수 override 불가 | 메모리는 `context` 주입만 — score 계산 로직 무변경 |
| `screening_output_only=True` | 자동 매매 없음 | 메모리는 어드바이저 *입력*만 강화 |

### KPI

| Metric | 현재 | 목표 |
|--------|------|------|
| 어드바이저 컨텍스트 크기 | 0 (이전 기억 없음) | regime별 top-K 메모리 주입 (K≤5) |
| regime-tagged 메모리 쓰기 | 없음 | 매 `aanalyze()` 호출 후 자동 기록 |
| CWRM 라우팅 활성화 | 없음 (항상 shallow) | 신호 불일치 > threshold 시 deep path |
| STL 명제 생성 | 없음 | NewsSentiment 출력마다 logical proposition 1개 |
| 메모리 레이어 ON 시 기존 테스트 | N/A | 100% 기존 테스트 통과 (backward compat) |
| `memory_layer=None` 시 동작 | 기존과 동일해야 함 | 코드 경로 동일 확인 |

### 범위
- **In-scope**: `advisors/memory/` 신규 패키지, `AdvisoryOutput` additive 확장, `Orchestrator` memory hook, CWRM 라우팅, STL 명제, DuckDB 메모리 백엔드, MLflow 메트릭
- **Out-of-scope**: Graphiti 그래프 DB, PostgresStore 프로덕션 마이그레이션, 브로커 연동, 자동 weight 갱신(alpha ≥ 목표 달성 후 Phase 2 고려)

### 핵심 결정

| # | 결정 | 이유 |
|---|------|------|
| D1 | DuckDB를 메모리 백엔드로 사용 | 기존 P1 data lake와 동일 인프라, 추가 dep 없음 |
| D2 | `MemoryLayer=None` 기본값 (opt-in) | 기존 동작 100% 보존, CI 영향 없음 |
| D3 | regime_label을 `AdvisoryOutput`에 optional 필드로 추가 | `MacroRegimeAgent`가 이미 regime을 계산하므로 side-channel 불필요 |
| D4 | CWRM = 불일치 점수 기반 라우팅 (LLM call 없음) | 추가 LLM 비용 없이 라우팅 결정 |
| D5 | STL 명제 = 프롬프트 포맷 강제 (새 LLM call 없음) | `NewsSentimentAgent` system prompt 수정만 |
| D6 | 메모리 *쓰기*는 `aanalyze()` 직후, *결과* 업데이트는 deferred | forward return은 나중에 알 수 있으므로 outcome=None으로 먼저 저장 |

### 마일스톤

| 마일스톤 | 기간 | 완료 기준 |
|----------|------|-----------|
| M1: 데이터 모델 + 백엔드 | Week 1 | `RegimeMemory` DuckDB 스키마 + CRUD 테스트 통과 |
| M2: 계층 스토어 + CWRM + STL | Week 2 | `HierarchicalStore`, `CWRMRouter`, `STLProtocol` 유닛 테스트 통과 |
| M3: Orchestrator 통합 | Week 2~3 | `Orchestrator(memory_layer=...)` E2E + 기존 테스트 100% 통과 |
| M4: MLflow + 테스트 + 문서 | Week 3~4 | 커버리지 ≥80% (memory 모듈), CLAUDE.md 업데이트 |

---

## B. Context & Requirements

### B1. 문제 정의

**현재 한계:**
```
호출 1: Orchestrator.aanalyze("AAPL", ctx)
  → news=0.6, macro=-0.3(risk_off), devils=-0.2 → score=-0.02
  → [FORGET]

호출 2 (2주 후, 동일한 risk_off regime):
  → news=0.5, macro=-0.35(risk_off), devils=-0.1 → score=0.01
  → 2주 전 risk_off에서 devils가 "금리 인상 신호 무시" 오류를 범했던 사실을 모름
```

**목표 상태:**
```
호출 2 (2주 후):
  → MacroRegime: regime="risk_off" → 메모리 쿼리: "risk_off 시 AAPL 관련 과거 추론"
  → 메모리 주입: "risk_off #3: news 낙관이었지만 실제 -4.2% — 금리 민감도 과소평가"
  → DevilsAdvocate context에 과거 오류 패턴 포함 → 더 신중한 verdict
```

### B2. AMH (Adaptive Markets Hypothesis) 원리

| AMH 원리 | R-Mem 구현 | stock_1901 적용 |
|----------|-----------|----------------|
| 시장 참여자는 진화적으로 적응한다 | 어드바이저가 과거 추론 체인에서 학습 | `regime_memory.py`의 read/write |
| 같은 전략도 regime에 따라 효과가 다르다 | regime_label로 메모리를 태깅/필터링 | `get_relevant_memories(regime=current)` |
| 과거 성공 패턴이 새 regime에서 실패할 수 있다 | regime 전환 시 메모리 decay/archiving | `archive_stale_memories()` |
| 다중 에이전트 상호작용이 적응을 가속화 | 크로스-에셋 메모리 공유 | `get_cross_asset_memories(regime)` |

### B3. FinThink R-Mem → 구현 매핑

| FinThink 컴포넌트 | 구현 | 파일 |
|-----------------|------|------|
| R-Mem (Reasoning-Driven Hierarchical Memory) | `HierarchicalStore` (L1 단기 + L2 의미론 + L3 절차적) | `hierarchical_store.py` |
| CWRM (Context-aware Workflow for Reasoning) | `CWRMRouter` 불일치 점수 → shallow/deep 경로 | `cwrm_router.py` |
| STL (Sentiment-To-Logic) Protocol | `STLProtocol` 명제 추출 | `stl_protocol.py` |
| Cross-asset reflective memory | `get_cross_asset_memories()` | `regime_memory.py` |
| Regime-tagged storage | `regime_label` in `MemoryEntry` + DuckDB | `regime_memory.py` |

### B4. 기능 요구사항

| ID | 요구사항 | 우선순위 |
|----|----------|----------|
| FR-1 | `AdvisoryOutput`에 `regime_label: str = ""` optional 추가 (backward compat) | P0 |
| FR-2 | `RegimeMemory`: regime별 과거 추론 체인 + score 저장/조회 (DuckDB) | P0 |
| FR-3 | `HierarchicalStore`: L1(단기)/L2(의미론)/L3(절차적) 3계층 조회 | P1 |
| FR-4 | `CWRMRouter`: news vs macro 불일치 점수 계산 → shallow/deep 경로 결정 | P1 |
| FR-5 | `STLProtocol`: NewsSentiment 출력을 logical proposition으로 변환 | P1 |
| FR-6 | `Orchestrator`: `memory_layer=None` 기본, 설정 시 context 주입 | P0 |
| FR-7 | `MemoryLayer=None`일 때 기존 동작 100% 보존 | P0 |
| FR-8 | 메모리 쓰기: 매 `aanalyze()` 완료 후 자동 (outcome=None → deferred update) | P1 |
| FR-9 | `memory_layer.update_outcome(session_id, realized_pct)` — forward return 업데이트 | P2 |
| FR-10 | MLflow: regime별 메모리 count, retrieval hit rate 기록 | P2 |

### B5. 비기능 요구사항

| ID | 요구사항 |
|----|----------|
| NFR-1 | 기존 Key Invariants 전부 보존 (CLAUDE.md) |
| NFR-2 | `advisory_score ∈ [-1,+1]` — 메모리는 score 계산 무관 |
| NFR-3 | `screening_output_only=True` 유지 |
| NFR-4 | 메모리 레이어 추가 시 어드바이저 호출 지연 ≤ 50ms (retrieval) |
| NFR-5 | DuckDB 메모리 DB 크기: 기본 최대 10MB (max_entries=1000 per regime) |

---

## C. UI/UX Plan

### C1. Information Architecture

```
어드바이저 메모리 상태 (운영자 가시성)
  ├─ python main.py advisor-memory list [--regime REGIME] [--ticker TICKER]
  ├─ python main.py advisor-memory stats
  └─ audit_log/advisor_memory.jsonl (자동 기록)

Orchestrator 출력 (기존 + 확장)
  ├─ OrchestratorResult.advisory_score          ← 기존 (변경 없음)
  ├─ OrchestratorResult.confidence              ← 기존 (변경 없음)
  ├─ OrchestratorResult.outputs[].regime_label  ← 신규 optional
  └─ OrchestratorResult.memory_context_used     ← 신규 optional
```

### C2. 운영자 워크플로우

```
일별 추천 실행
  1. Orchestrator.aanalyze("005930.KS", ctx)
  2. [신규] MacroRegime 실행 → regime_label="risk_off"
  3. [신규] MemoryLayer.get_relevant_memories(ticker, regime="risk_off", k=5)
  4. [신규] CWRMRouter: news(+0.4) vs macro(-0.3) → disagreement=0.7 > threshold → deep path
  5. DevilsAdvocate context += {"memory_context": [...5개 과거 추론], "path": "deep"}
  6. [신규] MemoryLayer.write(session_id, ticker, regime, outputs, score)
  7. 기존 OrchestratorResult 반환 (구조 동일)

30거래일 후 (forward return 알게 됨)
  8. MemoryLayer.update_outcome(session_id, realized_return_pct=+2.1)
```

### C3. Screens (CLI 출력)

| Screen | 출력 예시 |
|--------|----------|
| `advisor-memory list` | `[risk_off] AAPL 2026-05-15: score=-0.12 outcome=-3.2% (devils: 금리 민감도 과소평가)` |
| `advisor-memory stats` | `L1: 12 entries, L2: 87 entries, L3: 3 procedures, regime_distribution: risk_off=45%` |
| `advisor-memory purge --before 2026-01-01` | `Purged 34 stale entries (regime_mismatch=18, expired=16)` |
| Orchestrator 로그 | `[MemoryLayer] regime=risk_off retrieved=5 path=deep elapsed=12ms` |

---

## D. System Architecture

### D1. 전체 구성도

```
Orchestrator.aanalyze(ticker, ctx)
│
├─ [Step 0: 신규] regime_prefetch_node (MacroRegime quick check, no LLM)
│     └─ regime_label = ctx.get("regime") or "unknown"
│
├─ [Step 1] news_node || macro_node (병렬 — 기존 동일)
│     └─ MacroRegimeAgent → AdvisoryOutput(regime_label="risk_off")  ← 신규 필드
│
├─ [Step 2: 신규] memory_inject_node
│     ├─ MemoryLayer.get_relevant_memories(ticker, regime_label, k=5)
│     ├─ CWRMRouter.route(news_out, macro_out) → "shallow" | "deep"
│     └─ STLProtocol.extract(news_out) → logical_proposition: str
│
├─ [Step 3] devils_node (기존 — context 풍부해짐)
│     └─ ctx["memory_context"] = [...memories]
│        ctx["routing_path"] = "deep"
│        ctx["news_proposition"] = "IF VIX>25 THEN bearish WITH 0.7"
│
├─ [Step 4] _blend (기존 동일)
│
└─ [Step 5: 신규] memory_write_node
      └─ MemoryLayer.write(session_id, ticker, regime_label, outputs, final_score)
```

### D2. 메모리 계층 (R-Mem 3-tier)

```
┌─────────────────────────────────────────────────────────┐
│ L3: Procedural Memory (절차적)                          │
│   — 어드바이저별 "이 regime에서는 X를 중시하라" 지침    │
│   — 느린 업데이트 (outcome 누적 후 batch 갱신)          │
│   — storage: DuckDB advisor_procedures 테이블           │
├─────────────────────────────────────────────────────────┤
│ L2: Semantic Memory (의미론적)                          │
│   — regime별 공통 패턴 ("risk_off에서 뉴스 낙관은 덫")  │
│   — 크로스-에셋 교훈 (AAPL 패턴 → MSFT에 주입)         │
│   — storage: DuckDB regime_semantic 테이블              │
├─────────────────────────────────────────────────────────┤
│ L1: Episodic Memory (에피소딕)                          │
│   — 개별 분석 세션: {reasoning_chain, score, outcome}   │
│   — regime_label + ticker 인덱싱                        │
│   — storage: DuckDB regime_episodic 테이블              │
└─────────────────────────────────────────────────────────┘
```

### D3. CWRM 라우팅 로직

```python
# cwrm_router.py — LLM call 없이 숫자 연산만
def route(news: AdvisoryOutput, macro: AdvisoryOutput) -> RoutingDecision:
    disagreement = abs(news.score - macro.score)
    conf_product = news.confidence * macro.confidence
    # 두 어드바이저가 확신을 갖고 반대 방향을 가리킬 때 → deep
    if disagreement > DEEP_THRESHOLD and conf_product > CONF_MIN:
        return RoutingDecision(path="deep", disagreement=disagreement)
    return RoutingDecision(path="shallow", disagreement=disagreement)
```

### D4. 컴포넌트 경계

| 컴포넌트 | 책임 | 외부 의존성 |
|----------|------|------------|
| `regime_memory.py` | DuckDB CRUD, regime-tagged 저장/조회 | duckdb, dataclasses |
| `hierarchical_store.py` | L1/L2/L3 조정, retrieval 순서 | regime_memory |
| `cwrm_router.py` | disagreement 점수, path 결정 | base.AdvisoryOutput |
| `stl_protocol.py` | sentiment → proposition 변환 | re, dataclasses |
| `memory_layer.py` | 공개 API, 4개 모듈 조정 | 위 4개 |
| `orchestrator.py` (수정) | memory hook 주입 | memory_layer |

---

## E. Data Model & API Contract

### E1. 데이터 모델

#### AdvisoryOutput 확장 (additive — frozen dataclass 끝에 default 필드 추가)
```python
# advisors/base.py — 기존 필드 이후에 추가
@dataclass(frozen=True)
class AdvisoryOutput:
    # ... 기존 필드들 (변경 없음) ...
    cost_usd: float
    # 신규 optional 필드 (keyword-only safe with default)
    regime_label: str = ""          # "risk_on" | "neutral" | "risk_off" | ""
    logical_proposition: str = ""   # STL Protocol 출력 (NewsSentiment only)
```

#### MemoryEntry (L1 에피소딕)
```python
@dataclass
class MemoryEntry:
    session_id: str          # UUID
    ticker: str
    ts: str                  # ISO 8601
    regime_label: str        # "risk_on" | "neutral" | "risk_off"
    final_score: float       # OrchestratorResult.advisory_score
    reasoning_chains: dict   # {agent_name: rationale}
    logical_proposition: str # STL 명제 (NewsSentiment)
    outcome_pct: float | None  # forward return %, None until updated
    layer: str = "L1"        # "L1" | "L2" | "L3"
```

#### DuckDB 스키마
```sql
-- regime_episodic (L1)
CREATE TABLE IF NOT EXISTS regime_episodic (
    session_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    ts TIMESTAMP NOT NULL,
    regime_label TEXT NOT NULL,
    final_score DOUBLE,
    reasoning_chains JSON,
    logical_proposition TEXT,
    outcome_pct DOUBLE,       -- NULL until updated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_episodic_regime_ticker ON regime_episodic(regime_label, ticker);

-- regime_semantic (L2)
CREATE TABLE IF NOT EXISTS regime_semantic (
    id TEXT PRIMARY KEY,
    regime_label TEXT NOT NULL,
    pattern_summary TEXT NOT NULL,  -- "risk_off에서 뉴스 낙관은 평균 -2.3%"
    evidence_count INT DEFAULT 1,
    avg_outcome_pct DOUBLE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- advisor_procedures (L3)
CREATE TABLE IF NOT EXISTS advisor_procedures (
    advisor_name TEXT NOT NULL,
    regime_label TEXT NOT NULL,
    procedure_text TEXT NOT NULL,   -- 어드바이저 system prompt 보완
    confidence DOUBLE DEFAULT 0.5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (advisor_name, regime_label)
);
```

### E2. Public API (memory_layer.py)

```python
class MemoryLayer:
    """Public API — injected into Orchestrator as optional field."""

    def get_relevant_memories(
        self,
        ticker: str,
        regime: str,
        k: int = 5,
    ) -> list[MemoryEntry]:
        """L1 에피소딕 + L2 의미론 retrieval, regime-gated."""

    def write(
        self,
        session_id: str,
        ticker: str,
        regime: str,
        outputs: list[AdvisoryOutput],
        final_score: float,
    ) -> None:
        """매 aanalyze() 완료 후 자동 호출."""

    def update_outcome(
        self,
        session_id: str,
        realized_return_pct: float,
    ) -> bool:
        """30거래일 후 forward return 업데이트."""

    def get_procedure(self, advisor_name: str, regime: str) -> str:
        """L3 절차적 메모리 조회 — 어드바이저 프롬프트 보완용."""

    def archive_stale(self, regime_shift_threshold_days: int = 90) -> int:
        """오래된 메모리 아카이브."""
```

### E3. CLI API (main.py 확장)

| 명령어 | 기능 |
|--------|------|
| `python main.py advisor-memory list [--regime R] [--ticker T] [--limit N]` | 메모리 목록 조회 |
| `python main.py advisor-memory stats` | regime별 통계 |
| `python main.py advisor-memory update-outcome --session S --return-pct F` | forward return 업데이트 |
| `python main.py advisor-memory purge --before DATE` | 오래된 메모리 삭제 |

### E4. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ADVISOR_MEMORY_ENABLED` | `false` | `true`로 설정 시 메모리 레이어 활성화 |
| `ADVISOR_MEMORY_DB_PATH` | `:memory:` | DuckDB 경로 (`:memory:` = 인메모리, 영속성 없음) |
| `ADVISOR_MEMORY_MAX_ENTRIES` | `1000` | regime별 최대 메모리 항목 |
| `CWRM_DEEP_THRESHOLD` | `0.5` | disagreement 점수 deep path 임계값 |
| `CWRM_CONF_MIN` | `0.3` | 신뢰도 곱 최소값 (deep path 조건) |

---

## F. Repo/Package Structure

### F1. Target Tree

```
src/stock_rtx4060/advisors/
├── base.py                          ← AdvisoryOutput: regime_label + logical_proposition 추가
├── macro_regime.py                  ← analyze() 반환값에 regime_label 채우기
├── news_sentiment.py                ← system prompt에 STL proposition 포맷 추가
├── orchestrator.py                  ← memory_layer hook + CWRM 라우팅
└── memory/
    ├── __init__.py                  ← 공개 API
    ├── regime_memory.py             ← DuckDB CRUD (L1 + L2 + L3)
    ├── hierarchical_store.py        ← 3계층 조정, retrieval 순서
    ├── cwrm_router.py               ← disagreement → routing decision
    ├── stl_protocol.py              ← sentiment → logical proposition
    └── memory_layer.py              ← public MemoryLayer class

tests/
├── test_advisor_regime_memory.py    ← 신규
├── test_advisor_hierarchical_store.py ← 신규
├── test_advisor_cwrm_router.py      ← 신규
├── test_advisor_stl_protocol.py     ← 신규
├── test_advisor_memory_layer.py     ← 신규
└── test_advisor_orchestrator_memory.py ← 기존 orchestrator 테스트 확장
```

### F2. 벤치마크 기반 패턴

| 패턴 | 출처 | 적용 |
|------|------|------|
| 3-tier memory (episodic/semantic/procedural) | LangMem (LangChain, 2025-02-20) | L1/L2/L3 계층 설계 |
| Regime-tagged storage | FinThink R-Mem (openreview, 2025-09-19) ⚠️ AMBER | DuckDB `regime_label` 인덱스 |
| Temporal knowledge graph | Graphiti (getzep, 20K stars, 2025-01) | L2 semantic pattern 업데이트 로직 영감 |
| Hybrid memory store | Mem0 (mem0ai, 90K stars, 2025) | L1+L2+L3 통합 인터페이스 설계 |
| `MemorySaver` namespace | LangGraph docs (LangChain, 2025) | `memory_layer.py` namespace 설계 |

---

## G. Implementation Plan

### G0. Why This Works (Cross-Domain Rationale — Novelty: 5)

**생태계 진화 이론 → 시장 어드바이저**

AMH(Lo 2004)는 금융 시장을 다윈적 생태계로 본다: "성공한 전략도 환경(regime)이 바뀌면 멸종한다." FinThink R-Mem은 이 원리를 LLM 어드바이저의 메모리 설계로 직역했다:

| 생태계 진화 | R-Mem/AMH 어드바이저 |
|------------|---------------------|
| 환경 = 생태 지위 | Regime = risk_on / risk_off / neutral |
| 생존한 개체의 행동 = 성공 전략 | 좋은 outcome을 낸 추론 체인 = L1 메모리 |
| 환경 변화 → 전략 무효화 | Regime shift → 해당 메모리 decay |
| 크로스 종 학습 | 크로스 에셋 메모리 (AAPL→MSFT 패턴 이전) |
| 개체군 집단 지성 | L2 semantic: 여러 에피소드의 공통 패턴 추출 |

현재 시스템에 맞는 이유: `MacroRegimeAgent`가 이미 `risk_on/neutral/risk_off` 분류를 하고 있고, `DevilsAdvocate`가 이미 `prior_outputs`를 `context`로 받는 구조라 — regime-gated 메모리 주입이 기존 데이터 흐름에 자연스럽게 맞물린다.

### G1. Epics

| Epic | 제목 | 기간 |
|------|------|------|
| E1 | AdvisoryOutput 확장 + MacroRegime regime_label 노출 | Week 1 |
| E2 | regime_memory.py + hierarchical_store.py (DuckDB 백엔드) | Week 1 |
| E3 | cwrm_router.py + stl_protocol.py | Week 2 |
| E4 | memory_layer.py + Orchestrator 통합 | Week 2 |
| E5 | CLI 확장 + MLflow 메트릭 | Week 3 |
| E6 | 테스트 + CI + 문서 | Week 3~4 |

### G2. Stories

**E1: AdvisoryOutput + MacroRegime**
- S1.1: `base.py` — `regime_label: str = ""`, `logical_proposition: str = ""` 추가 (keyword arg default)
- S1.2: `macro_regime.py` — `AdvisoryOutput(... regime_label=regime ...)` 반환
- S1.3: `news_sentiment.py` — system prompt에 STL proposition 포맷 요청 (`"proposition": "IF ... THEN ... WITH ..."`)

**E2: 메모리 백엔드**
- S2.1: `regime_memory.py` — DuckDB 스키마 생성, `write_episodic()`, `query_episodic(regime, ticker, k)`
- S2.2: `regime_memory.py` — `update_outcome()`, `archive_stale()`
- S2.3: `hierarchical_store.py` — L1+L2+L3 조정, `retrieve(ticker, regime, k)` 통합 메서드
- S2.4: `regime_memory.py` — L2 semantic 자동 패턴 추출 (10개 에피소드 누적 시 배치 요약)

**E3: CWRM + STL**
- S3.1: `cwrm_router.py` — `CWRMRouter.route(news, macro) → RoutingDecision`
- S3.2: `cwrm_router.py` — `CWRM_DEEP_THRESHOLD`, `CWRM_CONF_MIN` 환경변수 로드
- S3.3: `stl_protocol.py` — `STLProtocol.extract(output) → str` (regex 파싱 + fallback)
- S3.4: `stl_protocol.py` — proposition 포맷 검증 ("IF ... THEN ... WITH ..." 파싱)

**E4: MemoryLayer + Orchestrator**
- S4.1: `memory_layer.py` — `MemoryLayer` 클래스, `get_relevant_memories()`, `write()`, `update_outcome()`
- S4.2: `orchestrator.py` — `memory_layer: MemoryLayer | None = None` field 추가
- S4.3: `orchestrator.py` — `_fallback_run()` 메모리 주입 hook: `if self.memory_layer:`
- S4.4: `orchestrator.py` — `_langgraph_run()` memory_node 추가 (LangGraph path)

**E5: CLI + MLflow**
- S5.1: `main.py` — `advisor-memory` 서브커맨드 그룹
- S5.2: `memory_layer.py` — `log_to_mlflow()`: regime별 entry count, retrieval hit rate
- S5.3: alert_engine — "memory_layer: regime=X, retrieved=Y, path=Z" 로그 이벤트

**E6: 테스트 + 문서**
- S6.1~S6.5: 5개 테스트 파일 작성 (unit + integration)
- S6.6: `CLAUDE.md` 업데이트 — Key Invariants + 새 모듈 안내

### G3. PR Plan

| PR | 번호 | 제목 | 파일 | 롤백 |
|----|------|------|------|------|
| PR-1 | `feat(P6): extend AdvisoryOutput — add regime_label + logical_proposition (additive, default="")` | `advisors/base.py` | `git revert` (필드 삭제) |
| PR-2 | `feat(P6): MacroRegimeAgent — populate regime_label in AdvisoryOutput` | `advisors/macro_regime.py` | `git revert` |
| PR-3 | `feat(P6): add advisors/memory/ — regime_memory.py + hierarchical_store.py (DuckDB backend)` | `advisors/memory/regime_memory.py`, `advisors/memory/hierarchical_store.py` | 파일 삭제 |
| PR-4 | `feat(P6): add cwrm_router.py + stl_protocol.py — routing + proposition extraction` | `advisors/memory/cwrm_router.py`, `advisors/memory/stl_protocol.py` | 파일 삭제 |
| PR-5 | `feat(P6): add memory_layer.py — public MemoryLayer API` | `advisors/memory/memory_layer.py` | 파일 삭제 |
| PR-6 | `feat(P6): update orchestrator.py — memory hook (ADVISOR_MEMORY_ENABLED=false default)` | `advisors/orchestrator.py` | `git revert` |
| PR-7 | `feat(P6): update news_sentiment.py — STL proposition format in system prompt` | `advisors/news_sentiment.py` | `git revert` |
| PR-8 | `feat(P0): MLflow regime_memory metrics + advisor-memory CLI subcommands` | `advisors/memory/memory_layer.py`, `main.py` | `git revert` |
| PR-9 | `test(P6): comprehensive test suite — 5 new test files for memory modules` | `tests/test_advisor_*.py` (5개) | 파일 삭제 |
| PR-10 | `docs: update CLAUDE.md + README — AMH memory layer guide + Key Invariants` | `CLAUDE.md`, `README.md` | `git revert` |

### G4. Feature Flags

| 플래그 | 기본값 | 효과 |
|--------|--------|------|
| `ADVISOR_MEMORY_ENABLED=false` | `false` | 기존 동작 100% 유지 |
| `ADVISOR_MEMORY_DB_PATH=:memory:` | `:memory:` | 재시작 시 메모리 초기화 (영속성 없음) |
| `CWRM_DEEP_THRESHOLD=0.5` | `0.5` | disagreement > 0.5 → deep path |

### G5. 타임라인

```
Week 1:  PR-1 → PR-2 → PR-3
Week 2:  PR-4 → PR-5 → PR-6
Week 3:  PR-7 → PR-8 → PR-9 일부
Week 4:  PR-9 완료 → PR-10
```

---

## H. Testing Strategy

### H1. Test Pyramid

```
E2E (1개)
  └─ test_orchestrator_memory_e2e.py
      └─ Orchestrator(memory_layer=MemoryLayer(":memory:")).aanalyze() 전체 흐름

Integration (3개)
  ├─ test_advisor_memory_layer.py (write→read→update_outcome 흐름)
  ├─ test_advisor_orchestrator_memory.py (기존 테스트 + memory_layer=None 확인)
  └─ test_advisor_memory_cli.py (advisor-memory CLI 서브커맨드)

Unit (6개)
  ├─ test_advisor_regime_memory.py (DuckDB CRUD)
  ├─ test_advisor_hierarchical_store.py (L1/L2/L3 조회 순서)
  ├─ test_advisor_cwrm_router.py (routing 결정)
  ├─ test_advisor_stl_protocol.py (proposition 파싱)
  ├─ test_advisory_output_backward_compat.py (기존 코드 호환)
  └─ test_advisor_regime_memory_archive.py (stale 아카이브)
```

### H2. 핵심 테스트 케이스

| 테스트 | 검증 내용 |
|--------|----------|
| `test_advisory_output_backward_compat` | 기존 10개 필드만으로 생성 → 오류 없음 (regime_label, logical_proposition = "") |
| `test_memory_layer_none_same_behavior` | `Orchestrator(memory_layer=None)` → 기존 `_blend()` 결과 동일 |
| `test_cwrm_deep_when_high_disagreement` | `news.score=0.8, macro.score=-0.5` → path="deep" |
| `test_cwrm_shallow_when_low_disagreement` | `news.score=0.2, macro.score=0.1` → path="shallow" |
| `test_stl_extract_valid_proposition` | `rationale="positive earnings..."` → `"IF earnings > Q3 THEN bullish WITH 0.7"` 포맷 |
| `test_stl_fallback_on_no_proposition` | 포맷 없는 rationale → empty string (예외 없음) |
| `test_regime_memory_write_and_read` | 쓰기 후 같은 regime으로 읽기 → entry 반환 |
| `test_regime_memory_does_not_cross_regime` | risk_off으로 저장 후 risk_on으로 읽기 → empty |
| `test_hierarchical_store_l1_before_l2` | L1 entry 있으면 L1 먼저 반환 |
| `test_memory_layer_write_on_analyze` | `aanalyze()` 후 `get_relevant_memories()` → 방금 저장한 entry 포함 |
| `test_update_outcome_success` | `update_outcome(session_id, 2.1)` → DB outcome_pct=2.1 |
| `test_orchestrator_injects_memory_to_devils_context` | deep path 시 devils ctx에 `memory_context` 키 존재 |

### H3. CI Gates

| Gate | 조건 |
|------|------|
| `ADVISOR_MEMORY_ENABLED=false` | CI 기본값 — 추가 인프라 없이 통과 |
| `test_memory_layer_none_same_behavior` | CI 필수 통과 |
| `test_advisory_output_backward_compat` | CI 필수 통과 |
| `pytest --cov-fail-under=75` | 기존 유지 |

### H4. 테스트 데이터

```python
# tests/fixtures/memory/
# valid_advisory_output_risk_off.json — regime_label="risk_off" 포함 예시
# memory_entries_5_risk_off.json — L1 에피소딕 5개 예시
# stl_proposition_format.txt — "IF VIX>25 THEN bearish WITH 0.7"
```

---

## I. Observability & Operations

### I1. 로깅

```python
# memory_layer.py
_LOGGER = get_logger("advisors.memory")

_LOGGER.info(
    "[MemoryLayer] regime=%s retrieved=%d path=%s elapsed_ms=%.0f",
    regime, len(memories), routing.path, elapsed * 1000
)
_LOGGER.debug("[MemoryLayer] write session_id=%s ticker=%s final_score=%.3f", ...)
_LOGGER.warning("[MemoryLayer] DuckDB unavailable — memory disabled for this call")
```

### I2. audit_log/advisor_memory.jsonl

```json
{
  "ts": "2026-05-29T10:00:00Z",
  "event": "memory_read",
  "session_id": "adv_20260529_xyz",
  "ticker": "005930.KS",
  "regime": "risk_off",
  "retrieved_count": 5,
  "routing_path": "deep",
  "elapsed_ms": 12
}
```

### I3. MLflow 메트릭

```python
# memory_layer.log_to_mlflow()
mlflow.log_metrics({
    "memory_l1_entries_risk_off": count_l1_risk_off,
    "memory_l1_entries_risk_on": count_l1_risk_on,
    "memory_retrieval_hit_rate": hit_rate,   # retrieved > 0 / total calls
    "cwrm_deep_path_rate": deep_rate,        # deep / total
})
```

### I4. 런북

```bash
# 메모리 상태 확인
python main.py advisor-memory stats

# 특정 regime 메모리 조회
python main.py advisor-memory list --regime risk_off --limit 10

# forward return 업데이트
python main.py advisor-memory update-outcome \
  --session adv_20260529_xyz --return-pct 2.1

# 오래된 메모리 정리 (90일 이전)
python main.py advisor-memory purge --before 2026-03-01

# 메모리 DB 경로 확인
echo $ADVISOR_MEMORY_DB_PATH

# 메모리 비활성화 (롤백)
export ADVISOR_MEMORY_ENABLED=false
```

---

## J. Error Handling & Recovery

### J1. 오류 분류

| 오류 | 처리 방식 |
|------|----------|
| DuckDB 연결 실패 | graceful — `MemoryLayer` 비활성, WARNING 로그, 분석 계속 |
| `get_relevant_memories()` 예외 | try/except → 빈 list 반환, ERROR 로그 |
| `write()` 예외 | try/except → WARNING 로그, `aanalyze()` 결과는 반환 |
| STL proposition 파싱 실패 | fallback → `logical_proposition=""` |
| CWRM `route()` 예외 | fallback → `RoutingDecision(path="shallow")` |
| `AdvisoryOutput.__post_init__` 실패 | regime_label="" default → 검증 패스 |

### J2. Graceful Degradation 계층

```
ADVISOR_MEMORY_ENABLED=false → 완전 비활성, 기존과 동일
ADVISOR_MEMORY_ENABLED=true, DuckDB 실패 → in-memory fallback (재시작 시 초기화)
메모리 조회 오류 → 빈 context, 분석 계속
메모리 쓰기 오류 → 로그만, 분석 결과에 영향 없음
```

### J3. 멱등성

- `write()`: `session_id` PRIMARY KEY → 동일 세션 재호출 시 UPSERT (결과 동일)
- `update_outcome()`: idempotent — 같은 `session_id`로 여러 번 호출 가능, 마지막 값 유지
- `archive_stale()`: 이미 아카이브된 항목 재실행 → COUNT 0 반환 (안전)

---

## K. Dependencies, Security, Risks

### K1. 의존성

| 패키지 | 버전 | 용도 | 비고 |
|--------|------|------|------|
| `duckdb` | `>=1.5.3` (기존) | 메모리 백엔드 | 버전 업 없음 |
| `hmmlearn` | `>=0.3` (optional) | 향후 regime detection 강화 | Phase 2 고려 |
| `langmem` | optional | LangMem SDK (LangChain 2025) | Phase 2 고려 |
| `graphiti-core` | optional | 시간적 지식 그래프 | Phase 2 고려 |

**Phase 1 신규 의존성: 없음** — 기존 DuckDB만 사용.

### K2. 보안

| 위험 | 대응 |
|------|------|
| 메모리에 ticker/rationale PII 저장 | `advisor_memory.jsonl`은 내부 전용, git-ignore |
| `ADVISOR_MEMORY_DB_PATH`가 공유 경로 | 기본값 `:memory:` (영속 없음), 영속 사용 시 README 경고 |
| advisory_score 메모리 조작 가능성 | 메모리는 context injection만, score 계산 로직 무관 |

### K3. Risk Register

| # | 위험 | 확률 | 영향 | 대응 |
|---|------|------|------|------|
| R1 | FinThink R-Mem ICLR 2026 미채택 → 설계 방향성 재검토 필요 | 중 | 낮음 | 구현은 LangMem + DuckDB로 독립적 — 논문 미채택 시 영향 없음 |
| R2 | `AdvisoryOutput` additive 필드가 기존 테스트 실패 | 낮음 | 높음 | `default=""` + `test_advisory_output_backward_compat` CI 필수 |
| R3 | CWRM deep path 비율이 너무 높아 DevilsAdvocate 오버로드 | 중 | 중 | `CWRM_DEEP_THRESHOLD=0.5` 조정 가능, 초기 높게 설정 |
| R4 | DuckDB 메모리 파일 증가 | 낮음 | 낮음 | `max_entries=1000` + `archive_stale()` 주간 실행 |
| R5 | 메모리 주입이 어드바이저 지연 증가 | 낮음 | 낮음 | 목표 ≤ 50ms (DuckDB 조회는 ~5ms), 타임아웃 설정 |
| R6 | regime_label이 빈 문자열 → 메모리 쿼리 불가 | 중 | 낮음 | `get_relevant_memories(regime="")` → 빈 list graceful |

### K4. Change Control

- `AdvisoryOutput`: additive optional fields — schema_version 변경 불필요
- `Orchestrator`: `memory_layer=None` 기본값 — 기존 호출 코드 변경 불필요
- `MacroRegimeAgent`: `regime_label` 채우기만 — 기존 score/confidence 로직 무변경
- Key Invariants 전부 보존 (CLAUDE.md)

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| FinThink R-Mem (설계 영감) ⚠️ | OpenReview | FinThink: AMH-Grounded MAS | openreview.net/forum?id=vm7xqrU345 | 2025-09-19 제출, 2026-02-11 수정 | ICLR 2026 active review | R-Mem/CWRM/STL 3컴포넌트 확인 |
| LangMem (구현 기반) | LangChain | LangMem SDK long-term memory | changelog.langchain.com | 2025-02-20 | ~100K (langchain) | episodic/semantic/procedural 3-tier |
| Graphiti (옵션) | GitHub | getzep/graphiti | github.com/getzep/graphiti | 2025-01 (arxiv) | 20K stars | 시간적 지식 그래프, regime 변화 추적 |
| Mem0 (옵션) | GitHub | mem0ai/mem0 | github.com/mem0ai/mem0 | 2025 (active) | 90K stars | 하이브리드 벡터+그래프+KV 메모리 |
| Agent Memory (참조) | GitHub | NirDiamant/Agent_Memory_Techniques | github.com | 2025 (active) | — | 30개 메모리 패턴 Jupyter notebook |
| LangGraph Store | LangChain docs | LangGraph Persistence | docs.langchain.com | 2025 (live) | — | `BaseStore` + checkpointer 패턴 |
| AMH 이론 | Academic | Lo (2004) AMH | — | 2004 (기초 이론) | 광범위 인용 | 시장 적응 원리, regime-tagged memory 근거 |
| H-MEM | arXiv | Hierarchical Memory for LLM Agents | arxiv.org/abs/2507.22925 | 2025-07 | — | 다계층 의미 추상화 참조 |
| Wave 4 리포트 (내부) | Internal | 20260529_project-upgrade-report-wave4.md | 내부 파일 | 2026-05-29 | — | Surprise Pick ★2, SurpriseScore 6.67 |

### ㅋ2. AMBER_BUCKET

| 항목 | AMBER 이유 | 처리 |
|------|-----------|------|
| FinThink 구체적 STL 명제 포맷 | ICLR 2026 미채택, 논문 세부 API 변경 가능 | 포맷은 자체 regex 정의 (논문 의존 최소화) |
| R-Mem cross-asset 메모리 가중치 | 논문의 구체적 가중치 수식 미확인 | Phase 2로 이연, Phase 1은 단순 k-NN retrieval |

AMBER 아이템: 2개이나 **Best 3 핵심 구현**에 포함 안 됨 → ZERO 미발동.

### ㅋ3. Benchmarked Repo Notes

| Repo | Stars | 패턴 | 적용 |
|------|-------|------|------|
| langchain-ai/langgraph | ~100K | `BaseStore` namespace, `MemorySaver` | `memory_layer.py` 인터페이스 |
| mem0ai/mem0 | 90K | hybrid 3-tier memory, self-edit | L1/L2/L3 계층 설계 |
| getzep/graphiti | 20K | temporal edges, regime-expiry | `archive_stale()` 로직 |
| NirDiamant/Agent_Memory_Techniques | — | 30 notebooks: episodic/semantic/proc | `hierarchical_store.py` 구현 참조 |
| kenny1031/regime-aware-dynamic | — | HMM + XGBoost regime detection | 향후 `MacroRegimeAgent` HMM 강화 참조 |

### ㅋ4. 용어집

| 용어 | 설명 |
|------|------|
| AMH | Adaptive Markets Hypothesis — 시장 참여자는 진화적으로 적응한다 (Lo 2004) |
| R-Mem | Reasoning-Driven Hierarchical Memory — FinThink의 regime-tagged 메모리 컴포넌트 |
| CWRM | Context-aware Workflow for Reasoning — 신호 불일치 기반 라우팅 |
| STL | Sentiment-To-Logic — 감성 신호 → 논리 명제 변환 프로토콜 |
| L1/L2/L3 | 에피소딕(단기)/의미론적(중기)/절차적(장기) 메모리 계층 |
| regime | 시장 체제: risk_on / neutral / risk_off |
| shallow path | 신호 일치 시: 메모리 요약만 DevilsAdvocate에 전달 |
| deep path | 신호 불일치 시: 전체 메모리 체인 + proposition 전달 |

---

## Verification Gate

| Gate | 항목 | 상태 |
|------|------|------|
| Gate 0 (Dry-run) | 코드 변경 없음 | ✅ |
| Gate 1 (Evidence) | LangMem 2025-02-20, Graphiti 20K stars, Mem0 90K stars — 2개 이상 확인 | ✅ |
| Gate 2 (PR plan ≥6) | PR 10개 | ✅ |
| Gate 3 (Tests) | 테스트 케이스 명세 완비 | ✅ |
| Gate 4 (Rollout/Rollback) | `ADVISOR_MEMORY_ENABLED=false` + `git revert` | ✅ |
| Gate 5 (KPI 정의) | 메모리 hit rate, CWRM deep rate, 커버리지 | ✅ |
| Gate 6 (Safety) | `advisory_score` 불변, `screening_output_only=True` 유지, PIT 가드 무관 | ✅ |
| AMBER check | FinThink AMBER → Best 3 핵심 구현 미포함 (LangMem으로 대체) | ✅ ZERO 없음 |

**최종 판정: Go ✅**

### Apply Gates

- **Gate 0**: 현재 플랜 문서. 코드 수정 없음.
- **Gate 1**: 변경 파일 — F1 섹션 참조 (6개 신규 파일, 4개 수정 파일)
- **Gate 2**: PR-1 시작 전 사용자 승인 필요
- **Gate 3**: `ADVISOR_MEMORY_ENABLED=false` (모든 환경 기본값)
- **Gate 4**: Rollback = `git revert` + `ADVISOR_MEMORY_ENABLED=false`
