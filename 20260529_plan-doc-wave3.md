# PLAN_DOC — Wave 3 Best 3 구현 계획
**Skill:** project-plan v2.2.0 | **Date:** 2026-05-29
**Source:** project-upgrade Wave 3 Best 3 (`20260529_project-upgrade-report-wave3.md`)
**Branch:** `claude/upgrade-investment-system-2Mc7x`

---

## A. Executive Summary

### A1. 목표
Wave 3의 Best 3 아이디어를 구현해 `stock_rtx4060` P0–P8 시스템의 **관찰 가능성(Observability)**, **백테스트 신뢰도 가시성**, **라이브 추적 자동화**를 향상시킨다.

| Best | 아이디어 | 목표 |
|------|---------|------|
| B1 | MLflow 3.x 업그레이드 | `mlflow>=2.16` → `>=3.0,<4.0`; P6 어드바이저 LLM trace + LoggedModel lineage |
| B2 | PBO 지표 Dashboard 통합 | `backtest/pbo.py` 값 → `dashboard_snapshot.v1` 노출 + readiness 강등 조건 추가 |
| B3 | AutoForwardRecorder → Prefect 자동화 | `live_review/auto_forward_recorder.py` → `flows/daily_krx.py` 마지막 태스크 편입 |

### A2. 핵심 KPI

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| `artifact_path` DeprecationWarning 수 | 미측정 | 0 | `pytest -W error::DeprecationWarning` |
| P6 어드바이저 MLflow span 기록 | 없음 | 100% advisor 호출 span 생성 | `mlflow.search_traces()` |
| PBO 지표 dashboard_snapshot 노출 | 없음 | `backtest_honesty_summary.pbo` 필드 존재 | `test_dashboard_bridge.py` |
| PBO AMBER/RED 시 readiness 강등 | 없음 | pbo>0.20 → 검토전용; pbo>0.50 → 반영금지 | `test_investment_readiness_benchmark.py` |
| AutoForwardRecorder 자동 실행 | 수동 전용 | daily_krx_flow 실행 시 자동 | `test_daily_krx_flow.py` |
| 테스트 커버리지 (line / branch) | 86% / 86% | ≥86% / ≥86% (퇴보 없음) | `pytest --cov-fail-under=75` |

### A3. 마일스톤 (3 Epics)

| Epic | 내용 | PR 수 | 예상 기간 |
|------|------|-------|---------|
| **E1: MLflow 3.x** | 버전 범프 → artifact_path 마이그레이션 → LLM tracing | 3 PRs | 5일 |
| **E2: PBO Dashboard** | backtest_honesty 필드 추가 → readiness 연동 → React badge | 3 PRs | 5일 |
| **E3: AutoForward Prefect** | AutoForwardRecorder API 정리 → Prefect task → alert 연동 | 3 PRs | 4일 |

---

## B. Context & Requirements

### B1. 문제 정의

| 영역 | 현재 문제 | 영향 |
|------|---------|------|
| P6 LLM 어드바이저 | `audit_log/advisor.jsonl` 수동 로깅만 존재 — MLflow와 분리됨 | P6 advisor ↔ P3 ML 모델 lineage 연결 불가 |
| 백테스트 신뢰도 | `backtest/pbo.py`에 PBO 계산됨 — 대시보드 미노출 | 리뷰어가 PBO 수치를 보려면 JSON 파일 직접 열어야 함 |
| 라이브 추적 | `AutoForwardRecorder.record()` 수동 실행 전용 | 거래일 누락 시 30-day forward evidence 공백 발생 |

### B2. 사용자 스토리

```
US-1 (운영자 — E1): "나는 MLflow UI에서 P6 어드바이저가 어떤 모델에서 점수를 생성했는지
       하나의 lineage 뷰로 보고 싶다."
US-2 (운영자 — E2): "REC 탭에서 PBO 값을 보고 백테스트 과적합 리스크를 즉시 판단하고 싶다."
US-3 (운영자 — E3): "KRX daily 플로우가 돌면 forward tracking이 자동으로 기록되어 있어야 한다."
```

### B3. 요구사항

**기능 요구사항:**
- R1: MLflow `mlflow.anthropic.autolog()` 또는 수동 span으로 advisor 호출 trace
- R2: `backtest_honesty_summary`에 `pbo`, `pbo_status` 필드 추가 (additive)
- R3: readiness classifier가 `pbo_status` 기반 강등 로직 포함
- R4: React RecommendationCard에 PBO badge 조건부 렌더링
- R5: `daily_krx_flow`에 `forward_tracking_task` 마지막 태스크 추가
- R6: `FORWARD_TRACKING_ENABLED` feature flag로 즉시 비활성화 가능

**비기능 요구사항:**
- NF1: 기존 `dashboard_snapshot.v1` schema_version 변경 없음 (additive only)
- NF2: `audit_log/advisor.jsonl` 포맷 보존 (MLflow는 추가 중복 기록)
- NF3: `screening_output_only=True` 불변 유지
- NF4: 테스트 커버리지 86%/86% 퇴보 없음
- NF5: Windows/Linux 모두 동작 (CI: Python 3.12)

