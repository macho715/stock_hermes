# PLAN_DOC — Wave 2 Best 3 Implementation
**Skill:** project-plan v2.2 | **Date:** 2026-05-29
**Source:** `20260529_project-upgrade-report-wave2.md` (Wave 2 Best 3)
**Branch target:** `claude/upgrade-investment-system-2Mc7x`

---

## A. Executive Summary

### 목표
Wave 2 Best 3를 순서대로 구현해 코드 품질, 인프라, LLM 운영 신뢰성을 한 단계 높인다.

| ID | 타이틀 | KPI 목표 | 소요 (일) |
|----|--------|---------|----------|
| W2-B1 | Hypothesis 속성 기반 테스트 | 브랜치 커버 77%→82%+, 불변 5개 이상 검증 | 3 |
| W2-B2 | DuckDB 1.5.3 + DuckLake 1.0 | DuckDB 최신화, PIT 쿼리 ≥20% 개선, 기존 테스트 100% pass | 3 |
| W2-B3 | LiteLLM 통합 LLM 게이트웨이 | Anthropic↔MiniMax 자동 폴백, 공급자 필드 audit 로그 추가 | 3 |

### 핵심 결정 (Decisions)
- **D-01**: Hypothesis는 `requirements-dev` 전용. 프로덕션 dep 아님.
- **D-02**: DuckDB 1.5.3 = 하위 호환. DuckLake는 `DUCKLAKE_ENABLED=false` feature flag 뒤에.
- **D-03**: LiteLLM은 optional import (`_HAS_LITELLM` 가드). 기존 Anthropic/MiniMax 분기 코드 폴백 유지.
- **D-04**: 어떤 PR도 `screening_output_only=True`, PIT `as_of` guard, audit_log 기존 이벤트 이름을 깨면 안 된다.

### 마일스톤
```
W2-B1 완료 → W2-B2 완료 → W2-B3 완료
      3일         3일          3일  = 총 9일
```

---

## B. Context & Requirements

### 문제 정의
| 번호 | 문제 | 영향 |
|------|------|------|
| B-1 | Branch coverage 77.4% — 시나리오 테스트로 잡히지 않는 엣지 케이스 존재 | 운영 중 예외 시 버그 발견 지연 |
| B-2 | DuckDB ≥1.1 고정 — 1.5.x의 sorted tables / deletion vectors / lambda syntax 미활용 | PIT 쿼리 최적화 기회 손실 |
| B-3 | claude_client.py 내 Anthropic/MiniMax 분기 619줄 — 공급자 추가 시 코드 수정 필요 | 운영 비용 추적 분산, 폴백 없음 |

### 유저 스토리
- **개발자(자신)**: "임의 입력에서 PIT guard가 깨지는지 pytest 실행 한 번으로 알고 싶다"
- **개발자**: "DuckDB를 1.5.x로 올려도 기존 테스트가 그대로 통과되는지 확인하고 싶다"
- **운영자**: "Anthropic API가 과부하일 때 자동으로 MiniMax로 전환되길 원한다"

### 제약
- `screening_output_only=True` / `PIT as_of guard` / `audit_log.jsonl` 기존 포맷 불변
- `numpy>=1.26,<3.0` / `shap>=0.50.0` 버전 범위 유지
- 기존 86%+ 라인 커버리지 유지 (하락 금지)
- 코드 변경은 `claude/upgrade-investment-system-2Mc7x` 브랜치에서만

---

## C. UI/UX Plan

이 플랜은 **CLI + API 백엔드 전용**이다. 시각적 UI 변경 없음.

### C1. 관련 사용자 접점

| 접점 | 변화 |
|------|------|
| `pytest` 실행 출력 | Hypothesis shrink 정보 출력 (기존 pytest output과 동일 포맷) |
| `DUCKLAKE_ENABLED=true` 환경변수 | DuckLake 경로 활성화 (기본값 false, 기존 경로 변경 없음) |
| `USE_LITELLM=true` 환경변수 | LiteLLM 게이트웨이 활성화 (기본값 false) |
| `audit_log/advisor.jsonl` | 신규 `provider` 필드 추가 (additive, 기존 필드 유지) |

---

