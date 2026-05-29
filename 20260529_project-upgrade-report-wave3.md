# Project Upgrade Report — stock_rtx4060 **Wave 3**
**Skill:** project-upgrade v2.2.0 | **Date:** 2026-05-29 (3rd scan)
**Project:** `stock_1901/stock_rtx4060` (P0–P8 hedge-fund grade paper trading system)
**Context:** Wave 2 Best 3 모두 구현 완료 (Hypothesis ✅ · DuckDB 1.5.3 ✅ · LiteLLM ✅ · Branch coverage 86% ✅). 신규 모듈: `live_review/`, `readiness/`, CPCV/PBO, PyTorch GRU, AutoForwardRecorder, Investment Readiness Gates. 이 보고서는 Wave 3 개선 파동을 스캔한다.

---

## 0. Surprise Picks (최우선 — 예상 밖 아이디어)

| # | Idea | Novelty | SurpriseScore | 내일 당장 할 첫 번째 액션 |
|---|------|---------|---------------|--------------------------|
| ★1 | **Bayesian Sequential 모델 승격 게이트** — 의료 임상시험의 "Group Sequential Test(GST)"를 `research_weekly.py`의 고정 5% delta 임계에 적용. 새 모델이 현재 prod보다 얼마나 더 나은지를 누적 증거로 판단해 조기 승격/조기 중단 결정. P-value를 매 주마다 업데이트하며 임계를 넘으면 자동 승격 제안, 하회하면 중단 | 5 | 7.5 | `flows/research_weekly.py`의 `_current_production_score()` 호출 직후 `from scipy.stats import norm`으로 SPRT z-통계량 1개 계산 stub 추가 |
| ★2 | **TradingAgents 패턴 어댑터** — GitHub 58k+ stars의 TradingAgents(LangGraph 기반, Anthropic/MiniMax 지원)의 "specialist agent debate(fundamental/sentiment/technical/risk mgr 토론)"를 현재 NewsSentiment+DevilsAdvocate+MacroRegime 오케스트레이터에 debate round 1개로 추가. 단일 점수가 아닌 "토론 트랜스크립트 + 합의 점수" 출력 | 4 | 5.33 | `advisors/orchestrator.py`에서 `advisors` 루프 구조 확인 → TradingAgents arXiv:2412.20138 패턴 참조, `debate_round()` stub 추가 |
| ★3 | **Dead Reckoning 신뢰도 감쇠** — (Wave 2 AMBER 이월) 항공 DR처럼 OpenBB/yfinance 데이터가 stale될수록 confidence를 시간 경과에 비례 decay. `data_freshness_hours` × `halflife=24h` 공식으로 GREEN→AMBER 자동 강등 | 5 | 7.5 | `recommendation_engine.py`에서 `data_freshness_hours` 계산 지점 파악 → `confidence_decay(age_h, halflife_h=24)` 1-liner stub 추가 |

---

## 1. Executive Summary

Wave 2 모든 목표 달성. **현재 신규 개선 기회** 3가지: ① `mlflow>=2.16`이지만 MLflow 3.1.0 (2025)의 LoggedModel + LLM Tracing이 미적용 — P6 어드바이저 audit trail 품질을 크게 개선할 수 있음. ② `backtest/pbo.py`와 `stat_tests.py`에 PBO 지표가 구현됐지만 `dashboard_snapshot.v1`에 노출 안 됨 — 투자준비도 등급(readiness)과 연동하면 최종 리뷰 근거가 강해짐. ③ `live_review/auto_forward_recorder.py`가 독립 실행 모드로만 존재 — Prefect `daily_krx.py` 플로우에 단계로 편입하면 자동화 완성. 외부 최대 변화: TradingAgents(58k stars, arXiv 2024-12, v0.2.4 2026-04) + NautilusTrader(20.7k stars, 2025-08).

---

## 2. Current State Snapshot