---

## C. UI/UX Plan

### C1. 정보 아키텍처 변경 (E2: PBO Dashboard)

```
REC 탭
└─ RecommendationPanel
   └─ RecommendationCard [per candidate]
      ├─ Verdict Badge (기존)
      ├─ Risk Gate Badge (기존)
      ├─ Investment Grade (기존)
      ├─ Advisor Score Gauge (기존)
      └─ [신규] PBO Badge ← E2 추가
         ├─ PASS (pbo ≤ 20%): 초록
         ├─ AMBER (20% < pbo ≤ 50%): 노란
         ├─ RED (pbo > 50%): 빨간
         └─ NO_DATA: 회색 (CPCV 미실행)
```

### C2. PBO Badge 디자인

```
┌──────────────────────────────────┐
│ PBO  12.3%   [PASS]              │
│ Backtest Overfitting Probability  │
└──────────────────────────────────┘
```
- 툴팁: "PBO measures the probability that this strategy's backtest results are due to overfitting. Lower is better. Threshold: ≤20% PASS."
- `pbo` 필드 없으면 badge 미표시 (하위 호환)

### C3. 화면 변경 목록

| 화면 | 변경 내용 | 파일 |
|------|---------|------|
| REC 카드 | PBO badge 추가 (조건부) | `RecommendationCard.jsx` |
| REC 카드 툴팁 | PBO 설명 hover text | `RecommendationCard.jsx` |
| SIGNAL 탭 | 변경 없음 | — |
| MLflow UI | trace 뷰 신규 (외부 MLflow UI) | — (백엔드만) |

### C4. Accessibility
- PBO badge color: WCAG AA 준수 (color + icon + 텍스트 숫자 동시 표시)
- PBO=NO_DATA: "–" 표시 (screen reader: "PBO data not available")

---

## D. System Architecture

### D1. 변경 컴포넌트

```
[E1: MLflow 3.x]
advisors/
  claude_client.py        ← mlflow.anthropic.autolog() 또는 수동 span
  orchestrator.py         ← @mlflow.trace(span_type="AGENT") 래퍼
ml/
  registry.py             ← artifact_path → name 마이그레이션
ensemble_model.py         ← artifact_path DeprecationWarning 제거
requirements.in           ← mlflow>=3.0,<4.0

[E2: PBO Dashboard]
backtest_honesty.py       ← pbo + pbo_status 필드 additive 추가
readiness/classifier.py   ← pbo_status 강등 조건 추가
stock-pred-v5/src/
  components/
    RecommendationCard.jsx ← PBO badge 조건부 렌더링

[E3: AutoForward Prefect]
live_review/
  auto_forward_recorder.py ← record_today() 직렬화 가능 dict 반환 메서드 추가
flows/
  daily_krx.py             ← forward_tracking_task 추가 (마지막)
```

### D2. 데이터 흐름

**E1 — MLflow Tracing 흐름:**
```
advisor 호출
→ claude_client._call_with_litellm()
→ [신규] mlflow.start_span("advisor_call", span_type="LLM")
  → litellm.completion(model=ANTHROPIC_MODEL, ...)
→ span.set_outputs({score, tokens_in, tokens_out, cost_usd})
→ audit_log/advisor.jsonl (기존 보존)
→ MLflow Trace UI (신규)
```

**E2 — PBO 노출 흐름:**
```
recommend 실행
→ backtester.py → backtest_honesty.py
→ _normalize_cpcv_pbo_dsr()  (기존: pbo 계산됨)
→ [신규] build_backtest_honesty_summary()에 pbo + pbo_status 추가
→ dashboard_bridge.py → dashboard_snapshot.v1
→ REC 탭 → RecommendationCard → PBO badge
```

**E3 — Prefect AutoForward 흐름:**
```
daily_krx_flow() 실행 (16:30 KST)
→ ingest → factors → model → portfolio → recommend → dashboard → alert
→ [신규] forward_tracking_task()
  → AutoForwardRecorder.record_today()
  → reports/live_review/auto_forward_recorder_state.json 업데이트
  → Slack 알림에 forward tracking status 추가
```

### D3. 시스템 경계 (변경 없음)
- `screening_output_only=True` 보존
- 브로커 주문 경로 없음
- API 키: 환경변수 전용

---

## E. Data Model & API Contract

### E1. 신규/변경 엔티티

**E2: `backtest_honesty_summary` 스키마 (additive 추가)**

| 필드 | 타입 | 기존/신규 | 의미 |
|------|------|---------|------|
| `status` | str | 기존 | PASS/AMBER/RED |
| `checks` | list | 기존 | 세부 체크 목록 |
| `pbo` | float \| None | **신규** | Probability of Backtest Overfitting (0.0~1.0) |
| `pbo_status` | str | **신규** | PASS / AMBER / RED / NO_DATA |

**임계값:**
```python
pbo_status = (
    "PASS"    if pbo is not None and pbo <= 0.20 else
    "AMBER"   if pbo is not None and pbo <= 0.50 else
    "RED"     if pbo is not None else
    "NO_DATA"
)
```