## D. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    stock_rtx4060 core                        │
│                                                              │
│  ┌──────────────┐  W2-B1   ┌───────────────────────────┐   │
│  │ paper_trading│◄────────►│ tests/test_invariants_     │   │
│  │ validation   │  property│ hypothesis.py              │   │
│  │ data_provid. │   based  │ (Hypothesis @given)        │   │
│  └──────────────┘  testing └───────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  W2-B2   ┌───────────────────────────┐   │
│  │ data_lake/   │◄────────►│ DuckDB 1.5.3               │   │
│  │ store.py     │  upgrade │ + DuckLake feature flag    │   │
│  │ (DuckDBStore)│          └───────────────────────────┘   │
│                                                              │
│  ┌──────────────┐  W2-B3   ┌───────────────────────────┐   │
│  │ advisors/    │◄────────►│ LiteLLM Router             │   │
│  │ claude_client│  gateway │ anthropic → minimax        │   │
│  │ .py          │          │ fallback chain             │   │
│  └──────────────┘          └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### D1. 컴포넌트 변경 범위

| 컴포넌트 | W2-B1 | W2-B2 | W2-B3 |
|---------|-------|-------|-------|
| `tests/test_invariants_hypothesis.py` | **신규** | — | — |
| `requirements-dev.in` | hypothesis 추가 | — | — |
| `requirements.in` | — | duckdb>=1.5.3 | litellm>=1.55 |
| `data_lake/store.py` | — | 버전 호환성 확인 | — |
| `data_lake/__init__.py` | — | DuckLake feature flag | — |
| `advisors/claude_client.py` | — | — | `_call_with_litellm()` 추가 |
| `advisors/audit.py` | — | — | `provider` 필드 추가 |
| `tests/test_claude_client.py` | — | — | LiteLLM 폴백 테스트 |

---

## E. Data Model & API Contract

### E1. 변경되는 데이터 구조

#### E1-1. `audit_log/advisor.jsonl` — W2-B3 추가 필드
```json
{
  "ts": "2026-05-29T10:00:00Z",
  "ticker": "005930.KS",
  "agent": "news_sentiment",
  "prompt_hash": "abc123",
  "score": 0.35,
  "tokens_in": 12400,
  "tokens_out": 380,
  "cost_usd": 0.0124,
  "provider": "anthropic"   // ← 신규 (기존 없음; litellm disabled 시 null)
}
```

#### E1-2. DuckDB 스키마 — W2-B2 변경 없음
기존 hive-partitioned Parquet 스키마 유지. DuckLake DDL은 `DUCKLAKE_ENABLED=true` 시에만 병렬 생성.

### E2. 환경 변수 API

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DUCKLAKE_ENABLED` | `false` | DuckLake 1.0 경로 활성화 |
| `USE_LITELLM` | `false` | LiteLLM 게이트웨이 활성화 |
| `LITELLM_FALLBACK_MODELS` | `"openai/MiniMax-M2.7"` | 폴백 모델 리스트(콤마 구분) |
| `MINIMAX_BASE_URL` | `"https://api.minimax.io/v1"` | 기존 변수 유지 |

---

## F. Repo/Package Structure

### F1. 변경 파일 목록 (전체)

```
stock_1901/
├── requirements.in                          # duckdb>=1.5.3, litellm>=1.55 추가
├── requirements-dev.in                      # hypothesis>=6.100 추가
├── src/stock_rtx4060/
│   ├── advisors/
│   │   ├── claude_client.py                 # W2-B3: _call_with_litellm() 추가 (~50줄)
│   │   └── audit.py                         # W2-B3: provider 필드 추가
│   └── data_lake/
│       ├── __init__.py                      # W2-B2: DuckLake feature flag 추가
│       └── store.py                         # W2-B2: 1.5.3 호환성 확인 (변경 minimal)
└── tests/
    ├── test_invariants_hypothesis.py        # W2-B1: 신규 (5개 불변 @given 테스트)
    ├── test_ducklake_smoke.py               # W2-B2: 신규 (4개 smoke 테스트)
    └── test_claude_client.py                # W2-B3: LiteLLM 폴백 테스트 추가 (~40줄)