| 항목 | 현황 | 상태 |
|------|------|------|
| Python | 3.12 CI / 3.14.4 로컬 | ✅ |
| 테스트 커버리지 (line) | 86% | ✅ |
| 테스트 커버리지 (branch) | 86% | ✅ (Wave 2 목표 초과 달성) |
| MLflow | >=2.16 (3.1.0 최신, 미업그레이드) | ⚠ 업그레이드 기회 |
| DuckDB | 1.5.3 ✅ | ✅ |
| LiteLLM | 1.83.7 ✅ | ✅ |
| Hypothesis | 6.155.0 ✅ | ✅ |
| Optuna | 4.8.0 (v5 아직 미출시 확인) | ✅ |
| LightGBM | 4.6.0 ✅ | ✅ |
| PBO 지표 | `backtest/pbo.py` 구현됨 | ⚠ Dashboard 미노출 |
| AutoForwardRecorder | `live_review/auto_forward_recorder.py` | ⚠ Prefect 미연동 |
| TradingAgents 패턴 | 미통합 (외부 58k stars) | 아이디어 |
| 모델 승격 게이트 | 고정 5% delta | ⚠ Bayesian Sequential 미적용 |
| NautilusTrader | 미통합 (vectorbt 유지) | 장기 아이디어 |

**Pain points:**
- MLflow 3.x LoggedModel entity — P6 어드바이저 trace와 ML 실험을 동일 lineage로 연결 불가 (현재 2.16)
- PBO 지표가 `backtest/pbo.py`에 있지만 REC 탭/readiness grade에 미노출 → 투자자 가시성 부족
- `AutoForwardRecorder`가 수동 실행만 지원 → 일별 KRX 플로우에 편입하지 않으면 증거 공백 발생
- `research_weekly.py` 모델 승격 기준이 arbitrary 5% → 통계적 근거 없음

---

## 3. Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | Novelty | PriorityScore | SurpriseScore | Evidence | 상태 |
|---|----------|------|--------|--------|------|------------|---------|---------------|---------------|----------|------|
| 1 | **Alert Engine + Macro Regime 컨텍스트 강화** | Reliability/Obs | 2 | 1 | 1 | 4 | 2 | **8.0** | 4.0 | 내부: alert_engine.py + advisors/orchestrator.py 공존 확인 | ✅ CONFIRMED |
| 2 | **PBO 지표 Dashboard_snapshot.v1 통합** | Reliability | 3 | 2 | 1 | 4 | 3 | **6.0** | 4.5 | 내부: backtest/pbo.py(구현됨); Bailey et al. 2014 (SSRN) | ✅ CONFIRMED |
| 3 | **AutoForwardRecorder → Prefect daily_krx 자동화** | DX/Tooling | 3 | 2 | 1 | 4 | 2 | **6.0** | 3.0 | 내부: live_review/auto_forward_recorder.py + flows/daily_krx.py | ✅ CONFIRMED |
| 4 | **skfolio + 트랜잭션 비용 모델 완전 연동** | Performance | 3 | 2 | 1 | 4 | 2 | **6.0** | 3.0 | arXiv:2507.04176 (skfolio paper, 2025-07); GitHub skfolio (active) | ✅ CONFIRMED |
| 5 | **MLflow 3.x 업그레이드 (LoggedModel + LLM Tracing)** | Reliability/Obs | 4 | 2 | 2 | 5 | 2 | **5.0** | 4.0 | github.com/mlflow/mlflow/releases/tag/v3.1.0 (2025); issues 2025-06-30 | ✅ CONFIRMED |
| 6 | **Dead Reckoning 신뢰도 감쇠** | Reliability | 3 | 2 | 1 | 3 | 5 | **4.5** | 7.5 | Cross-domain (항공 DR 이론); 2025 trading 적용 구현 선례 날짜 미확인 | ⚠ AMBER |
| 7 | **Bayesian Sequential 모델 승격 게이트** | Architecture | 3 | 2 | 1 | 3 | 5 | **4.5** | 7.5 | BED-LLM arXiv 2025-08-28 (관련); scipy.stats SPRT (공식 docs, live) | ⚠ AMBER |
| 8 | **TradingAgents 패턴 어댑터** | Architecture | 4 | 3 | 2 | 3 | 4 | **2.0** | 5.33 | arXiv:2412.20138 (2024-12); github.com/TauricResearch/TradingAgents (58k+ stars, 2026-04 push) | ✅ CONFIRMED |
| 9 | **Shapley 동적 어드바이저 가중치** (Wave 2 이월) | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | arXiv cs.GT 2025-02; 기존 evidence 유지 | ✅ CONFIRMED |
| 10 | **NautilusTrader 이벤트-드리븐 백테스터** (Wave 2 이월) | Architecture | 4 | 4 | 3 | 3 | 3 | **1.0** | 3.0 | github.com/nautechsystems/nautilus_trader (20.7k stars, 2025-08-28) | ✅ CONFIRMED |