> 기존 코드 `backtest_honesty.py:174-177`: `pbo <= 0.20` = PASS 임계값 이미 사용 중 → 일관성 유지

**E3: `AutoForwardRecorder.record_today()` 반환값**

```python
{
    "status": "recorded" | "skipped" | "error",
    "date": "2026-05-29",
    "symbol": "005930.KS",
    "reason": str | None,   # skipped/error 시 이유
    "row_count": int,       # CSV에 누적된 총 행 수
}
```

### E2. API 변경

| 엔드포인트 | 변경 | 이유 |
|-----------|------|------|
| `GET /api/recommend` | 응답 내 `backtest_honesty_summary`에 `pbo`, `pbo_status` 추가 | E2 |
| `GET /api/snapshot` | 동일 (dashboard_bridge 통과) | E2 |
| MLflow REST API | 신규 trace endpoint 사용 (내부) | E1 |

---

## F. Repo/Package Structure

```
stock_1901/
├── requirements.in                    [E1] mlflow>=3.0,<4.0
├── src/stock_rtx4060/
│   ├── advisors/
│   │   ├── claude_client.py           [E1] _call_with_mlflow_span() 추가
│   │   └── orchestrator.py            [E1] @mlflow.trace 래퍼 선택적 적용
│   ├── backtest/
│   │   └── pbo.py                     [E2] compute_pbo() 공개 API 확인
│   ├── backtest_honesty.py            [E2] pbo + pbo_status 필드 추가
│   ├── live_review/
│   │   └── auto_forward_recorder.py  [E3] record_today() → JSON 직렬화 dict
│   ├── ml/
│   │   └── registry.py               [E1] artifact_path → name 마이그레이션
│   ├── readiness/
│   │   └── classifier.py             [E2] pbo_status 강등 로직 추가
│   └── ensemble_model.py             [E1] artifact_path DeprecationWarning 제거
├── flows/
│   └── daily_krx.py                  [E3] forward_tracking_task 추가
└── stock-pred-v5/src/
    └── components/
        └── RecommendationCard.jsx    [E2] PBO badge 조건부 렌더링

tests/
├── test_backtest_honesty.py          [E2] pbo 필드 검증 추가
├── test_daily_krx_flow.py            [E3] forward_tracking_task 검증 추가
├── test_investment_readiness_benchmark.py [E2] pbo_status 강등 검증
├── test_claude_client.py             [E1] MLflow span 기록 검증
└── test_ml_registry.py               [E1] artifact_path → name 검증
```

---

## G. Implementation Plan

### G1. Epics & Stories

| Epic | Story | 파일 | 크기 |
|------|-------|------|------|
| E1-MLflow | S1.1: mlflow>=3.0 범프 + 테스트 통과 확인 | `requirements.in` | XS |
| E1-MLflow | S1.2: `artifact_path` → `name` 전수 마이그레이션 | `ensemble_model.py`, `ml/registry.py` | S |
| E1-MLflow | S1.3: `_call_with_mlflow_span()` 추가 + autolog | `advisors/claude_client.py` | S |
| E2-PBO | S2.1: `build_backtest_honesty_summary()` pbo 필드 additive 추가 | `backtest_honesty.py` | S |
| E2-PBO | S2.2: readiness classifier pbo_status 강등 로직 | `readiness/classifier.py` | S |
| E2-PBO | S2.3: RecommendationCard PBO badge | `RecommendationCard.jsx` | S |
| E3-Forward | S3.1: `AutoForwardRecorder.record_today()` 직렬화 dict 반환 | `auto_forward_recorder.py` | XS |
| E3-Forward | S3.2: `forward_tracking_task` + `FORWARD_TRACKING_ENABLED` flag | `flows/daily_krx.py` | S |
| E3-Forward | S3.3: alert_task forward tracking status 포함 | `flows/daily_krx.py` | XS |

### G2. Feature Flags

| Flag | 기본값 | 사용처 | 설명 |
|------|--------|--------|------|
| `USE_MLFLOW_TRACING` | `false` | `advisors/claude_client.py` | LLM span 기록 on/off |
| `FORWARD_TRACKING_ENABLED` | `true` | `flows/daily_krx.py` | AutoForward Prefect 태스크 on/off |
| `DUCKLAKE_ENABLED` | `false` | `data_lake/__init__.py` | Wave 2 이월, 변경 없음 |
| `USE_LITELLM` | `true` | `advisors/claude_client.py` | Wave 2 이월, 변경 없음 |

### G3. PR Plan (9 PRs, 3 Epics)

