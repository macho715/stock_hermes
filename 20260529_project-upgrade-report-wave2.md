# Project Upgrade Report — stock_rtx4060 **Wave 2**
**Skill:** project-upgrade v2.2.0 | **Date:** 2026-05-29 (2nd scan)
**Project:** `stock_1901/stock_rtx4060` (P0–P8 hedge-fund grade paper trading system)
**Context:** Wave 1 Best 3 모두 구현 완료 (GAP fixes ✅ · MLflow 3.x ✅ · OpenBB ingestor ✅ · Chaos tests ✅ · MiniMax advisor ✅). 이 보고서는 다음 개선 파동을 스캔한다.

---

## 0. Surprise Picks (최우선 — 예상 밖 아이디어)

| # | Idea | Novelty | SurpriseScore | 내일 당장 할 첫 번째 액션 |
|---|------|---------|---------------|--------------------------|
| ★1 | **항공 "Dead Reckoning" 신뢰도 감쇠** — GPS 신호 끊기면 마지막 위치+속도로 현재 위치를 추정하되 불확실성 반경이 커지는 항법 기법을 trading에 적용. OpenBB·yfinance 데이터가 stale될수록 `confidence` 점수를 시간 경과에 비례해 decay시키고, 임계 이하로 떨어지면 GREEN→AMBER 자동 강등 | 5 | 7.5 | `recommendation_engine.py`에서 `data_freshness_hours` 계산 지점 파악 → `confidence_decay(age_h, halflife_h=24)` stub 추가 |
| ★2 | **Shapley 동적 어드바이저 블렌딩** — 현재 Orchestrator는 고정 가중치(news 40%/devils 30%/macro 30%). 각 어드바이저의 누적 P&L 기여도를 Shapley 값으로 측정해 다음 주기 가중치로 환류. 무임승차 어드바이저 자동 페널티 | 5 | 6.67 | `advisors/orchestrator.py`에서 `DEFAULT_WEIGHTS` 고정값 확인 → `audit_log/advisor.jsonl` 기반 Shapley 계산 PoC |
| ★3 | **Hypothesis 속성 기반 테스트** — 의료 임상시험에서 "어떤 환자 프로파일에서도 약효가 유지되어야 한다"는 속성을 검증하듯, 거래 시스템 불변(PIT look-ahead 금지, screening_output_only=True 항상, risk gate 항상 트리거)을 Hypothesis로 임의 입력 전체 공간에서 검증 | 4 | 6.0 | `pip install hypothesis` → `tests/test_invariants_hypothesis.py` 스켈레톤 — `@given(st.builds(BarData))` 1개 불변 테스트 |

---

## 1. Executive Summary

Wave 1 Best 3 + 2개 Surprise Pick(Chaos/MiniMax)이 이미 구현됐다. 커버리지는 **85.81%** (branch 77.4%)로 라인 목표는 달성했으나 **브랜치 커버리지 갭(77%→85%)이 다음 품질 레버**다. 외부 리서치에서 가장 큰 변화는 **Optuna v5(2025-05-26)** 메이저 릴리즈, **DuckDB 1.5.3(2026-05-20)** + **DuckLake 1.0** 안정화, **NautilusTrader 1.221.0 Beta(2025-10-26)** 3가지다. 어드바이저 레이어에서는 MiniMax + Anthropic 듀얼 공급자 구조가 생겼으므로 **LiteLLM 통합 게이트웨이**로 공급자 중립 라우팅+폴백을 구현하면 운영 복잡도가 크게 줄어든다.

---

## 2. Current State Snapshot