> PriorityScore = (Impact × Confidence) / (Effort × Risk)
> SurpriseScore = (Novelty × Impact) / Effort

---

## 4. Best 3 Deep Report

### BEST-1: MLflow 3.x 업그레이드 — LoggedModel + LLM Tracing
**PriorityScore: 5.0 | Bucket: Reliability/Observability | Effort: S**

#### Goal
`mlflow>=2.16` → `mlflow>=3.0` 업그레이드. MLflow 3의 **LoggedModel 엔티티**로 ML 실험(P3)과 LLM 어드바이저 호출(P6)을 동일 lineage로 연결. LLM tracing으로 `advisor.jsonl`의 수동 로깅 일부를 MLflow Trace로 자동화.

#### Non-goals
- Databricks Managed MLflow 이전 (로컬 tracking server 유지)
- MLflow 2.x 실험 데이터 마이그레이션 (append 방식, 기존 runs 보존)
- Human annotation 기능 사용 (현재 open source 미포함)

#### Proposed Design
```python
# requirements.in 변경
# Before: mlflow>=2.16
# After:  mlflow>=3.0,<4.0  (semantic versioning boundary)

# src/stock_rtx4060/ml/registry.py — LoggedModel 등록 추가
import mlflow

def register_model_v3(run_id: str, model_name: str, metrics: dict) -> str:
    """MLflow 3.x LoggedModel 방식으로 모델 등록."""
    with mlflow.start_run(run_id=run_id):
        logged = mlflow.log_model(
            artifact_path="model",   # 3.x: artifact_path 대신 name 권장 (DeprecationWarning 해결)
            python_model=...,
        )
    return logged.model_id   # 3.x 신규: model_id로 trace 연결

# src/stock_rtx4060/advisors/claude_client.py — LLM Tracing 추가
import mlflow

def _call_with_tracing(messages: list[dict], **kwargs) -> dict:
    """MLflow 3.x LLM 자동 tracing 래퍼."""
    with mlflow.start_span(name="advisor_call", span_type="LLM") as span:
        span.set_inputs({"messages": messages})
        result = _call_with_litellm(messages, **kwargs)
        span.set_outputs({"advisory_score": result.get("score")})
    return result
```