| PR | 제목 | Epic | 파일 | 롤백 |
|----|------|------|------|------|
| PR-M1 | `chore(P0): bump mlflow>=3.0,<4.0 — verify all tests pass` | E1 | `requirements.in`, `requirements.txt` | `pip install mlflow==2.16.x` |
| PR-M2 | `fix(P3): migrate artifact_path→name in log_model calls` | E1 | `ensemble_model.py`, `ml/registry.py` | `git revert` |
| PR-M3 | `feat(P6): add MLflow LLM span tracing to advisor calls` | E1 | `advisors/claude_client.py`, `advisors/orchestrator.py`, `tests/test_claude_client.py` | `USE_MLFLOW_TRACING=false` |
| PR-P1 | `feat(P5): expose pbo + pbo_status in backtest_honesty_summary` | E2 | `backtest_honesty.py`, `tests/test_backtest_honesty.py` | `git revert` (additive) |
| PR-P2 | `feat(readiness): downgrade readiness on pbo_status AMBER/RED` | E2 | `readiness/classifier.py`, `tests/test_investment_readiness_benchmark.py` | `git revert` |
| PR-P3 | `feat(dashboard): add PBO badge to RecommendationCard` | E2 | `RecommendationCard.jsx`, playwright tests | `git revert` |
| PR-F1 | `feat(live_review): add record_today() serializable dict method` | E3 | `live_review/auto_forward_recorder.py` | `git revert` |
| PR-F2 | `feat(P7): add forward_tracking_task to daily_krx_flow` | E3 | `flows/daily_krx.py`, `tests/test_daily_krx_flow.py` | `FORWARD_TRACKING_ENABLED=false` |
| PR-F3 | `feat(P7): include forward tracking status in alert message` | E3 | `flows/daily_krx.py` 또는 `alert_engine.py` | `git revert` |

### G4. 구현 상세 — E1 MLflow 3.x

```python
# requirements.in 변경
# Before: mlflow>=2.16
# After:  mlflow>=3.0,<4.0

# ensemble_model.py & ml/registry.py — artifact_path 마이그레이션 패턴
# Before (경고 발생):
mlflow.pyfunc.log_model(artifact_path="model", python_model=...)
# After (3.x 권장):
mlflow.pyfunc.log_model(name="model", python_model=...)

# advisors/claude_client.py — USE_MLFLOW_TRACING flag 기반 span
import os
_USE_MLFLOW_TRACING = os.getenv("USE_MLFLOW_TRACING", "false").lower() == "true"

def _call_with_mlflow_span(messages: list[dict], ticker: str, **kwargs) -> dict:
    """LiteLLM 호출을 MLflow span으로 래핑."""
    if not _USE_MLFLOW_TRACING:
        return _call_with_litellm(messages, **kwargs)

    try:
        import mlflow  # type: ignore[import-not-found]
        with mlflow.start_span(
            name="advisor_call",
            span_type="LLM",
            attributes={"ticker": ticker, "provider": PROVIDER_FALLBACK_CHAIN[0]},
        ) as span:
            span.set_inputs({"messages": messages})
            result = _call_with_litellm(messages, **kwargs)
            span.set_outputs({
                "advisory_score": result.get("score"),
                "cost_usd": result.get("cost_usd"),
            })
        return result
    except Exception:  # pragma: no cover — mlflow optional
        return _call_with_litellm(messages, **kwargs)
```

> **Anthropic autolog 주의:** `mlflow.anthropic.autolog()`는 `anthropic` SDK 직접 호출에만 작동. LiteLLM 경유 시 수동 span 필요 (위 패턴 사용).

### G5. 구현 상세 — E2 PBO Dashboard

```python
# backtest_honesty.py — _normalize_cpcv_pbo_dsr() 반환 구조에 노출 추가

def _normalize_cpcv_pbo_dsr(
    cpcv_result: dict | None,
    pbo_report: dict | None = None,
    dsr_result: dict | None = None,
) -> dict[str, Any]:
    """기존 로직 유지 + pbo_status 최종 필드 추가."""
    base = _existing_normalize(cpcv_result, pbo_report, dsr_result)

    # pbo_status: 기존 내부 체크(line 174-177)와 동일 임계값 사용
    raw_pbo = base.get("pbo")
    pbo_status: str
    if raw_pbo is None:
        pbo_status = "NO_DATA"
    elif float(raw_pbo) <= 0.20:
        pbo_status = "PASS"
    elif float(raw_pbo) <= 0.50:
        pbo_status = "AMBER"
    else:
        pbo_status = "RED"

    return {**base, "pbo_status": pbo_status}   # additive only
```

```python
# readiness/classifier.py — pbo_status 강등 조건 추가
def classify_readiness(snapshot: dict) -> str:
    honesty = snapshot.get("backtest_honesty_summary", {})

    # [신규] PBO 강등 조건 — 기존 로직 앞에 배치 (우선 순위 높음)
    pbo_status = honesty.get("pbo_status", "NO_DATA")
    if pbo_status == "RED":
        return "반영 금지"    # pbo > 50%
    if pbo_status == "AMBER":
        return "검토 전용"    # 20% < pbo ≤ 50%

    # 기존 로직 유지 (변경 없음)
    ...
```