```

### F2. 벤치마크 참조 패턴

| 패턴 | 소스 repo | 적용 위치 |
|------|----------|----------|
| `@given` + `@settings(max_examples=50)` | HypothesisWorks/hypothesis | test_invariants_hypothesis.py |
| `_HAS_LITELLM` optional import guard | BerriAI/litellm 패턴 | claude_client.py |
| `DUCKLAKE_ENABLED` feature flag | DuckDB extension pattern | data_lake/__init__.py |

---

## G. Implementation Plan

### G1. Epics

| Epic | 설명 | PR 수 | 예상 일수 |
|------|------|-------|----------|
| **W2-B1** Hypothesis PBT | 속성 기반 테스트 도입 | 3 | 3 |
| **W2-B2** DuckDB 1.5.3 | DuckDB 업그레이드 + DuckLake flag | 3 | 3 |
| **W2-B3** LiteLLM gateway | LLM 게이트웨이 + audit 개선 | 3 | 3 |

---

### G2. Cross-Domain Rationale (W2-B1 — Novelty 4)

**의료 임상시험 → 소프트웨어 불변 검증**

임상시험에서 "어떤 환자 프로파일(나이/체중/기저질환 조합)에서도 약이 특정 범위 이상의 독성을 보여서는 안 된다"는 속성을 통계적 표본으로 검증한다. Hypothesis PBT는 동일한 원리로 "어떤 입력 조합에서도 `screening_output_only=True`여야 한다" 같은 불변을 수천 개의 자동 생성 입력으로 검증한다. 임상시험이 단일 케이스가 아닌 모집단을 검증하듯, PBT는 단일 예제 테스트가 아닌 입력 공간 전체를 탐색한다.

---

### G3. PR Plan (전체 9개)

#### W2-B1: Hypothesis PBT

| PR | 제목 | 파일 | 핵심 내용 | 롤백 |
|----|------|------|---------|------|
| PR-H1 | `test(W2-B1): add hypothesis to dev deps + skeleton` | `requirements-dev.in`, `tests/test_invariants_hypothesis.py` | `hypothesis>=6.100` 추가; `test_screening_output_only` 1개 @given 불변 | `git revert` |
| PR-H2 | `test(W2-B1): add PIT as_of + GAP-01 invariant tests` | `tests/test_invariants_hypothesis.py` | `@given(st.dates(..., min=2027))` PIT 미래날짜 RuntimeError; `@given(score=st.floats(0,55.99))` GAP-01 | `git revert` |
| PR-H3 | `test(W2-B1): add portfolio weight + advisory score invariants` | `tests/test_invariants_hypothesis.py` | `weights.sum() ≈ 1.0`; `advisory_score ∈ [-1,+1]`; `@settings(max_examples=100)` | `git revert` |

#### W2-B2: DuckDB 1.5.3 + DuckLake

| PR | 제목 | 파일 | 핵심 내용 | 롤백 |
|----|------|------|---------|------|
| PR-D1 | `chore(W2-B2): bump duckdb>=1.5.3, verify existing tests` | `requirements.in` | 버전 범프; CI 통과 확인; lambda syntax `->` → `lambda x: x+1` 변환 필요 시 | `pip install duckdb==1.1.x` |
| PR-D2 | `feat(W2-B2): add DUCKLAKE_ENABLED feature flag + DDL` | `data_lake/__init__.py`, `data_lake/store.py` | `DUCKLAKE_ENABLED=false` guard; `CREATE TABLE IF NOT EXISTS lake.ohlcv` DDL | `DUCKLAKE_ENABLED=false` |
| PR-D3 | `test(W2-B2): add ducklake smoke + version compat tests` | `tests/test_ducklake_smoke.py` | 4개 테스트: 버전, flag 기본값, write/read roundtrip, PIT guard 유지 | `git revert` |

#### W2-B3: LiteLLM Gateway

| PR | 제목 | 파일 | 핵심 내용 | 롤백 |
|----|------|------|---------|------|
| PR-L1 | `feat(W2-B3): add litellm dep + _call_with_litellm stub` | `requirements.in`, `advisors/claude_client.py` | `litellm>=1.55`; `_HAS_LITELLM` guard; `_call_with_litellm()` 빈 구현 | `pip uninstall litellm` |
| PR-L2 | `feat(W2-B3): wire litellm Router into advisor call path` | `advisors/claude_client.py`, `tests/test_claude_client.py` | `USE_LITELLM=true` 시 `litellm.Router` 경로; Anthropic→MiniMax 폴백 테스트 | `USE_LITELLM=false` |
| PR-L3 | `feat(W2-B3): add provider field to advisor audit log` | `advisors/audit.py`, `advisors/claude_client.py` | `provider` 필드 additive 추가; `USE_LITELLM=false` 시 `null` | `git revert` (additive-only) |

---

### G4. Feature Flags 요약

| Flag | 기본값 | 활성화 효과 | 안전한 롤백 |
|------|--------|------------|------------|
| `DUCKLAKE_ENABLED` | `false` | DuckLake DDL 활성화 | `false`로 재설정 |
| `USE_LITELLM` | `false` | LiteLLM Router 경로 | `false`로 재설정 |

---

### G5. Timeline

```
Day 1-3:  W2-B1 (PR-H1 → H2 → H3)
           - pip install hypothesis
           - test_invariants_hypothesis.py 5개 불변
           - CI 통과 확인