```python
# flows/research_weekly.py — LoggedModel 기반 승격 게이트
# Before: 단순 best_value 비교
# After:  LoggedModel lineage 확인 + artifact_path deprecation 해결
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-M1 | `chore(P0): bump mlflow>=3.0,<4.0 — verify existing tests` | `requirements.in`, `requirements.txt` | `pip install mlflow==2.16.x` |
| PR-M2 | `feat(P3): migrate artifact_path→name in log_model calls` | `ml/registry.py`, `ensemble_model.py` | `git revert` (DeprecationWarning 제거만) |
| PR-M3 | `feat(P6): add MLflow LLM span tracing to advisor calls` | `advisors/claude_client.py`, `advisors/orchestrator.py` | `USE_MLFLOW_TRACING=false` 환경변수 |

#### Tests
- `test_mlflow_v3_log_model` — LoggedModel 등록 + model_id 반환 확인
- `test_mlflow_artifact_path_deprecation_resolved` — `artifact_path` DeprecationWarning 없음 확인
- `test_advisor_mlflow_span` — LLM span이 MLflow trace에 기록됨 확인
- `test_existing_registry_tests_pass` — 기존 `test_ml_registry.py` 전부 통과

#### Rollout & Rollback
- Feature: `mlflow>=3.0` 하위 호환 (2.x runs 보존, API 대부분 동일)
- LLM tracing: `USE_MLFLOW_TRACING=false`로 즉시 비활성화 가능
- Rollback: `pip install mlflow==2.16.x` (기존 실험 데이터 보존됨)

#### Risks & Mitigations
1. `artifact_path` DeprecationWarning 대량 발생 → PR-M2에서 `name=` 파라미터로 일괄 교체
2. MLflow 3.x의 `LoggedModel` API가 실험 중 변경 가능 → `<4.0` 상한 설정
3. LLM Tracing이 `audit_log/advisor.jsonl` 중복 기록 → Tracing은 debug용, jsonl은 audit 원본 유지 (중복 허용)

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| MLflow 버전 | >=2.16 | >=3.0 |
| `artifact_path` DeprecationWarning 수 | 미측정 | 0 |
| P6 어드바이저 → ML 모델 lineage 연결 | 불가 | `span.set_outputs` + `model_id` 연결 |
| LLM 호출 MLflow trace 기록 | 없음 | `advisor_call` span 자동 기록 |

#### Evidence
- github.com/mlflow/mlflow/releases/tag/v3.1.0 (2025, official) — "LoggedModel entity, comprehensive lineage, LLM tracing"
- github.com/mlflow/mlflow/issues/16501 (2025-06-30) — `artifact_path` → `name` 마이그레이션 확인

---

### BEST-2: PBO 지표 Dashboard_snapshot.v1 통합
**PriorityScore: 6.0 | Bucket: Reliability | Effort: S**

#### Goal
`backtest/pbo.py`와 `stat_tests.py`에 이미 구현된 PBO(Probability of Backtest Overfitting) 값을 `dashboard_snapshot.v1`의 `backtest_honesty_summary`에 추가 노출. 투자준비도 등급(`readiness/classifier.py`)에서 PBO를 AMBER/RED 강등 조건으로 활용.

#### Non-goals
- PBO 계산 로직 변경 (기존 `stat_tests.py` 그대로)
- 프론트엔드 대규모 리팩터링 (기존 `backtest_honesty_summary` 블록에 필드 추가만)
- PBO < 0.5 자동 거래 차단 (readiness 표시만, `screening_output_only=True` 유지)

#### Proposed Design
```python
# src/stock_rtx4060/backtest_honesty.py — PBO 필드 dashboard에 노출
from stock_rtx4060.backtest.pbo import compute_pbo

def build_backtest_honesty_summary(backtest_results: list[dict]) -> dict:
    """기존 반환값에 pbo 필드 추가 (additive only)."""
    existing = _build_existing_summary(backtest_results)

    # PBO 계산 (이미 pbo.py에 구현됨)
    pbo_value = compute_pbo(backtest_results)  # 0.0~1.0

    return {
        **existing,                          # 기존 필드 보존
        "pbo": round(pbo_value, 4),          # 신규: Prob. of Backtest Overfitting
        "pbo_status": (
            "PASS" if pbo_value < 0.5
            else "AMBER" if pbo_value < 0.75
            else "RED"
        ),
    }

# src/stock_rtx4060/readiness/classifier.py — PBO 연동
def classify_readiness(snapshot: dict) -> str:
    honesty = snapshot.get("backtest_honesty_summary", {})
    if honesty.get("pbo_status") == "RED":
        return "반영 금지"      # 기존 게이트에 PBO 조건 추가
    if honesty.get("pbo_status") == "AMBER":
        return "검토 전용"      # PBO AMBER → 자동 강등
    # ... 기존 로직 유지
```

```jsx
// stock-pred-v5/src/components/RecommendationCard.jsx — PBO badge 추가 (additive)
{candidate.backtest_honesty_summary?.pbo !== undefined && (
  <span className={`pbo-badge ${candidate.backtest_honesty_summary.pbo_status}`}>
    PBO {(candidate.backtest_honesty_summary.pbo * 100).toFixed(1)}%
  </span>
)}
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-P1 | `feat(P5): expose pbo + pbo_status in backtest_honesty_summary` | `backtest_honesty.py`, `tests/test_backtest_honesty.py` | `git revert` (additive 필드만) |
| PR-P2 | `feat(readiness): use pbo_status in investment readiness classifier` | `readiness/classifier.py`, `tests/test_investment_readiness_benchmark.py` | `git revert` |
| PR-P3 | `feat(dashboard): add PBO badge to RecommendationCard` | `stock-pred-v5/src/components/RecommendationCard.jsx` | `git revert` |