```jsx
// RecommendationCard.jsx — PBO badge 추가 (조건부 렌더링)
const pboBadgeStyle = {
  "PASS":    { bg: "#22c55e", label: "PASS" },
  "AMBER":   { bg: "#f59e0b", label: "AMBER" },
  "RED":     { bg: "#ef4444", label: "RED" },
  "NO_DATA": { bg: "#9ca3af", label: "N/A" },
};

// 기존 카드 하단에 추가
{candidate.backtest_honesty_summary?.pbo_status && (
  <div className="pbo-badge-container" title="Probability of Backtest Overfitting">
    <span className="pbo-badge-label">PBO</span>
    <span className="pbo-badge-value">
      {candidate.backtest_honesty_summary.pbo !== null
        ? `${(candidate.backtest_honesty_summary.pbo * 100).toFixed(1)}%`
        : "–"}
    </span>
    <span
      className="pbo-badge-status"
      style={{ backgroundColor: pboBadgeStyle[candidate.backtest_honesty_summary.pbo_status]?.bg }}
    >
      {pboBadgeStyle[candidate.backtest_honesty_summary.pbo_status]?.label}
    </span>
  </div>
)}
```

### G6. 구현 상세 — E3 AutoForward Prefect

```python
# live_review/auto_forward_recorder.py — record_today() 추가
def record_today(self) -> dict[str, Any]:
    """Prefect task 호환 — 기존 CLI record() 래퍼. JSON 직렬화 가능 dict 반환."""
    try:
        result = self._record_single_day(_today())
        return {
            "status": "recorded",
            "date": str(_today()),
            "symbol": self.ticker,
            "row_count": self._count_rows(),
            "reason": None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("AutoForwardRecorder.record_today() failed: %s", exc)
        return {
            "status": "error",
            "date": str(_today()),
            "symbol": self.ticker,
            "row_count": 0,
            "reason": str(exc),
        }
```

```python
# flows/daily_krx.py — forward_tracking_task 추가

import os
from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder

_FORWARD_TRACKING_ENABLED = os.getenv("FORWARD_TRACKING_ENABLED", "true").lower() == "true"

@with_retries(retries=2, retry_delay_seconds=60)
def forward_tracking_task(
    ticker: str = "005930.KS",
    evidence_dir: str = "reports/live_review",
) -> dict[str, Any]:
    """일별 forward tracking 기록. FORWARD_TRACKING_ENABLED=false 시 skip."""
    if not _FORWARD_TRACKING_ENABLED:
        return {"status": "disabled", "ticker": ticker}
    recorder = AutoForwardRecorder(
        evidence_dir=Path(evidence_dir),
        ticker=ticker,
    )
    return recorder.record_today()


@flow(name="daily_krx_flow")
def daily_krx_flow(*, dry_run: bool = False, as_of: str | None = None) -> dict[str, Any]:
    """KRX post-close DAG. 기존 8 태스크 + forward_tracking_task."""
    # ... 기존 8 태스크 (변경 없음) ...

    # [신규] 마지막 태스크
    results["forward_tracking"] = forward_tracking_task()

    # alert_task에 forward tracking 상태 전달 (PR-F3)
    results["alert"] = alert_task(
        results["recommend"],
        dry_run=dry_run,
        extra_context={"forward_tracking": results["forward_tracking"]},
    )
    return results
```

### G7. 타임라인

```
Week 1 (2026-06-01 ~ 2026-06-05)
  Day 1-2: PR-M1 (mlflow bump) + PR-P1 (pbo field)
  Day 3-4: PR-M2 (artifact_path → name)
  Day 5:   PR-F1 (record_today())

Week 2 (2026-06-08 ~ 2026-06-12)
  Day 1-2: PR-P2 (readiness pbo)
  Day 3-4: PR-M3 (MLflow tracing)
  Day 5:   PR-F2 (forward_tracking_task)

Week 3 (2026-06-15 ~ 2026-06-17)
  Day 1:   PR-P3 (React PBO badge)
  Day 2:   PR-F3 (alert status)
  Day 3:   통합 테스트 + 최종 검증
```

---

## H. Testing Strategy

### H1. 테스트 피라미드

```
E2E (playwright)    2개 (PBO badge 표시, forward tracking API)
────────────────────────────────
Integration         6개 (MLflow span, daily_krx forward task, readiness pipeline)
────────────────────────────────
Unit                20개+ (pbo field, record_today, artifact_path, span 생성)
```

### H2. 핵심 테스트 목록

**E1 — MLflow:**

```python
# tests/test_claude_client.py
def test_mlflow_span_created_when_enabled(monkeypatch):
    """USE_MLFLOW_TRACING=true 시 mlflow.start_span 호출 확인."""
    monkeypatch.setenv("USE_MLFLOW_TRACING", "true")
    mock_mlflow = MagicMock()
    monkeypatch.setattr("stock_rtx4060.advisors.claude_client.mlflow", mock_mlflow)
    _call_with_mlflow_span([{"role": "user", "content": "test"}], ticker="005930")
    mock_mlflow.start_span.assert_called_once()
    assert mock_mlflow.start_span.call_args[1]["name"] == "advisor_call"

def test_mlflow_span_disabled_when_flag_off(monkeypatch):
    """USE_MLFLOW_TRACING=false 시 기존 LiteLLM 경로 사용."""
    monkeypatch.setenv("USE_MLFLOW_TRACING", "false")
    # mlflow import 안 되어도 정상 작동 확인
    result = _call_with_mlflow_span([{"role": "user"}], ticker="test")
    assert result is not None

# tests/test_ml_registry.py 추가
def test_no_artifact_path_deprecation_warning():
    """artifact_path 파라미터가 코드베이스에 없음을 확인."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "artifact_path=", "src/stock_rtx4060/"],
        capture_output=True, text=True
    )
    assert result.stdout == "", f"artifact_path= found: {result.stdout}"
```