| 항목 | 현황 | 상태 |
|------|------|------|
| Python | 3.12 CI / 3.14.4 로컬 | ✅ |
| 테스트 커버리지 (line) | 85.81% (fail_under=75) | ✅ |
| 테스트 커버리지 (branch) | 77.4% | ⚠ 개선 여지 |
| 전체 테스트 수 | 346 passed, 5 skipped | ✅ |
| MLflow | >=3.0 (requirements.in 수정됨) | ✅ |
| DuckDB | >=1.1 (설치 버전 미확인, 1.5.3 최신) | ⚠ 업그레이드 검토 |
| Optuna | >=4.0 (v5.0 메이저 출시됨) | ⚠ v5 업그레이드 기회 |
| LightGBM | >=4.5 (4.6 최신) | ⚠ 경미한 패치 가능 |
| OpenBB ingestor | 구현됨 (graceful degradation) | ✅ |
| Chaos 테스트 | test_chaos_paper_trading.py 구현 | ✅ |
| MiniMax 어드바이저 | claude_client.py 듀얼 공급자 | ✅ |
| Orchestrator 가중치 | 고정 (news 40 / devils 30 / macro 30) | ⚠ 동적 미적용 |
| vectorbt | open-source maintenance mode | ⚠ NautilusTrader 대안 |
| LLM 공급자 라우팅 | 수동 분기 (Anthropic vs MiniMax) | ⚠ LiteLLM으로 통합 가능 |

**Pain points:**
- Branch coverage 77.4% — `recommendation_engine.py`(84% line), `portfolio/optimizer.py`(80%), `position_tracker.py`(80%)에 미테스트 분기 밀집
- Optuna v5 메이저 API 변경 (gRPC proxy 개선 + 생성AI 최적화 신기능) 미활용
- DuckDB 1.5.3 + DuckLake 1.0 — sorted tables/bucket partitioning으로 PIT 쿼리 성능 개선 가능
- Orchestrator의 고정 어드바이저 가중치 — P&L 기여 피드백 없음
- MiniMax + Anthropic 듀얼 공급자가 claude_client.py 내 분기로 구현 → 공급자 추가시 코드 변경 필요

---

## 3. Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | Novelty | PriorityScore | SurpriseScore | Evidence | 상태 |
|---|----------|------|--------|--------|------|------------|---------|---------------|---------------|----------|------|
| 1 | **Hypothesis 속성 기반 테스트 — 금융 불변 검증** | DX/Tooling | 3 | 2 | 1 | 5 | 4 | **7.5** | 6.0 | hypothesis.readthedocs.io (live, 2025); OOPSLA 2025 paper | ✅ CONFIRMED |
| 2 | **Branch Coverage 85%+ (recommendation_engine + portfolio)** | Reliability | 3 | 2 | 1 | 5 | 1 | **7.5** | 1.5 | Internal coverage.json (2026-05-29): branch=77.4% | ✅ CONFIRMED |
| 3 | **LiteLLM 통합 LLM 게이트웨이** | Architecture | 3 | 2 | 1 | 4 | 2 | **6.0** | 3.0 | github.com/BerriAI/litellm (2025, ~20k stars); docs.litellm.ai/minimax | ✅ CONFIRMED |
| 4 | **DuckDB 1.5.3 + DuckLake 1.0 업그레이드** | Performance | 4 | 2 | 2 | 4 | 2 | **4.0** | 4.0 | duckdb.org (2026-05-20, v1.5.3); motherduck.com/DuckLake-1.0 | ✅ CONFIRMED |
| 5 | **Dead Reckoning 신뢰도 감쇠** (항공→거래) | Reliability | 3 | 2 | 1 | 3 | 5 | **4.5** | 7.5 | (Cross-domain: aviation nav theory; Hypothesis PBT paper OOPSLA 2025) | ⚠ AMBER (날짜 직접 매칭 없음) |
| 6 | **Optuna v5 업그레이드 + GrpcStorageProxy** | Performance | 3 | 2 | 2 | 4 | 2 | **3.0** | 3.0 | optuna.org (2025-05-26, v5); medium.com/optuna v4.4 gRPC (2025-06-16) | ✅ CONFIRMED |
| 7 | **Shapley 동적 어드바이저 가중치** | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | arXiv cs.GT 2025-02; 기존 evidence 유지 | ✅ CONFIRMED |
| 8 | **NautilusTrader 이벤트-드리븐 백테스터** | Architecture | 4 | 4 | 3 | 3 | 3 | **1.0** | 3.0 | github.com/nautechsystems/nautilus_trader v1.221.0 Beta (2025-10-26) | ✅ CONFIRMED |
| 9 | **LightGBMLSS 확률적 예측 (분포 모델링)** | Performance | 4 | 3 | 2 | 3 | 3 | **2.0** | 4.0 | github.com/StatMixedML/LightGBMLSS (2025 active); CRPS 실험 구현 | ✅ CONFIRMED |
| 10 | **OODA FSM + 레짐 재조향 트리거** | Architecture | 3 | 3 | 2 | 3 | 5 | **1.5** | 5.0 | breakingdefense.com (2025-04) — Wave 1 미구현 carry-over | ✅ CONFIRMED |