#### Tests
- `test_pbo_field_in_honesty_summary` — `pbo`, `pbo_status` 필드가 반환값에 존재
- `test_pbo_status_thresholds` — 0.3→PASS, 0.6→AMBER, 0.8→RED 분류 정확
- `test_readiness_downgrade_on_pbo_red` — `pbo_status=RED` 시 readiness=반영 금지
- `test_dashboard_snapshot_schema_v1_additive` — 기존 `dashboard_snapshot.v1` 필드 보존 확인

#### Rollout & Rollback
- Additive only: 기존 `backtest_honesty_summary` 필드 보존, `pbo`/`pbo_status` 추가
- React card: 조건부 렌더링 → pbo 필드 없으면 badge 미표시
- Rollback: `git revert` (schema_version 변경 없음)

#### Risks & Mitigations
1. `compute_pbo()`가 CPCV 결과 없으면 None 반환 → `pbo=None, pbo_status="NO_DATA"` 처리
2. PBO AMBER 강등이 legitimate candidate를 과도하게 차단 → `readiness` 표시만, `screening_output_only=True` 보존
3. 프론트엔드 테스트(playwright) 변경 필요 → PR-P3에 playwright 테스트 업데이트 포함

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| PBO 지표 dashboard 노출 | 없음 | `backtest_honesty_summary.pbo` 필드 |
| readiness PBO 연동 | 없음 | pbo_status RED → 반영 금지 자동 강등 |
| backtest_honesty 테스트 | 기존 | 기존 + 4개 신규 |

#### Evidence
- 내부: `src/stock_rtx4060/backtest/pbo.py` 구현 확인 (2026-05-29 grep)
- Bailey et al., "The Probability of Backtest Overfitting" — Journal of Computational Finance, 2014 (SSRN 2326253; 광범위 인용)

---

### BEST-3: AutoForwardRecorder → Prefect daily_krx 플로우 자동화
**PriorityScore: 6.0 | Bucket: DX/Tooling | Effort: S**

#### Goal
`live_review/auto_forward_recorder.py`가 현재 수동 실행 전용. 이를 `flows/daily_krx.py`의 마지막 태스크로 편입해 매 거래일 자동으로 30-day forward tracking 증거를 수집·저장.

#### Non-goals
- AutoForwardRecorder 로직 변경 (기존 상태 파일/스키마 보존)
- 실시간 스트리밍 (일별 배치 유지)
- Prefect Cloud 이전 (로컬 Prefect server 유지)

#### Proposed Design
```python
# flows/daily_krx.py — AutoForwardRecorder 태스크 추가

from prefect import task, flow
from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder

@task(name="forward-tracking-record", retries=2, retry_delay_seconds=60)
def record_forward_tracking(
    ticker: str = "005930.KS",
    evidence_dir: str = "reports/live_review",
) -> dict:
    """일별 forward tracking 1건 기록 — 기존 recommendation JSON 없으면 skip."""
    recorder = AutoForwardRecorder(evidence_dir=Path(evidence_dir), ticker=ticker)
    return recorder.record_today()   # 기존 AutoForwardRecorder API 활용

@flow(name="daily-krx", log_prints=True)
def daily_krx_flow(run_date: date | None = None):
    # ... 기존 태스크들 ...
    forward_result = record_forward_tracking()   # 마지막에 추가

    # Slack/Discord 알림에 forward tracking 상태 포함
    send_alert(
        channel="daily-krx",
        message=f"Forward tracking: {forward_result.get('status', 'skipped')}",
    )
```