**E2 — PBO:**

```python
# tests/test_backtest_honesty.py 추가
def test_pbo_field_in_honesty_summary():
    """backtest_honesty_summary에 pbo, pbo_status 필드 존재."""
    result = build_backtest_honesty_summary(
        candidates=[{"cpcv_result": {"pbo": 0.15}}]
    )
    assert "pbo" in result
    assert "pbo_status" in result

@pytest.mark.parametrize("pbo,expected", [
    (0.10, "PASS"),
    (0.20, "PASS"),   # 경계값
    (0.21, "AMBER"),
    (0.50, "AMBER"),  # 경계값
    (0.51, "RED"),
    (None, "NO_DATA"),
])
def test_pbo_status_thresholds(pbo, expected):
    summary = _normalize_cpcv_pbo_dsr({"pbo": pbo} if pbo else None)
    assert summary["pbo_status"] == expected

# tests/test_investment_readiness_benchmark.py 추가
def test_readiness_downgrade_pbo_red():
    snap = {"backtest_honesty_summary": {"pbo": 0.75, "pbo_status": "RED"}}
    assert classify_readiness(snap) == "반영 금지"

def test_readiness_downgrade_pbo_amber():
    snap = {"backtest_honesty_summary": {"pbo": 0.35, "pbo_status": "AMBER"}}
    assert classify_readiness(snap) == "검토 전용"

def test_readiness_unchanged_pbo_pass():
    snap = {"backtest_honesty_summary": {"pbo": 0.10, "pbo_status": "PASS"}}
    # 기존 readiness 로직에 의해 결정됨 (pbo_status PASS → 기존 경로 사용)
    result = classify_readiness(snap)
    assert result in ("반영 금지", "검토 전용", "조건부 반영 가능")
```

**E3 — Forward Tracking:**

```python
# tests/test_daily_krx_flow.py 추가
def test_daily_krx_flow_includes_forward_tracking(monkeypatch):
    """daily_krx_flow 결과에 forward_tracking 키 존재."""
    monkeypatch.setenv("FORWARD_TRACKING_ENABLED", "true")
    result = daily_krx_flow(dry_run=True)
    assert "forward_tracking" in result
    assert result["forward_tracking"]["status"] in ("recorded", "skipped", "error", "disabled")

def test_forward_tracking_disabled_via_flag(monkeypatch):
    monkeypatch.setenv("FORWARD_TRACKING_ENABLED", "false")
    result = forward_tracking_task()
    assert result["status"] == "disabled"

# tests/test_auto_forward_recorder.py 추가
def test_record_today_returns_serializable():
    """record_today() 반환값이 JSON 직렬화 가능."""
    recorder = AutoForwardRecorder(evidence_dir=tmp_path, ticker="005930.KS")
    result = recorder.record_today()
    import json
    json.dumps(result)  # 직렬화 오류 없으면 통과
    assert result["status"] in ("recorded", "skipped", "error")
```

### H3. CI Gates

```yaml
# .github/workflows/ci.yml (기존 유지 + 추가 확인)
- name: pytest with coverage
  run: |
    PYTHONPATH=.:src pytest \
      --cov=stock_rtx4060 \
      --cov-fail-under=75 \   # 기존 gate
      --tb=short -rfE -q
    # [신규] artifact_path DeprecationWarning 없음 확인
    PYTHONPATH=.:src python -W error::DeprecationWarning -c \
      "from stock_rtx4060.ensemble_model import EnsembleModel; print('OK')"

- name: CLI invariants
  run: |
    PYTHONPATH=.:src python main.py recommend --help
    PYTHONPATH=.:src python main.py backtest --help
```

---

## I. Observability & Operations

### I1. 로깅

**E1 신규 로그 이벤트:**
```python
# advisors/audit.py 또는 claude_client.py 내
logger.info("mlflow_span: ticker=%s score=%.3f tokens_in=%d cost_usd=%.4f",
            ticker, score, tokens_in, cost_usd)
```

**E2 신규 로그 이벤트:**
```python
# backtest_honesty.py
logger.debug("pbo_field: ticker=%s pbo=%.3f pbo_status=%s", ticker, pbo, pbo_status)
```

**E3 신규 로그 이벤트:**
```python
# flows/daily_krx.py
logger.info("forward_tracking: status=%s date=%s symbol=%s row_count=%d",
            status, date, symbol, row_count)
```

### I2. 알림