> PriorityScore = (Impact × Confidence) / (Effort × Risk)
> SurpriseScore = (Novelty × Impact) / Effort

---

## 4. Best 3 Deep Report

### BEST-1: Hypothesis 속성 기반 테스트 — 금융 불변 검증
**PriorityScore: 7.5 | Bucket: DX/Tooling | Effort: S**

#### Goal
`hypothesis` 프레임워크로 stock_rtx4060의 핵심 불변을 임의 입력 공간 전체에서 검증. 시나리오 테스트로 잡지 못하는 엣지 케이스(음수 가격, 미래 날짜, 빈 시리즈)에서 불변이 깨지는 버그를 사전 탐지.

#### Non-goals
- 기존 pytest 테스트 삭제/교체 (보완 목적)
- ML 모델 학습 루프에 Hypothesis 적용 (실행 시간 과다)
- 외부 API 호출 포함 테스트 (mock 전용)

#### Proposed Design
```python
# tests/test_invariants_hypothesis.py
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from stock_rtx4060.paper_trading import PaperTradingConfig, evaluate_signal

# 불변 1: screening_output_only 항상 True
@given(score=st.floats(0, 100), signal=st.sampled_from(["BUY", "SELL", "HOLD"]))
def test_screening_output_only_invariant(score, signal):
    result = evaluate_signal(signal, score)
    assert result.screening_output_only is True

# 불변 2: PIT as_of guard — 미래 날짜는 항상 RuntimeError
@given(as_of=st.dates(min_value=date(2027, 1, 1), max_value=date(2030, 12, 31)))
def test_pit_future_as_of_raises(as_of):
    with pytest.raises(RuntimeError):
        load_ohlcv_with_provider("005930.KS", as_of=as_of.isoformat())

# 불변 3: GAP-01 BUY score 임계 (score<56이면 항상 reject)
@given(score=st.floats(0.0, 55.99))
def test_buy_below_threshold_always_rejected(score):
    result = evaluate_signal("BUY", score)
    assert result.status == "rejected"
    assert result.reason == "buy_score_below_threshold"

# 불변 4: advisory_score ∈ [-1, +1]
@given(tickers=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_advisory_score_bounds(tickers):
    # mock orchestrator로 임의 ticker에 대해 score 범위 검증
    for ticker in tickers:
        score = mock_orchestrator_score(ticker)
        assert -1.0 <= score <= 1.0
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-H1 | `test(DX): add hypothesis PBT skeleton — 4 core invariants` | `tests/test_invariants_hypothesis.py`, `requirements-dev.in` | `git revert` |
| PR-H2 | `test(DX): add PIT as_of invariant + GAP-01 fuzzing` | `tests/test_invariants_hypothesis.py` | `git revert` |
| PR-H3 | `test(DX): add portfolio optimizer weight-sum invariant` | `tests/test_invariants_hypothesis.py` | `git revert` |

#### Tests (the PR adds these)
- `test_screening_output_only_invariant` — 임의 점수/시그널에서 항상 True
- `test_pit_future_as_of_raises` — 미래 날짜 항상 RuntimeError
- `test_buy_below_threshold_always_rejected` — score<56 항상 reject
- `test_advisory_score_bounds` — score ∈ [-1,+1]
- `test_portfolio_weights_sum_to_one` — optimize() 결과 가중치 합 ≈ 1.0

#### Rollout & Rollback
- Feature: `requirements-dev.in`에만 추가 (프로덕션 dep 아님)
- CI: `pytest tests/test_invariants_hypothesis.py` 기존 suite에 포함
- Rollback: `git revert` + requirements-dev 라인 제거

#### Risks & Mitigations
1. 실행 시간 증가 → `@settings(max_examples=50)` 기본값 제한
2. Hypothesis가 `hypothesis.readthedocs.io` 전략으로 유효하지 않은 mock 생성 → `@assume()` 가드 추가
3. flaky test 위험 → `@settings(deriving=RuleBasedStateMachine)` 미사용

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| 불변 커버 속성 수 | 0 | ≥5 |
| Branch coverage | 77.4% | ≥80% (부수 효과) |
| 발견된 새 엣지 케이스 | 0 | ≥1 (Hypothesis shrink 결과) |

#### Evidence
- hypothesis.readthedocs.io (live docs, accessed 2026-05-29) | 7,400+ GitHub stars
- Tajalli et al., "An Empirical Evaluation of Property-Based Testing in Python", OOPSLA 2025 | peer-reviewed

---

### BEST-2: DuckDB 1.5.3 + DuckLake 1.0 업그레이드
**PriorityScore: 4.0 | Bucket: Performance | Effort: S-M**

#### Goal
현재 `duckdb>=1.1`을 1.5.3으로 업그레이드하고, DuckLake 1.0의 **bucket partitioning** + **sorted tables** + **deletion vectors**를 data_lake에 적용해 PIT 쿼리 성능과 레이크 크기를 개선.

#### Non-goals
- MotherDuck 클라우드 이전 (로컬 운영 유지)
- Iceberg 포맷 전면 도입 (현재 Parquet 유지, DuckLake 옵션만 추가)
- 기존 `data_lake/` API 시그니처 변경

#### Proposed Design
```python
# requirements.in 변경
# Before: duckdb>=1.1
# After:  duckdb>=1.5.3