Day 4-6:  W2-B2 (PR-D1 → D2 → D3)
           - duckdb 버전 범프
           - DUCKLAKE_ENABLED feature flag
           - smoke test

Day 7-9:  W2-B3 (PR-L1 → L2 → L3)
           - litellm 설치
           - Router 통합
           - audit provider 필드
```

---

## H. Testing Strategy

### H1. Test Pyramid

```
          ┌──────────────┐
          │  E2E (0개)   │  ← 이번 범위 아님
          ├──────────────┤
          │ Integration  │  DuckLake roundtrip, LiteLLM Router 실제 HTTP mock
          │  (6개)       │
          ├──────────────┤
          │   Unit PBT   │  Hypothesis @given 불변 (5개)
          │  (5개)       │
          ├──────────────┤
          │  Unit smoke  │  각 PR별 기본 smoke (3×3=9개)
          │  (9개)       │
          └──────────────┘
```

### H2. W2-B1 테스트 상세

```python
# tests/test_invariants_hypothesis.py
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# 불변 1 — screening_output_only 항상 True
@given(
    score=st.floats(0, 100, allow_nan=False),
    signal=st.sampled_from(["BUY", "SELL", "HOLD"]),
)
@settings(max_examples=200)
def test_screening_output_only_invariant(score, signal):
    result = evaluate_signal(signal, score)
    assert result.screening_output_only is True

# 불변 2 — GAP-01: BUY score < 56 항상 reject
@given(score=st.floats(0.0, 55.99, allow_nan=False))
def test_buy_below_threshold_always_rejected(score):
    result = evaluate_signal("BUY", score)
    assert result.status == "rejected"
    assert "score" in result.reason.lower()

# 불변 3 — PIT as_of 미래 날짜 → RuntimeError
@given(
    days_future=st.integers(min_value=1, max_value=3650),
)
def test_pit_future_as_of_raises(days_future, monkeypatch):
    from datetime import date, timedelta
    future = (date.today() + timedelta(days=days_future)).isoformat()
    with pytest.raises(RuntimeError):
        load_ohlcv_with_provider("005930.KS", as_of=future)

# 불변 4 — advisory_score ∈ [-1, +1]
@given(raw_score=st.floats(-10, 10, allow_nan=False))
def test_advisory_score_clipped(raw_score):
    clipped = clip_advisory_score(raw_score)
    assert -1.0 <= clipped <= 1.0

# 불변 5 — portfolio weights 합 ≈ 1.0
@given(n=st.integers(min_value=2, max_value=20))
def test_portfolio_weights_sum_to_one(n, tmp_path):
    returns = pd.DataFrame(
        np.random.randn(252, n),
        columns=[f"S{i}" for i in range(n)]
    )
    weights = optimize(returns)
    assert abs(weights.sum() - 1.0) < 1e-6
```

### H3. CI Gates

```bash
# W2-B1 완료 기준
pytest tests/test_invariants_hypothesis.py -v        # 5개 pass
pytest --cov=stock_rtx4060 --cov-fail-under=75 -q    # 기존 통과 유지

# W2-B2 완료 기준
pytest tests/test_ducklake_smoke.py -v               # 4개 pass
pytest --cov=stock_rtx4060 -q                        # 기존 통과 유지