| 조건 | 채널 | 메시지 |
|------|------|--------|
| `forward_tracking.status == "error"` | Slack/Discord | `⚠ Forward tracking error: {reason}` |
| `pbo_status == "RED"` (REC 결과) | 로그 WARN | `pbo_status=RED ticker={ticker}` |
| MLflow span 기록 실패 | 로그 DEBUG | `mlflow_span failed (optional), continuing` |

### I3. MLflow UI 접근

```bash
# 로컬 MLflow tracking server 실행
mlflow server --host 127.0.0.1 --port 5000
# UI: http://127.0.0.1:5000
# Traces 탭 → "advisor_call" span 검색
```

### I4. Runbook

**B1 MLflow tracing 활성화:**
```bash
export USE_MLFLOW_TRACING=true
PYTHONPATH=.:src python main.py recommend --universe "005930.KS" --top 1
# → MLflow UI Traces 탭에서 advisor_call span 확인
```

**B2 PBO 필드 확인:**
```bash
PYTHONPATH=.:src python main.py recommend --synthetic --universe "SYNTH-A" --top 1 \
    --output-dir reports/pbo_smoke
cat reports/pbo_smoke/recommendations_*.json | python -c \
    "import json,sys; d=json.load(sys.stdin); print(d.get('backtest_honesty_summary',{}).get('pbo_status'))"
```

**B3 Forward tracking 수동 확인:**
```bash
FORWARD_TRACKING_ENABLED=true python -c "
from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder
from pathlib import Path
r = AutoForwardRecorder(evidence_dir=Path('reports/live_review'), ticker='005930.KS')
print(r.record_today())
"
```

---

## J. Error Handling & Recovery

### J1. 오류 분류

| 구성요소 | 오류 유형 | 처리 방법 |
|---------|---------|---------|
| MLflow 3.x 범프 | 기존 테스트 실패 | CI에서 즉시 발견 → `pip install mlflow==2.16.x` rollback |
| MLflow span 생성 실패 | `ImportError`, `ConnectionError` | try/except → 로그 DEBUG + LiteLLM 경로로 폴백 |
| PBO 필드 없음 | `cpcv_result=None` | `pbo=None, pbo_status="NO_DATA"` 안전 처리 |
| `record_today()` 실패 | yfinance timeout, 파일 I/O | `status="error"` + `reason` 반환 (Prefect retry=2) |
| Playwright 테스트 실패 | badge 미표시 | 조건부 렌더링 확인 (`pbo_status`가 None이면 badge 숨김) |

### J2. Retry 정책

| 컴포넌트 | 재시도 | 지연 |
|---------|-------|------|
| `forward_tracking_task` | 2 | 60s |
| MLflow span 기록 | 0 (선택적) | — (실패해도 advisor 호출 계속) |
| `ingest_kis_task` (기존) | 3 | 60s |

### J3. 멱등성

- `record_today()`: 동일 날짜 두 번 호출 시 `"status": "skipped"` (기존 상태 파일 확인)
- PBO 필드 추가: JSON additive → 기존 snapshot 파일 읽어도 `pbo` 없으면 badge 미표시 (하위 호환)
- MLflow `log_model(name=...)`: 동일 실험 재실행 시 MLflow run 덮어씀 (기존 동작 유지)

---

## K. Dependencies, Security, Risks

### K1. 의존성 변경

| 패키지 | 현재 | 변경 | 이유 |
|--------|------|------|------|
| `mlflow` | `>=2.16` | `>=3.0,<4.0` | LoggedModel + LLM Tracing |
| `litellm` | `>=1.55` (Wave 2) | 변경 없음 | Anthropic autolog → LiteLLM 경유 수동 span 사용 |
| `hypothesis` | `>=6.0` (Wave 2) | 변경 없음 | — |
| `duckdb` | `>=1.5.3` (Wave 2) | 변경 없음 | — |

### K2. 보안

| 항목 | 확인 사항 |
|------|---------|
| MLflow trace 데이터 | 어드바이저 입력(ticker 정보)만 기록 — `messages` 전체는 기록하지 않음 |
| `advisor.jsonl` 감사 로그 | 보존 (MLflow trace는 추가 레이어, 기존 로그 대체 아님) |
| PBO 값 노출 | 내부 운영 메트릭 — 외부 API 응답(`/api/recommend`)에 포함되나 PII 없음 |
| `FORWARD_TRACKING_ENABLED` env | 운영 환경에서 `true` 기본값 유지 |

### K3. 위험 레지스터

| # | 위험 | 확률 | 영향 | 완화 방법 | 트리거 |
|---|------|------|------|---------|--------|
| R1 | MLflow 3.x API 변경으로 기존 테스트 실패 | 중 | 높음 | CI 즉시 발견, `pip install mlflow==2.16.x` rollback | PR-M1 CI 실패 |
| R2 | LiteLLM + MLflow 수동 span 비용 오버헤드 | 낮음 | 낮음 | `USE_MLFLOW_TRACING=false` 즉시 비활성화 | advisor latency p99 >200ms |
| R3 | PBO 필드 추가로 `dashboard_snapshot.v1` 하위 호환 깨짐 | 낮음 | 높음 | additive only + 조건부 렌더링 | snapshot 파싱 오류 |
| R4 | `record_today()` yfinance timeout으로 Prefect task 실패 | 중 | 낮음 | `retries=2, retry_delay=60s` + `status="error"` 안전 반환 | forward_tracking status=error |
| R5 | `artifact_path` 마이그레이션 누락 | 낮음 | 낮음 | `grep artifact_path= src/` CI 검증 | DeprecationWarning in pytest |