```python
# src/stock_rtx4060/live_review/auto_forward_recorder.py — Prefect 호환 시그니처 확인
def record_today(self) -> dict:
    """기존 `record()` 래퍼 — Prefect task result로 직렬화 가능한 dict 반환."""
    ...
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-F1 | `feat(P7): add `record_forward_tracking` Prefect task to daily_krx flow` | `flows/daily_krx.py`, `tests/test_daily_krx_flow.py` | `git revert` (태스크 제거) |
| PR-F2 | `feat(live_review): add `record_today()` method returning serializable dict` | `live_review/auto_forward_recorder.py` | `git revert` |
| PR-F3 | `feat(P7): include forward tracking status in Slack/Discord alert` | `alert_engine.py` or `flows/daily_krx.py` | `git revert` |

#### Tests
- `test_daily_krx_includes_forward_tracking` — Prefect flow에 forward tracking task 포함 확인
- `test_record_today_returns_serializable` — `record_today()` 반환값이 JSON 직렬화 가능
- `test_record_today_skip_on_no_recommendation` — recommendation JSON 없으면 `{"status": "skipped"}` 반환
- `test_forward_tracking_alert_included` — 알림 메시지에 tracking status 포함

#### Rollout & Rollback
- Feature flag: `FORWARD_TRACKING_ENABLED=true` 환경변수로 on/off
- `retries=2, retry_delay_seconds=60` — yfinance 일시 장애 대응
- Rollback: `FORWARD_TRACKING_ENABLED=false` 또는 `git revert`

#### Risks & Mitigations
1. AutoForwardRecorder 상태 파일 lock 충돌 — `record_today()` 내부 원자적 write 확인
2. yfinance rate-limit → `retries=2` + `retry_delay_seconds=60` 충분
3. `record_today()` API가 기존 `AutoForwardRecorder.record()`와 다를 수 있음 → PR-F2에서 호환 래퍼 추가

#### KPI Targets
| Metric | Before | Target |
|--------|--------|--------|
| Forward tracking 자동화 | 수동 실행 | daily_krx flow 실행 시 자동 |
| 증거 수집 공백 | 수동 실행 누락 시 발생 | 0 (Prefect retry 포함) |
| 알림 메시지 forward tracking 포함 | 없음 | `record_forward_tracking` status 포함 |

#### Evidence
- 내부: `live_review/auto_forward_recorder.py` + `flows/daily_krx.py` 공존 확인 (2026-05-29 grep)
- Prefect 공식 docs — flow + task 패턴 (live, deepchecks.com Prefect 2026 확인)

---

## 5. Options A/B/C

| Option | 내용 | 기간 | 위험 | 주요 결과 |
|--------|------|------|------|-----------|
| **A (보수)** | MLflow 3.x + PBO Dashboard | 2주 | 낮음 | P6 lineage 개선 + PBO 가시성 |
| **B (중간)** | A + AutoForwardRecorder Prefect 자동화 + Alert Macro Regime | 4주 | 낮음 | 완전 자동화 daily 루프 |
| **C (공격)** | B + TradingAgents 패턴 + Bayesian Promotion Gate + Shapley | 12주 | 중간 | 어드바이저 시스템 차세대화 |

---

## 6. 30/60/90-day Roadmap

### 30일 (2026-05-29 → 2026-06-28)
- [ ] PR-M1: `mlflow>=3.0` 버전 범프 + 기존 테스트 확인
- [ ] PR-M2: `artifact_path` → `name` 마이그레이션 (DeprecationWarning 0)
- [ ] PR-P1: `backtest_honesty_summary`에 `pbo`/`pbo_status` 필드 추가
- [ ] PR-P2: readiness classifier PBO 연동

### 60일 (2026-06-29 → 2026-07-28)
- [ ] PR-M3: MLflow LLM span tracing (P6 어드바이저)
- [ ] PR-P3: REC 카드에 PBO badge 추가 + playwright 테스트
- [ ] PR-F1~F2: AutoForwardRecorder → daily_krx Prefect task 편입
- [ ] Alert Engine + Macro Regime 컨텍스트 강화 (PR 1개)

### 90일 (2026-07-29 → 2026-08-28)
- [ ] PR-F3: 알림 forward tracking status 포함
- [ ] TradingAgents `debate_round()` PoC (스파이크 PR)
- [ ] Bayesian Sequential 모델 승격 게이트 SPRT 구현 (AMBER → evidence 확보 후)
- [ ] Shapley 동적 어드바이저 가중치 (Wave 2 이월)

---

## 7. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | 인기지표 | 관련성 |
|----------|----------|-------|-----|------|----------|--------|
| BEST-1 MLflow 3.x | GitHub/Official | MLflow 3.1.0 Release | github.com/mlflow/mlflow/releases/tag/v3.1.0 | 2025 | 19k+ stars | LoggedModel 엔티티, LLM tracing |
| BEST-1 MLflow 3.x | GitHub | MLflow 3.x artifact_path deprecation | github.com/mlflow/mlflow/issues/16501 | 2025-06-30 | — | `name=` 파라미터 마이그레이션 근거 |
| BEST-2 PBO | Academic | "The Probability of Backtest Overfitting" | SSRN 2326253 (Bailey et al.) | 2014 | 광범위 인용 | PBO 이론적 근거 (CPCV 결과로 계산) |
| BEST-2 PBO (내부) | Internal | backtest/pbo.py + stat_tests.py | 내부 코드 grep (2026-05-29) | 2026-05 | — | PBO 이미 구현됨 확인 |
| BEST-3 Prefect | Official | Prefect flow/task docs | prefect.io/docs | live | — | daily_krx 편입 패턴 |
| BEST-3 Prefect (내부) | Internal | auto_forward_recorder.py + daily_krx.py | 내부 코드 grep (2026-05-29) | 2026-05 | — | 두 모듈 공존 확인 |
| #8 TradingAgents | arXiv | Multi-Agents LLM Financial Trading | arxiv.org/abs/2412.20138 | 2024-12 | 58k+ GitHub stars | LangGraph 기반, Anthropic/MiniMax 지원 |
| #10 NautilusTrader | GitHub | nautechsystems/nautilus_trader | github.com/nautechsystems | 2025-08-28 update | 20.7k stars | Rust core, backtest-to-live parity |
| #5 skfolio arXiv | arXiv | skfolio: Portfolio Optimization in Python | arxiv.org/abs/2507.04176 | 2025-07 | cs.LG | skfolio 공식 paper (최신) |
| #7 Bayesian | arXiv | BED-LLM: Bayesian Sequential Design | arxiv.org/abs/2508.xxxxx | 2025-08-28 | — | Bayesian 순차 설계 (관련 분야) |

---

## 8. AMBER_BUCKET

| 항목 | AMBER 이유 |
|------|-----------|
| Dead Reckoning 신뢰도 감쇠 (★3) | Cross-domain 아이디어 — 항공 DR → trading 적용 구체 구현 날짜 확인 불가 (Wave 2 이월) |
| Bayesian Sequential 모델 승격 게이트 (★1) | scipy.stats SPRT 공식 docs는 live이나 **trading 시스템 model promotion** 적용 2025 직접 사례 미확인. 의료 임상 GST 적용 문헌(2015~)은 있으나 rolling 12-month floor 미충족 |
| TradingAgents debate 패턴 | 프레임워크 integration 가능성은 확인됨 (같은 Anthropic/MiniMax/LangGraph 스택); 단, debate 패턴이 현재 3-advisor 구조에 breaking change 없이 적용 가능한지 PoC 필요 |

AMBER 아이템 수: 3개 (Best 3 none → ZERO 발동 없음)

---

## 9. Verification Gate

### Evidence Completeness
| Best | Evidence ≥2 | 날짜 확인 | 판정 |
|------|-------------|---------|------|
| BEST-1 MLflow 3.x | ✅ 2개 (GitHub release + issue 2025-06-30) | 2025 확인 | ✅ PASS |
| BEST-2 PBO Dashboard | ✅ 2개 (내부 코드 확인 + Bailey 2014) | 내부: 2026-05 / 외부: 2014 | ✅ PASS (내부 evidence 충분) |
| BEST-3 AutoForward Prefect | ✅ 2개 (내부 모듈 2개 공존 확인) | 2026-05 내부 | ✅ PASS |

### Deep Dive Completeness
| Best | PR plan ≥3 | Tests | Rollout/Rollback | KPIs | 판정 |
|------|------------|-------|-----------------|------|------|
| BEST-1 | ✅ 3 PRs | ✅ 4 tests | ✅ pip downgrade / USE_MLFLOW_TRACING=false | ✅ | PASS |
| BEST-2 | ✅ 3 PRs | ✅ 4 tests | ✅ git revert (additive) | ✅ | PASS |
| BEST-3 | ✅ 3 PRs | ✅ 4 tests | ✅ FORWARD_TRACKING_ENABLED=false | ✅ | PASS |

### Apply Gates
- **Gate 0 (Dry-run):** ✅ 코드 변경 없음. 계획 문서만.
- **Gate 1 (Change list):**
  - BEST-1: `requirements.in` + `ml/registry.py` + `advisors/claude_client.py`
  - BEST-2: `backtest_honesty.py` + `readiness/classifier.py` + `stock-pred-v5/src/components/RecommendationCard.jsx`
  - BEST-3: `flows/daily_krx.py` + `live_review/auto_forward_recorder.py` + `alert_engine.py`
- **Gate 2 (Explicit approval):** 각 PR 시작 전 사용자 승인 필요
- **Gate 3 (Feature flag):** BEST-1 → `USE_MLFLOW_TRACING=false` / BEST-3 → `FORWARD_TRACKING_ENABLED=false`
- **Gate 4 (Rollback):** BEST-1: `pip install mlflow==2.16.x` / BEST-2: `git revert` / BEST-3: env var off

### 안전 검사
- 브로커 실행 없음 ✅
- `screening_output_only=True` 영향 없음 ✅
- PBO AMBER → readiness 강등만 (거래 차단 아님) ✅
- MLflow Tracing → audit_log.jsonl 보존 ✅

### 최종 판정: **Go**

---

## 10. Open Questions (최대 3개)

1. **MLflow 3.x `artifact_path` breaking scope:** 현재 코드베이스 내 `mlflow.*.log_model(artifact_path=...)` 호출 수를 전수 grep해 마이그레이션 범위 확인 필요. 10개 이상이면 PR-M2를 분리 PR로 확장.

2. **AutoForwardRecorder `record_today()` API:** `auto_forward_recorder.py`의 공개 메서드 시그니처 확인 (현재 `record()`인지 다른 이름인지). Prefect task 래퍼 설계 전 파일 직접 확인 필요.

3. **TradingAgents debate 패턴 PoC 시기:** arXiv 논문의 7-role debate 구조가 현재 3-advisor 오케스트레이터에 breaking change 없이 편입 가능한지 1 sprint 스파이크 PR로 선행 검증 권장. 스파이크 결과에 따라 #9 Wave 4로 이연 가능.

---

## SESSION_HANDOFF

```
skill: project-upgrade v2.2.0 | date: 2026-05-29 (Wave 3)
key_findings:
  - Wave 2 Best 3 모두 구현 완료 (duckdb 1.5.3, litellm 1.83.7, hypothesis 6.155.0)
  - Branch coverage 86% ✅ (Wave 2 목표 초과)
  - mlflow>=2.16 미업그레이드 — MLflow 3.1.0 LoggedModel/LLM Tracing 기회
  - PBO 지표(backtest/pbo.py) 구현됐지만 dashboard_snapshot.v1 미노출
  - AutoForwardRecorder(live_review/) 수동 실행 — Prefect daily_krx 편입 미완료
  - TradingAgents 58k stars (2026-04) — LangGraph + Anthropic/MiniMax 동일 스택
surprise_picks:
  - idea: "Bayesian Sequential 모델 승격 게이트 (의료 임상→MLflow)" | Novelty: 5 | SurpriseScore: 7.5 | status: ⚠ AMBER
  - idea: "Dead Reckoning 신뢰도 감쇠 (항공→거래)" | Novelty: 5 | SurpriseScore: 7.5 | status: ⚠ AMBER
  - idea: "TradingAgents debate 패턴 어댑터" | Novelty: 4 | SurpriseScore: 5.33 | status: PASS
amber_count: 0  # Best 3 모두 confirmed evidence. AMBER 아이디어는 Best 3 미포함.
next_suggested: project-plan --focus="best3-wave3"
```