# W2-B3 완료 기준
pytest tests/test_claude_client.py -v                # 기존 + 신규 pass
python -c "from stock_rtx4060.advisors.claude_client import ClaudeClient; print('OK')"
```

---

## I. Observability & Operations

### I1. Logging 변경사항

#### W2-B3: advisor.jsonl 신규 필드
```
# 기존
{"ts": "...", "cost_usd": 0.012, ...}
# 변경 후 (additive)
{"ts": "...", "cost_usd": 0.012, "provider": "anthropic"}
# USE_LITELLM=false 시
{"ts": "...", "cost_usd": 0.012, "provider": null}
```

### I2. 운영 메트릭 (변경 없음)
기존 Prometheus/Grafana 알림 영향 없음. LiteLLM 활성화 시 `provider` 필드로 공급자별 비용 추적 가능.

### I3. Runbook — LiteLLM 폴백 발생 시
1. `grep '"provider": "minimax"' audit_log/advisor.jsonl` → 폴백 빈도 확인
2. Anthropic 오류 원인 조사: rate limit vs outage
3. `USE_LITELLM=false` 설정으로 즉시 기존 경로 복귀

---

## J. Error Handling & Recovery

### J1. W2-B1 Hypothesis 오류 분류

| 오류 유형 | 예상 원인 | 대응 |
|---------|---------|------|
| `UnsatisfiedAssumption` 과다 | `assume()` 조건이 너무 엄격 | `st.integers(...)` 범위 조정 |
| 테스트 느림 (`HealthCheck.too_slow`) | 불변 내부에서 IO 호출 | `monkeypatch`로 IO mock화 |
| `hypothesis.errors.Flaky` | 랜덤 의존 코드 | 시드 고정 `@settings(deriving=False)` |

### J2. W2-B2 DuckDB 업그레이드 오류 분류

| 오류 유형 | 예상 원인 | 대응 |
|---------|---------|------|
| `SyntaxError: lambda ->` | 1.2 이하 lambda syntax | `x -> x+1` → `lambda x: x+1` 변환 |
| `DuckDBPyConnection deprecated` | 1.4+ API 변경 | 릴리즈 노트 확인 후 호출부 수정 |
| 기존 Parquet 읽기 실패 | 스토리지 버전 불일치 | DuckDB storage version bump 확인 |

### J3. W2-B3 LiteLLM 오류 분류

| 오류 유형 | 예상 원인 | 대응 |
|---------|---------|------|
| `litellm.exceptions.RateLimitError` | Anthropic 과부하 | 자동 MiniMax 폴백 |
| `litellm.exceptions.AuthenticationError` | API 키 누락 | `has_live_advisor_key()` 사전 체크 |
| prompt cache 미적용 | LiteLLM이 헤더 미전달 | `USE_LITELLM=false`로 fallback |

---

## K. Dependencies, Security, Risks

### K1. 신규 의존성

| 패키지 | 버전 | 위치 | 설치 조건 |
|--------|------|------|---------|
| `hypothesis` | >=6.100 | requirements-dev.in | CI dev 환경만 |
| `litellm` | >=1.55 | requirements.in | optional import (graceful) |
| `duckdb` | >=1.5.3 | requirements.in | 하위 호환 업그레이드 |

### K2. Security 체크

- `hypothesis`: 테스트 전용, 프로덕션 dep 아님 ✅
- `litellm`: API 키는 기존 환경변수(`ANTHROPIC_API_KEY`, `MINIMAX_API_KEY`) 그대로 사용 — 신규 키 노출 없음 ✅
- `duckdb 1.5.3`: in-process DB, 네트워크 노출 없음 ✅
- `DUCKLAKE_ENABLED`: false 기본값 — 실수로 DuckLake DDL 실행 불가 ✅

### K3. Risk Register

| # | 리스크 | 가능성 | 영향 | 완화 |
|---|--------|--------|------|------|
| R-01 | DuckDB 1.5.x lambda syntax 변경으로 기존 코드 구문 에러 | 중 | 중 | PR-D1에서 `duckdb.execute()` 호출부 전수 확인 |
| R-02 | LiteLLM Anthropic prompt caching 헤더 미전달 → 캐시 히트율 하락 | 중 | 중 | `USE_LITELLM=false` fallback; 헤더 패스스루 단위 테스트 추가 |
| R-03 | Hypothesis 불변 테스트가 너무 느려 CI 시간 초과 | 낮 | 중 | `@settings(max_examples=50)` 제한; `deadline=None` |
| R-04 | litellm Router의 `fallbacks=` 파라미터 버전 호환성 | 낮 | 중 | litellm 1.55+ 버전 고정; docs 확인 |
| R-05 | DuckLake DDL이 기존 Parquet 데이터와 충돌 | 낮 | 낮 | `DUCKLAKE_ENABLED=false`(기본) + 별도 `lake.*` 네임스페이스 |

### K4. Change Control
- 모든 PR은 `claude/upgrade-investment-system-2Mc7x` 브랜치에서
- CI 통과 + `pytest --cov-fail-under=75` 통과 후 main 머지
- 브로커 실행 없음; `screening_output_only=True` 불변 유지 확인

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | accessed |
|----------|----------|-------|-----|------|----------|---------|
| W2-B1 Hypothesis | Official | Hypothesis Docs | hypothesis.readthedocs.io | live | 7,400 stars | 2026-05-29 |
| W2-B1 Hypothesis | Academic | OOPSLA 2025 PBT | cseweb.ucsd.edu/~mcoblenz/... | 2025-10 | peer-reviewed | 2026-05-29 |
| W2-B2 DuckDB | Official | DuckDB 1.5.0 release blog | duckdb.org/2026/03/09/announcing-duckdb-150 | 2026-03-09 | 28k+ stars | 2026-05-29 |
| W2-B2 DuckDB | Official | DuckDB 1.5.3 release | duckdb.org/2026/05/20/announcing-duckdb-153 | 2026-05-20 | 28k+ stars | 2026-05-29 |
| W2-B2 DuckLake | Official | DuckLake 1.0 production-ready | motherduck.com/duckdb-news/ | 2025-12 | — | 2026-05-29 |
| W2-B3 LiteLLM | GitHub | BerriAI/litellm | github.com/BerriAI/litellm | 2025 active | ~20k stars | 2026-05-29 |
| W2-B3 LiteLLM docs | Official | LiteLLM Routing & Fallback | docs.litellm.ai/docs/routing | 2025 | — | 2026-05-29 |
| W2-B3 LiteLLM MiniMax | Official | LiteLLM MiniMax support | docs.litellm.ai/docs/providers/minimax | 2025 | — | 2026-05-29 |

### ㅋ2. Benchmarked Repo Notes

| Repo | Stars | 적용 패턴 |
|------|-------|---------|
| `HypothesisWorks/hypothesis` | 7.4k | `@given` + `@settings(max_examples=N)` + `assume()` 패턴 |
| `BerriAI/litellm` | 20k+ | `Router(model_list=[...], fallbacks=[...])` 패턴; `_HAS_LITELLM` optional guard |
| `duckdb/duckdb` | 28k+ | DuckLake extension `ATTACH 'ducklake:...' AS lake` DDL |

### ㅋ3. AMBER_BUCKET

| 항목 | 이유 | 플랜 영향 |
|------|------|---------|
| Dead Reckoning 신뢰도 감쇠 | Cross-domain 직접 구현 선례 날짜 미확인 | 이번 플랜 범위 제외 |
| DuckLake 1.0 정확한 GA 날짜 | motherduck.com에서 월 단위만 확인 (2025-12) | PR-D2는 feature flag 뒤에서 안전하게 진행 |

### ㅋ4. Glossary

| 용어 | 설명 |
|------|------|
| PBT | Property-Based Testing — Hypothesis 프레임워크 기반 임의 입력 검증 |
| DuckLake | DuckDB 확장 — lakehouse 메타데이터를 DB 내에서 관리 |
| LiteLLM | 100+ LLM 공급자 통합 Python SDK; Router로 폴백 지원 |
| PIT guard | `as_of` 미래 날짜 → `RuntimeError` 불변 (look-ahead bias 방지) |
| Feature flag | 환경변수 기반 on/off 스위치 (코드 변경 없이 롤백 가능) |

---

## Apply Gates (실행 전 필수 체크)

| Gate | 조건 | 판정 |
|------|------|------|
| Gate 0: Dry-run | 이 문서는 코드 변경 없음 | ✅ PASS |
| Gate 1: Change list | 변경 파일 목록 F1에 명시됨 | ✅ PASS |
| Gate 2: Explicit approval | 각 PR 시작 전 사용자 승인 필요 | ⏳ 대기 |
| Gate 3: Feature flag | DUCKLAKE_ENABLED, USE_LITELLM 기본값 false | ✅ PASS |
| Gate 4: Rollback plan | 각 PR 롤백 방법 G3에 명시됨 | ✅ PASS |
| Gate 5: Test coverage | 기존 86% 유지 + 신규 테스트 추가 | ✅ PASS |
| Gate 6: Safety invariants | screening_output_only / PIT guard / audit_log 포맷 불변 | ✅ PASS |

### 최종 판정: **Go** (Gate 2 승인 후 PR-H1부터 시작)