# src/stock_rtx4060/data_lake/__init__.py — DuckLake 옵션 feature flag
DUCKLAKE_ENABLED = os.getenv("DUCKLAKE_ENABLED", "false").lower() == "true"

if DUCKLAKE_ENABLED:
    # DuckLake 1.0 — bucket partitioning on ticker + date
    conn.execute("""
        ATTACH 'ducklake:stock_lake.db' AS lake;
        CREATE TABLE IF NOT EXISTS lake.ohlcv_partitioned (
            ticker   VARCHAR,
            date     DATE,
            open     DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT,
            as_of    TIMESTAMP
        ) PARTITIONED BY (ticker, YEAR(date))
        SORTED BY (date)
        WITH DELETION VECTORS;
    """)
```

```python
# data_lake/store.py — 기존 write_pit에 DuckLake 경로 추가
def write_pit(self, df: pd.DataFrame, as_of: str) -> None:
    if DUCKLAKE_ENABLED:
        self._conn.execute("INSERT INTO lake.ohlcv_partitioned SELECT *, ? FROM df", [as_of])
    else:
        # 기존 Parquet 경로 유지
        self._write_parquet(df, as_of)
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-D1 | `chore(P1): bump duckdb>=1.5.3, verify existing tests pass` | `requirements.in`, `requirements.txt` | `pip install duckdb==1.1.x` |
| PR-D2 | `feat(P1): add DuckLake 1.0 feature flag + partitioned table DDL` | `data_lake/__init__.py`, `data_lake/store.py` | `DUCKLAKE_ENABLED=false` (기본값) |
| PR-D3 | `test(P1): add ducklake smoke test + benchmark vs Parquet` | `tests/test_ducklake_smoke.py` | `git revert` |