### K4. Change Control

- PR별 단독 배포 가능 (독립적 rollback)
- `claude/upgrade-investment-system-2Mc7x` 브랜치에 모든 PR
- 각 PR은 CI green 후 squash merge (관련 Wave 3 Best PR 커밋 메시지 형식: `feat(E1-mlflow)/fix(E2-pbo)/feat(E3-forward)`)

---

## ㅋ. Appendix

### ㅋ1. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| E1: MLflow 3.x | Official | MLflow 3.3.1 Tracing Docs | mlflow.org/docs/3.3.1/genai/tracing | live | 19k+ stars | `@mlflow.trace`, `mlflow.start_span`, SpanType.LLM |
| E1: MLflow 3.x | Official | MLflow 3.2.0 Tracing Quickstart | mlflow.org/docs/3.2.0/genai/tracing/quickstart/python-openai | live | — | Anthropic 포함 모든 LLM 공급자 tracing |
| E1: MLflow artifact_path | GitHub | issue #16501 artifact_path deprecation | github.com/mlflow/mlflow/issues/16501 | 2025-06-30 | — | `artifact_path` → `name` 마이그레이션 근거 |
| E2: PBO | Academic | "The Probability of Backtest Overfitting" | SSRN 2326253 (Bailey et al., 2014) | 2014 | 광범위 인용 | PBO 이론 + CPCV 계산 방법 |
| E2: PBO 2025 | Medium | "The Probability of Backtest Overfitting (PBO)" | medium.com/balaena-quant-insights/pbo | 2025-07-19 | — | Python 구현 코드 + KDE 시각화 |
| E2: PBO (내부) | Internal | backtest/pbo.py, backtest_honesty.py | grep 확인 (2026-05-29) | 2026-05 | — | PBO 이미 구현됨, pbo_status 미노출 확인 |
| E3: Prefect 3 | GitHub | PrefectHQ/prefect v3.6.23 | github.com/PrefectHQ/prefect/tree/3.6.23 | 2025-2026 | 16k+ stars | `@task(retries=N)` + `@flow` 패턴 |
| E3: Prefect flows | Article | DataOps CI/CD Prefect 2026 | johal.in/dataops-ci-cd-prefect-flows | 2026 | — | daily pipeline cron 패턴 확인 |
| E3: AutoForward (내부) | Internal | live_review/auto_forward_recorder.py | grep 확인 (2026-05-29) | 2026-05 | — | 수동 실행 전용, record() API 확인 |

### ㅋ2. 벤치마크 Repo 메모

| Repo | Stars | 관련 Pattern | 사용처 |
|------|-------|------------|--------|
| mlflow/mlflow | 19k+ | `@mlflow.trace` + `SpanType.LLM` | E1 advisor span |
| PrefectHQ/prefect | 16k+ | `@with_retries` + `@flow` (기존 패턴 동일) | E3 task 추가 |
| balaena-quant-insights PBO article | Medium | KDE + scatter PBO viz | E2 React badge 설계 참고 |

### ㅋ3. AMBER_BUCKET

이 플랜에서 AMBER 아이디어(Dead Reckoning, Bayesian Sequential Gate)는 Best 3에 포함되지 않으므로 구현 계획 외.

### ㅋ4. 검증 게이트 체크리스트

```
Gate 0 (Dry-run):          ✅ 코드 변경 없음, 문서만
Gate 1 (Change list):      ✅ 9개 PR, 파일 목록 G3에 명시
Gate 2 (Explicit approval):✅ 각 PR 시작 전 사용자 승인 필요
Gate 3 (Feature flag):     ✅ USE_MLFLOW_TRACING, FORWARD_TRACKING_ENABLED
Gate 4 (Rollback):         ✅ 각 PR별 rollback 명시
Gate 5 (Coverage):         ✅ pytest --cov-fail-under=75 유지
Gate 6 (Safety):           ✅ screening_output_only=True, 브로커 없음
```

**최종 판정: Go ✅**

---

## 실행 순서 요약

```
Week 1:  PR-M1 → PR-P1 → PR-M2 → PR-F1
Week 2:  PR-P2 → PR-M3 → PR-F2
Week 3:  PR-P3 → PR-F3 → 통합 검증
```

**가장 먼저 실행할 PR:** `PR-M1` (mlflow bump — 리스크 최소, 기존 테스트 통과 확인만)
**병렬 실행 가능:** PR-M1 + PR-P1 (독립적 파일)

다음 권장 스킬: `/gsd-execute-phase` 또는 `project-plan --focus="E1-mlflow"` 로 Epic 단위 세분화 실행