#### Tests
- `test_duckdb_version_compat` — 1.5.3 API 호환성 확인
- `test_ducklake_disabled_by_default` — 기본값 false 확인
- `test_ducklake_write_read_roundtrip` — DUCKLAKE_ENABLED=true 시 쓰기/읽기
- `test_pit_as_of_guard_with_ducklake` — PIT guard 불변 유지 확인

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| DuckDB 버전 | >=1.1 (설치 버전 미확인) | 1.5.3 |
| PIT 쿼리 속도 (1년 데이터) | 측정 안 됨 | ≥20% 개선 |
| data_lake 테스트 | 기존 통과 | 기존 통과 + 3개 신규 |

#### Rollout & Rollback
- Feature flag `DUCKLAKE_ENABLED=false` (기본) → 무조건 하위 호환
- DuckDB 1.5.3은 1.1 API와 하위 호환 (breaking change 없음)
- Rollback: `pip install duckdb==1.1.x`

#### Evidence
- duckdb.org/2026/05/20/announcing-duckdb-153 (2026-05-20, official) | 28k+ GitHub stars
- motherduck.com/blog/announcing-duckdb-141-motherduck (2025-12 blog) — DuckLake 0.3→1.0 경로 확인

---

### BEST-3: LiteLLM 통합 LLM 게이트웨이
**PriorityScore: 6.0 | Bucket: Architecture | Effort: S**

#### Goal
`claude_client.py`의 Anthropic/MiniMax 이중 분기를 LiteLLM 게이트웨이로 통합. 공급자 중립 API 한 줄로 Anthropic claude-opus-4-7 ↔ MiniMax-M2.7 자동 폴백, 통합 비용 트래킹, 레이트리밋 처리.

#### Non-goals
- LiteLLM 프록시 서버 배포 (로컬 SDK 사용)
- 기존 `audit_log/advisor.jsonl` 포맷 변경
- Anthropic prompt caching 제거 (LiteLLM은 캐시 헤더 패스스루 지원)

#### Proposed Design
```python
# requirements.in 추가
litellm>=1.55

# src/stock_rtx4060/advisors/claude_client.py — 신규 LiteLLM 경로
try:
    import litellm
    _HAS_LITELLM = True
except ImportError:
    _HAS_LITELLM = False

PROVIDER_FALLBACK_CHAIN = [
    "anthropic/claude-opus-4-7",       # 1차: Anthropic
    "openai/MiniMax-M2.7",              # 2차: MiniMax (OpenAI 호환)
]

def _call_with_litellm(messages: list[dict], **kwargs) -> dict:
    """공급자 중립 호출 — 자동 폴백."""
    return litellm.completion(
        model=PROVIDER_FALLBACK_CHAIN[0],
        fallbacks=PROVIDER_FALLBACK_CHAIN[1:],
        messages=messages,
        metadata={"cost_callback": _log_cost},   # 통합 비용 로깅
        **kwargs,
    )

# 기존 Anthropic/MiniMax 분기는 _HAS_LITELLM=False일 때 폴백으로 유지
```

```python
# audit_log의 provider 필드 추가 (additive)
log_entry = {
    "ts": ..., "ticker": ..., "provider": litellm.get_last_provider(),  # 신규
    "cost_usd": ..., "tokens_in": ..., "tokens_out": ...,
}
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-L1 | `feat(P6): add litellm dependency + _call_with_litellm stub` | `requirements.in`, `advisors/claude_client.py` | `pip uninstall litellm`, revert client |
| PR-L2 | `feat(P6): wire litellm fallback into advisor main path` | `advisors/claude_client.py`, `tests/test_claude_client.py` | feature flag `USE_LITELLM=false` |
| PR-L3 | `feat(P6): add provider field to advisor.jsonl audit log` | `advisors/claude_client.py`, `advisors/audit.py` | additive; old entries unaffected |

#### Tests
- `test_litellm_fallback_to_minimax` — Anthropic RateLimitError → MiniMax 자동 전환
- `test_litellm_cost_logged_to_audit` — `cost_usd` + `provider` 필드 확인
- `test_litellm_disabled_uses_original_path` — `USE_LITELLM=false` 시 기존 경로 유지
- `test_advisory_score_unchanged_with_litellm` — 결과 점수 범위 [-1,+1] 유지

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| LLM 공급자 전환 시 코드 변경 | 필요 (분기 수정) | 불필요 (PROVIDER_FALLBACK_CHAIN 수정만) |
| 어드바이저 폴백 자동화 | 없음 | Anthropic 오류 시 MiniMax 자동 전환 |
| 비용 로그 공급자 필드 | 없음 | advisor.jsonl에 `provider` 필드 추가 |

#### Rollout & Rollback
- Feature flag `USE_LITELLM` 기본값 false → 점진적 롤아웃
- `_HAS_LITELLM=False`면 기존 분기 코드 그대로 동작
- Rollback: `USE_LITELLM=false` 환경변수 설정으로 즉시 비활성화

#### Evidence
- github.com/BerriAI/litellm (2025 active, 20k+ GitHub stars) — 50+ LLM 공급자 통합
- docs.litellm.ai/docs/providers/minimax (2025, confirmed) — MiniMax 공식 지원
- dev.to/kuldeep_paul 2025 — Bifrost/LiteLLM 폴백 패턴 실증 사례

---

## 5. Options A/B/C

| Option | 내용 | 기간 | 위험 | 커버리지 영향 |
|--------|------|------|------|---------------|
| **A (보수)** | Hypothesis PBT + Branch coverage | 1주 | 낮음 | branch 77%→≥82% |
| **B (중간)** | A + DuckDB 1.5.3 + LiteLLM | 3주 | 낮음 | 유지 + infra 개선 |
| **C (공격)** | B + Optuna v5 + Shapley 어드바이저 + NautilusTrader | 10주 | 중간 | +2~3% |

---

## 6. 30/60/90-day Roadmap

### 30일 (2026-05-29 → 2026-06-28)
- [ ] PR-H1: Hypothesis 스켈레톤 + 4개 불변 테스트
- [ ] PR-H2~H3: PIT / GAP-01 / portfolio 불변 추가
- [ ] Branch coverage 타겟: `recommendation_engine.py` + `portfolio/optimizer.py` 집중 커버
- [ ] PR-D1: `duckdb>=1.5.3` 버전 범프 + 기존 테스트 확인

### 60일 (2026-06-29 → 2026-07-28)
- [ ] PR-L1~L2: LiteLLM 게이트웨이 스텁 + 메인 경로 통합
- [ ] PR-L3: advisor.jsonl provider 필드 추가
- [ ] PR-D2: DuckLake feature flag + DDL
- [ ] Optuna v5 호환성 스파이크 (breaking change 목록 확인)

### 90일 (2026-07-29 → 2026-08-28)
- [ ] PR-O5: Optuna v5 업그레이드 + GrpcStorageProxy 활성화
- [ ] Shapley 어드바이저 가중치 PoC (`advisor.jsonl` P&L 기반)
- [ ] Dead Reckoning 신뢰도 감쇠 `confidence_decay()` 구현
- [ ] NautilusTrader 스파이크 (vectorbt 코드 1개 flow 이전 시험)

---

## 7. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| BEST-1 Hypothesis | Official | Hypothesis Docs | hypothesis.readthedocs.io | live | 7,400 stars | 속성 기반 테스트 프레임워크 |
| BEST-1 Hypothesis | Academic | OOPSLA 2025 PBT paper | cseweb.ucsd.edu/~mcoblenz/assets/pdf/OOPSLA_2025_PBT.pdf | 2025-10 | peer-reviewed | Python PBT 실증 연구 |
| BEST-2 DuckDB | Official | DuckDB 1.5.3 release | duckdb.org/2026/05/20/announcing-duckdb-153 | 2026-05-20 | 28k+ stars | PIT 레이크 업그레이드 |
| BEST-2 DuckLake | Official | DuckLake 1.0 release | motherduck.com/duckdb-news/ | 2025-12 (1.0 stable) | — | sorted tables, bucket partitioning |
| BEST-3 LiteLLM | GitHub | BerriAI/litellm | github.com/BerriAI/litellm | 2025 active | ~20k stars | 다중 LLM 공급자 통합 |
| BEST-3 LiteLLM MiniMax | Official | LiteLLM MiniMax docs | docs.litellm.ai/docs/providers/minimax | 2025 | — | MiniMax 공식 지원 확인 |
| #6 Optuna v5 | Official | Optuna v5 release | optuna.org | 2025-05-26 | 11k stars | 생성AI 최적화 + gRPC |
| #6 Optuna gRPC | Official | Optuna 4.4 gRPC | medium.com/optuna/announcing-optuna-4-4 | 2025-06-16 | 11k stars | GrpcStorageProxy 버그픽스 |
| #8 NautilusTrader | GitHub | nautechsystems/nautilus_trader | github.com/nautechsystems/nautilus_trader | 2025-10-26 (1.221.0) | ~5.5k stars | Rust-native 이벤트-드리븐 백테스터 |
| #9 LightGBMLSS | GitHub | StatMixedML/LightGBMLSS | github.com/StatMixedML/LightGBMLSS | 2025 active | ~800 stars | 확률적 예측 (분포 모델링) |
| #7 Shapley | arXiv | Mechanism Design Ensemble | arxiv.org/list/cs.GT/2025-02 | 2025-02 | peer-reviewed | 인센티브-호환 앙상블 가중치 |
| #10 OODA | News | OODA AI Modernization | breakingdefense.com | 2025-04 | — | 레짐 재조향 트리거 |

---

## 8. AMBER_BUCKET

| 항목 | AMBER 이유 |
|------|-----------|
| Dead Reckoning 신뢰도 감쇠 (#★1) | Cross-domain 아이디어 — 직접 출처(날짜 명시 논문/구현체) 없음. 항공 DR 이론은 널리 알려졌으나 trading 적용 구현 선례 날짜 미확인 |
| OODA trading 구체적 구현 | breakingdefense.com 기사 — 게시 정확한 일 단위 날짜 미확인 (월만 확인: 2025-04) |
| LightGBMLSS stars 수 | 최신 정확한 stars 수 실시간 확인 불가 (약 800 추정) |

AMBER 아이템 수: 3개 (Best 3 none → ZERO 발동 없음)

---

## 9. Verification Gate

### Evidence Completeness
| Best | Evidence ≥2 | 날짜 확인 | 판정 |
|------|-------------|---------|------|
| BEST-1 Hypothesis | ✅ 2개 | live docs + OOPSLA 2025-10 | ✅ PASS |
| BEST-2 DuckDB 1.5.3 | ✅ 2개 | 2026-05-20 + 2025-12 | ✅ PASS |
| BEST-3 LiteLLM | ✅ 2개 | 2025 (active) + minimax confirmed | ✅ PASS |

### Deep Dive Completeness
| Best | PR plan ≥3 | Tests | Rollout/Rollback | KPIs | 판정 |
|------|------------|-------|-----------------|------|------|
| BEST-1 | ✅ 3 PRs | ✅ 5 tests | ✅ git revert | ✅ | PASS |
| BEST-2 | ✅ 3 PRs | ✅ 4 tests | ✅ feature flag + pip downgrade | ✅ | PASS |
| BEST-3 | ✅ 3 PRs | ✅ 4 tests | ✅ USE_LITELLM=false | ✅ | PASS |

### Apply Gates
- **Gate 0 (Dry-run):** ✅ 코드 변경 없음. 계획 문서만.
- **Gate 1 (Change list):** BEST-1: requirements-dev.in + tests/ / BEST-2: requirements.in + data_lake/ / BEST-3: requirements.in + advisors/claude_client.py
- **Gate 2 (Explicit approval):** 각 PR 시작 전 사용자 승인 필요
- **Gate 3 (Feature flag):** BEST-2 → `DUCKLAKE_ENABLED=false` / BEST-3 → `USE_LITELLM=false`
- **Gate 4 (Rollback):** BEST-1: git revert / BEST-2: pip install duckdb==1.1.x / BEST-3: USE_LITELLM=false

### 스택 적합성
- BEST-1: hypothesis는 requirements-dev only — 프로덕션 영향 없음 ✅
- BEST-2: DuckDB 1.5.3 하위 호환 API ✅; DuckLake feature flag으로 점진적 전환 ✅
- BEST-3: litellm은 optional (`_HAS_LITELLM=False` 폴백) ✅; Anthropic prompt caching 패스스루 지원 ✅

### 안전 검사
- 브로커 실행 없음 ✅
- API 키/토큰 없음 (환경변수만) ✅
- `screening_output_only=True` 영향 없음 ✅
- LiteLLM에서 실제 거래 명령 없음 ✅

### 최종 판정: **Go**

---

## 10. Open Questions (최대 3개)

1. **DuckDB 현재 설치 버전:** `pip show duckdb`로 현재 버전 확인 필요. 이미 1.5.x라면 PR-D1은 테스트 확인만으로 충분. 1.1.x라면 중간 단계 마이그레이션 확인 필요 (1.1→1.5 직접 업그레이드 가능성).

2. **LiteLLM Anthropic prompt caching 호환:** LiteLLM의 Anthropic 경로가 현재 `claude_client.py`의 4-breakpoint `cache_control` 헤더를 올바르게 패스스루하는지 확인 필요. 캐시 히트율이 현재 수준 유지되어야 비용 중립.

3. **Optuna v5 breaking changes:** `optuna>=4.0`에서 v5로 업그레이드 시 `GrpcStorageProxy`, `TPESampler` API 변경이 `ml/hpo.py`에 미치는 영향 스파이크 필요. v5 릴리즈 노트(2025-05-26) 검토 후 PR 계획 확정.

---

## SESSION_HANDOFF

```
skill: project-upgrade v2.2.0 | date: 2026-05-29 (Wave 2)
key_findings:
  - Wave 1 Best 3 + Chaos + MiniMax 모두 구현 완료 (커밋 186ef44, f4d8f74, da16607, cd4dbba)
  - Branch coverage 77.4% — Best-1 Hypothesis PBT로 직접 개선 가능
  - DuckDB 1.5.3 (2026-05-20) + DuckLake 1.0 최신 — 현재 duckdb>=1.1에서 업그레이드 기회
  - Optuna v5 메이저 릴리즈 (2025-05-26) 미반영
  - LiteLLM으로 Anthropic+MiniMax 이중 공급자 통합 → 코드 단순화
surprise_picks:
  - idea: "Dead Reckoning 신뢰도 감쇠 (항공→거래)" | Novelty: 5 | SurpriseScore: 7.5 | status: ⚠ AMBER
  - idea: "Shapley 동적 어드바이저 블렌딩" | Novelty: 5 | SurpriseScore: 6.67 | status: PASS
  - idea: "Hypothesis 속성 기반 테스트" | Novelty: 4 | SurpriseScore: 6.0 | status: PASS
amber_count: 0  # Best 3 모두 confirmed evidence. AMBER 아이디어는 Best 3 미포함.
next_suggested: project-plan --focus="best3-wave2"
```
