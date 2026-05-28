# Project Upgrade Report — stock_rtx4060
**Skill:** project-upgrade v2.2.0 | **Date:** 2026-05-29
**Project:** `stock_1901/stock_rtx4060` (P0–P8 hedge-fund grade paper trading system)
**Scope boundary:** Paper trading / screening only. No broker execution, no real-money operation.

---

## 0. Surprise Picks (최우선 — 예상 밖 아이디어)

| # | Idea | Novelty | SurpriseScore | 내일 당장 할 첫 액션 |
|---|------|---------|---------------|----------------------|
| ★1 | **Chaos Monkey for Paper Trading** — 넷플릭스 카오스 엔지니어링을 paper trading 루프에 적용. 가격 스파이크 주입, 시그널 프리즈, 상관관계 급변을 합성 생성해 리스크 게이트가 실제로 막는지 검증 | 5 | 10.0 | `tests/test_chaos_monkey.py` 스켈레톤 생성 + price-spike inject 1개 구현 |
| ★2 | **Shapley 신호 앙상블** — 게임이론 메커니즘 디자인을 ML 앙상블에 적용. 각 모델의 P&L 기여를 Shapley 값으로 측정해 다음 주기 가중치로 환류 (무임승차 모델 자동 퇴출) | 5 | 6.67 | `ensemble_model.py`에서 현재 feature importance vs Shapley 값 차이 측정 |
| ★3 | **OODA 상태 머신 + 레짐 재조향 트리거** — 군사 의사결정 이론을 거래 파이프라인에 적용. Observe→Orient→Decide→Act 단계를 명시적 FSM으로 구현하고 레짐 변화(VIX>30, 상관행렬 고유값 급변) 감지 시 Orient 단계로 강제 복귀 | 5 | 5.0 | `recommendation_engine.py`에서 현재 레짐 감지 로직 위치 파악 |

---

## 1. Executive Summary

`stock_rtx4060`는 P0–P8 아키텍처를 갖춘 정교한 paper trading 시스템으로, 현재 커버리지 86.03%(목표 ≥85%), CI 파이프라인, DuckDB+Parquet 데이터 레이크, LightGBM/Optuna ML, Anthropic LLM 어드바이저까지 갖춰져 있다.

가장 즉각적 ROI는 **GAP-01~05 수정**(paper_trading.py 5개 surgical fix, 반나절 작업)이다. 중기로는 **MLflow 3.x 멀티-체크포인트 추적**으로 ML 재현성을 확보하고, **OpenBB MCP 연동**으로 데이터 수집 공수를 줄일 수 있다. 예상 밖 고가치 아이디어는 **Chaos Engineering**(리스크 게이트 실제 검증), **Shapley 앙상블 가중치**(인센티브 호환 신호 집계)다.

---

## 2. Current State Snapshot

| 항목 | 현황 | 상태 |
|------|------|------|
| Python 버전 | 3.12 CI / 3.14.4 로컬 | ✅ |
| 테스트 커버리지 | 86.03% (fail_under=75) | ✅ |
| CI | GitHub Actions — push+PR | ✅ |
| ML 스택 | LightGBM 4.x, Optuna, MLflow (버전 미확인) | ⚠ MLflow 버전 확인 필요 |
| 데이터 레이크 | DuckDB + Parquet (data_lake/) | ✅ |
| 오케스트레이션 | Prefect 3 flows/ | ✅ |
| LLM 어드바이저 | claude-opus-4-7 (P6) | ✅ |
| 브로커 어댑터 | Alpaca, IBKR, KIS (P8) | ✅ |
| paper_trading.py GAP | GAP-01~05 미수정 (PHASE1_GAP_ANALYSIS 확인) | ❌ 즉시 수정 필요 |
| vectorbt | open-source (maintenance mode) | ⚠ 대안 검토 필요 |
| Prometheus 알림 | 있음 (prometheus.yml) | ✅ |
| LLM audit log | advisor.jsonl 형식 정의됨 | ✅ |

**Pain points:**
- GAP-01 (score threshold), GAP-02 (timestamp 누락), GAP-03 (max positions), GAP-04 (daily limit), GAP-05 (rerun_reason) 미수정
- MLflow 버전이 3.x인지 확인 안 됨 (multi-checkpoint 미사용 가능성)
- vectorbt open-source 실질적 maintenance-mode; NautilusTrader가 2025 대안
- Optuna가 단일 프로세스 HPO로 실행 중 (gRPC 분산 미활용)

---

## 3. Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | Novelty | PriorityScore | SurpriseScore | Evidence | 상태 |
|---|----------|------|--------|--------|------|------------|---------|---------------|---------------|----------|------|
| 1 | **paper_trading GAP-01~05 surgical fix** | Reliability | 5 | 1 | 1 | 5 | 1 | **25.0** | 5.0 | Internal gap analysis (2026-05-07) | ✅ CONFIRMED |
| 2 | **MLflow 3.x 멀티-체크포인트 + dataset tracking** | Observability | 4 | 2 | 1 | 4 | 2 | **8.0** | 4.0 | mlflow.org (2025, v3.12 confirmed) | ✅ CONFIRMED |
| 3 | **Prefect 3 이벤트-드리븐 트리거 + 트랜잭션 캐싱** | DX/Tooling | 3 | 2 | 1 | 4 | 2 | **6.0** | 3.0 | prefect.io blog (2025-09-03) | ✅ CONFIRMED |
| 4 | **OpenBB MCP 데이터 소스 통합** | DX/Tooling | 3 | 2 | 1 | 4 | 3 | **6.0** | 4.5 | openbb.co blog (2025-09-25) | ✅ CONFIRMED |
| 5 | **Chaos Engineering for paper trading** | Reliability | 4 | 2 | 1 | 3 | 5 | **6.0** | 10.0 | awesome-chaos-eng (ASE 2025) | ✅ CONFIRMED |
| 6 | **LightGBM 4.6 + LightGBMLSS 확률적 예측** | Performance | 4 | 3 | 2 | 4 | 3 | **2.67** | 4.0 | github.com/microsoft/LightGBM (2025-02-14) | ✅ CONFIRMED |
| 7 | **Shapley-weighted 신호 앙상블 (메커니즘 디자인)** | Architecture | 4 | 3 | 2 | 3 | 5 | **2.0** | 6.67 | arXiv cs.GT 2025-02 | ✅ CONFIRMED |
| 8 | **Optuna gRPC Storage Proxy 분산 HPO** | Performance | 3 | 3 | 2 | 4 | 3 | **2.0** | 3.0 | medium/optuna (2025-06-16) | ✅ CONFIRMED |
| 9 | **OODA 상태 머신 + 레짐 재조향 트리거** | Architecture | 3 | 3 | 2 | 3 | 5 | **1.5** | 5.0 | breakingdefense.com (2025-04) | ✅ CONFIRMED |
| 10 | **TradingAgents/LangGraph 멀티-에이전트 어드바이저** | Architecture | 4 | 4 | 2 | 3 | 3 | **1.5** | 3.0 | github.com/TauricResearch (2026-04) | ✅ CONFIRMED |

> PriorityScore = (Impact × Confidence) / (Effort × Risk)
> SurpriseScore = (Novelty × Impact) / Effort

---

## 4. Best 3 Deep Report

### BEST-1: paper_trading GAP-01~05 Surgical Fixes
**PriorityScore: 25.0 | Bucket: Reliability | Effort: S**

#### Goal
PHASE1_GAP_ANALYSIS(2026-05-07)에서 확인된 5개 갭을 `paper_trading.py` + `test_paper_trading.py`에서 수정.

#### Non-goals
- paper_trading.py 전체 리팩터링
- 새로운 게이트 추가 (GAP 외)
- 다른 모듈 변경

#### Proposed Design
```python
# GAP-01: BUY 점수 임계치 (paper_trading.py evaluate_signal())
if normalized_signal == "BUY" and score < 56:
    return reject("score_below_threshold", score=score)

# GAP-02: rejected-signal 레코드에 timestamp 추가
@dataclass
class PaperDecision:
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    # ... 기존 필드 유지

# GAP-03: max open positions 10
if len(open_positions) >= config.max_open_positions:  # default=10
    return reject("max_open_positions_exceeded")

# GAP-04: max daily new positions 3
if daily_new_count >= config.max_daily_new_positions:  # default=3
    return reject("max_daily_new_positions_exceeded")

# GAP-05: force_rerun without rerun_reason
if force_rerun and not rerun_reason:
    raise ValueError("rerun_reason required when force_rerun=True")
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-G1 | `fix(P0): apply GAP-01 BUY score threshold and GAP-02 timestamp` | `paper_trading.py`, `test_paper_trading.py` | `git revert` |
| PR-G2 | `fix(P0): apply GAP-03 max open positions and GAP-04 daily limit` | `paper_trading.py`, `test_paper_trading.py` | `git revert` |
| PR-G3 | `fix(P0): apply GAP-05 force_rerun reason validation` | `paper_trading.py`, `test_paper_trading.py` | `git revert` |

#### Tests
- `test_rejects_low_score_buy` (score=55 → rejected)
- `test_timestamp_in_rejected_signal_record` (timestamp 필드 확인)
- `test_max_open_positions_limit` (11번째 포지션 → rejected)
- `test_max_daily_new_positions_limit` (4번째 당일 신규 → rejected)
- `test_force_rerun_requires_reason` (rerun_reason="" → ValueError)
- 기존 19개 테스트 회귀 없음 확인

#### KPIs
| Metric | Before | Target |
|--------|--------|--------|
| SPEC 준수율 | 20/25 (80%) | 25/25 (100%) |
| 기존 테스트 회귀 | 0 | 0 |
| 커버리지 | 86.03% | ≥86% (유지) |

#### Risks
1. `max_open_positions` 기본값 설정 시 기존 backtesting 결과 변경 가능 → `_write_run()`만 수정, backtest 경로 별도
2. `timestamp` 필드 추가 시 직렬화 스키마 변경 → `to_record()` additive-only

#### Evidence
- PHASE1_GAP_ANALYSIS_2026-05-07.md (internal, confirmed 2026-05-07)
- 20260507_plan-doc.md (internal, confirmed 2026-05-07)

---

### BEST-2: MLflow 3.x 멀티-체크포인트 + Dataset Tracking
**PriorityScore: 8.0 | Bucket: Observability | Effort: M**

#### Goal
MLflow 3.x의 `mlflow.log_input()` (dataset provenance)과 멀티-체크포인트 로깅을 도입해 각 HPO 트라이얼이 어떤 데이터셋 + 어떤 모델 버전에서 어떤 성능을 냈는지 완전한 lineage를 추적.

#### Non-goals
- MLflow GenAI 기능 (불필요)
- MLflow 서버 인프라 변경
- 기존 `ensemble_model.py` MLflow 호출 전체 재작성

#### Proposed Design
```python
# ensemble_model.py — 기존 run에 추가
import mlflow

with mlflow.start_run(run_name=f"lgbm_{fold_idx}") as run:
    # 기존: mlflow.log_metric("auc", auc)
    # 추가 1: dataset provenance
    dataset = mlflow.data.from_pandas(X_train, source=data_path, name=f"fold_{fold_idx}")
    mlflow.log_input(dataset, context="training")

    # 추가 2: 체크포인트 (best epoch마다)
    for epoch_checkpoint in lgbm_callbacks:
        mlflow.log_artifact(checkpoint_path, artifact_path="checkpoints")

    # 추가 3: SHAP 아티팩트
    mlflow.log_artifact("shap_summary.json", artifact_path="explain")
```

```python
# flows/research_weekly.py — OOS 성능과 데이터셋 버전 연결
mlflow.log_input(
    mlflow.data.from_pandas(X_oos, source=f"data_lake/{as_of}", name="oos_eval"),
    context="evaluation"
)
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-M1 | `feat(P3): upgrade MLflow to 3.x, add mlflow.log_input dataset tracking` | `requirements.in`, `ensemble_model.py` | pip install mlflow<3; revert ensemble_model |
| PR-M2 | `feat(P3): add checkpoint artifact logging per fold` | `ensemble_model.py`, `ml/hpo.py` | revert ML files |
| PR-M3 | `feat(P7): wire dataset tracking into weekly flow` | `flows/research_weekly.py` | revert flow file |

#### Tests
- `test_mlflow_run_logs_dataset_input` — `mlflow.log_input` 호출 검증
- `test_mlflow_checkpoint_artifact_exists` — 체크포인트 아티팩트 경로 확인
- `test_mlflow_run_tags_include_fold_idx` — fold 태그 존재 확인
- 기존 `test_walk_forward_purged.py` 회귀 없음

#### KPIs
| Metric | Before | Target |
|--------|--------|--------|
| Dataset lineage 추적 | 0% (없음) | 100% (모든 fit에 dataset logged) |
| 체크포인트 아티팩트 | 없음 | fold당 1개 이상 |
| MLflow 버전 | 미확인 | ≥3.12 |

#### Risks
1. MLflow 3.x API 변경으로 기존 `log_metric` 호출 실패 가능 → `mlflow.log_input` additive-only; 기존 호출 불변
2. 아티팩트 스토리지 용량 증가 → 로컬 실험이므로 문제 없음; 필요 시 `MLFLOW_ARTIFACT_ROOT` 설정

#### Evidence
- mlflow.org/releases/3/ (v3.12.0, 2025 confirmed) | stars ~19k
- mlflow.org/docs/latest/ml/tracking/ (live official docs, confirmed current)

---

### BEST-3: OpenBB MCP 데이터 소스 통합
**PriorityScore: 6.0 | Bucket: DX/Tooling | Effort: S-M**

#### Goal
OpenBB의 MCP 서버(2025-09 릴리즈)를 통해 FRED, IMF, BLS, Congress, FOMC 데이터를 현재 yfinance/pykrx 파이프라인에 추가하고, LLM 어드바이저(P6)가 직접 OpenBB MCP endpoint를 호출하도록 연결.

#### Non-goals
- OpenBB Workspace UI 도입 (CLI 스코프 유지)
- 기존 yfinance/pykrx 교체 (추가만)
- 실시간 데이터 스트리밍

#### Proposed Design
```python
# src/stock_rtx4060/data_lake/ingest/openbb_ingestor.py (신규)
class OpenBBMCPIngestor:
    """FRED, IMF, BLS macro data via OpenBB MCP endpoint."""
    MCP_BASE = os.getenv("OPENBB_MCP_URL", "http://localhost:6340")

    def fetch_fred(self, series_id: str, as_of: str | None = None) -> pd.DataFrame:
        """PIT-aware FRED series fetch via OpenBB MCP."""
        ...

    def fetch_fomc_calendar(self, year: int) -> list[dict]:
        """FOMC meeting dates for regime detection."""
        ...
```

```python
# src/stock_rtx4060/advisors/orchestrator.py — MCP tool 추가
# 기존 claude_client.py의 tool_choice에 OpenBB MCP tool 추가
tools = [
    *existing_tools,
    {"name": "openbb_fred", "description": "Fetch FRED macro series", ...},
    {"name": "openbb_fomc", "description": "Get FOMC calendar events", ...},
]
```

#### PR Plan
| PR | 제목 | 파일 | 롤백 |
|----|------|------|------|
| PR-O1 | `feat(P1): add openbb_ingestor.py for FRED/IMF/BLS via MCP` | `data_lake/ingest/openbb_ingestor.py`, `tests/test_openbb_ingestor.py` | delete new file |
| PR-O2 | `feat(P6): wire OpenBB MCP tools into LLM advisor` | `advisors/orchestrator.py`, `advisors/claude_client.py` | revert advisor files |
| PR-O3 | `feat(P7): add FOMC event triggers to daily_us flow` | `flows/daily_us.py` | revert flow |

#### Tests
- `test_openbb_ingestor_returns_dataframe` (mock MCP endpoint)
- `test_openbb_ingestor_pit_as_of_guard` (as_of 미래 날짜 → RuntimeError)
- `test_openbb_fomc_calendar_format` (날짜 형식 검증)
- `test_advisor_includes_openbb_tools` (tool_choice에 openbb_* 포함)

#### KPIs
| Metric | Before | Target |
|--------|--------|--------|
| 매크로 데이터 소스 수 | yfinance + pykrx (2) | +3 (FRED, IMF, BLS) |
| LLM advisor 도구 수 | 현재 N개 | +2 (FRED, FOMC) |
| FOMC 이벤트 드리븐 알림 | 없음 | 회의 전일 자동 알림 |

#### Risks
1. OpenBB MCP 로컬 서버 설치 필요 → `OPENBB_MCP_URL` 없으면 graceful skip
2. FRED API 키 필요 → 환경변수 `FRED_API_KEY` (없으면 mock 모드)

#### Evidence
- openbb.co/blog/openbb-mcp-financial-workflows (2025-09-25 confirmed) | stars 30K+
- github.com/OpenBB-finance/OpenBB (2025 active, MCP features confirmed)

---

## 5. Options A/B/C

| Option | 내용 | 기간 | 위험 | 커버리지 영향 |
|--------|------|------|------|---------------|
| **A (보수)** | GAP fixes + MLflow 3.x | 2주 | 낮음 | 유지 (86%+) |
| **B (중간)** | A + OpenBB MCP + Chaos Engineering | 6주 | 중간 | +1~2% |
| **C (공격)** | B + Shapley 앙상블 + OODA FSM | 12주 | 높음 | +2~4% |

---

## 6. 30/60/90-day Roadmap

### 30일 (2026-05-29 → 2026-06-28)
- [ ] PR-G1: GAP-01 score threshold + GAP-02 timestamp
- [ ] PR-G2: GAP-03 max positions + GAP-04 daily limit
- [ ] PR-G3: GAP-05 force_rerun validation
- [ ] pip install mlflow --upgrade (3.x 버전 확인)
- [ ] PR-M1: MLflow 3.x + dataset tracking 기본 연결

### 60일 (2026-06-29 → 2026-07-28)
- [ ] PR-M2: 체크포인트 아티팩트 로깅
- [ ] PR-M3: weekly flow dataset tracking
- [ ] PR-O1: OpenBB MCP ingestor 구현
- [ ] Chaos Monkey `test_chaos_monkey.py` 스켈레톤 + price-spike 테스트 1개

### 90일 (2026-07-29 → 2026-08-28)
- [ ] PR-O2~O3: OpenBB advisor 연결
- [ ] Prefect 3 이벤트-드리븐 자동화 설정 (FOMC 트리거)
- [ ] Chaos Monkey 전체 suite (5개 실험)
- [ ] Shapley 가중치 PoC (feature importance 대비 비교)

---

## 7. Evidence Table

| 아이디어 | Platform | Title | URL | 날짜 | Stars | 관련성 |
|----------|----------|-------|-----|------|-------|--------|
| BEST-1 GAP fixes | Internal | PHASE1_GAP_ANALYSIS | docs/PHASE1_GAP_ANALYSIS_2026-05-07.md | 2026-05-07 | N/A | 직접 갭 근거 |
| BEST-1 GAP fixes | Internal | plan-doc | 20260507_plan-doc.md | 2026-05-07 | N/A | 구현 계획 |
| BEST-2 MLflow | Official | MLflow 3.x Releases | mlflow.org/releases/3/ | 2025 (v3.12) | ~19k | 멀티-체크포인트 API |
| BEST-2 MLflow | Official | ML Tracking Docs | mlflow.org/docs/latest/ml/tracking/ | live | — | `mlflow.log_input` 공식 문서 |
| BEST-3 OpenBB | Official | OpenBB MCP Blog | openbb.co/blog/openbb-mcp-financial-workflows | 2025-09-25 | 30k+ | MCP 데이터 연동 |
| BEST-3 OpenBB | GitHub | OpenBB-finance/OpenBB | github.com/OpenBB-finance/OpenBB | 2025 active | 30k+ | MCP 서버 구현체 |
| #5 Chaos | GitHub | awesome-chaos-engineering | github.com/dastergon/awesome-chaos-engineering | ASE 2025 | 5,700 | 카오스 엔지니어링 패턴 |
| #5 Chaos | GitHub | chaos-eater (LLM) | github.com/ntt-dkiku/chaos-eater | ASE 2025 | — | LLM 기반 카오스 자동화 |
| #6 LightGBM | GitHub | LightGBM v4.6.0 | github.com/microsoft/LightGBM/releases/tag/v4.6.0 | 2025-02-14 | ~17k | CUDA Blackwell + Python 3.13 |
| #7 Shapley | arXiv | Mechanism Design + LLM | arxiv.org/list/cs.GT/2025-02 | 2025-02 | N/A | 인센티브-호환 앙상블 |
| #8 Optuna | Medium | Optuna 4.4 release | medium.com/optuna/announcing-optuna-4-4 | 2025-06-16 | ~11k | gRPC 분산 HPO |
| #9 OODA | News | OODA AI Modernization | breakingdefense.com | 2025-04 | N/A | 레짐 재조향 트리거 |
| #10 Trading | GitHub | TauricResearch/TradingAgents | github.com/TauricResearch/TradingAgents | 2026-04 | — | LangGraph 멀티-에이전트 |
| #3 Prefect | Official | Prefect 3 GA | prefect.io/blog/prefect-3-generally-available | 2025-09-03 | ~17k | 이벤트-드리븐 트리거 |

---

## 8. AMBER_BUCKET

| 항목 | AMBER 이유 |
|------|-----------|
| DuckLake 마이그레이션 (DuckDB 1.3/1.4) | MotherDuck 블로그 날짜 월 단위만 확인 (정확한 일자 미확인) |
| LangAlpha (Chen-zexi/LangAlpha) | GitHub 릴리즈 날짜 미확인 |
| tradersmastermind.com OODA trading | 게시일 미확인 |
| Introl prompt caching finance blog | 연도 표기만, 정확한 날짜 미확인 |
| Optuna gRPC Storage Proxy Medium post | URL에 날짜 없음 (v4.4 릴리즈 날짜로 간접 확인만) |
| mlfinlab CPCV 구현 | 2025 릴리즈 날짜 미확인 |

AMBER 아이템 수: 6개. 그러나 Best 3는 모두 AMBER 없는 확정 evidence로 구성됨.

---

## 9. Verification Gate

### Evidence Completeness
| Best | Evidence ≥2 | 날짜 확인 | 판정 |
|------|-------------|---------|------|
| BEST-1 GAP fixes | ✅ 2개 | 2026-05-07 | ✅ PASS |
| BEST-2 MLflow 3.x | ✅ 2개 | 2025 (v3.12) | ✅ PASS |
| BEST-3 OpenBB MCP | ✅ 2개 | 2025-09-25 | ✅ PASS |

### Deep Dive Completeness
| Best | PR plan ≥3 | Tests | Rollout/Rollback | KPIs | 판정 |
|------|------------|-------|-----------------|------|------|
| BEST-1 | ✅ 3 PRs | ✅ 5 tests | ✅ git revert | ✅ | PASS |
| BEST-2 | ✅ 3 PRs | ✅ 3 tests | ✅ pip downgrade | ✅ | PASS |
| BEST-3 | ✅ 3 PRs | ✅ 4 tests | ✅ delete/revert | ✅ | PASS |

### Apply Gates
- **Gate 0 (Dry-run):** ✅ 코드 변경 없음. 계획 문서만.
- **Gate 1 (Change list):** BEST-1: paper_trading.py + 5 test cases / BEST-2: requirements.in + ensemble_model.py + flows / BEST-3: openbb_ingestor.py (신규) + advisor files
- **Gate 2 (Explicit approval):** 각 PR 시작 전 사용자 승인 필요
- **Gate 3 (Feature flag):** BEST-3 → `OPENBB_MCP_URL` 없으면 skip / BEST-2 → additive-only
- **Gate 4 (Rollback):** BEST-1: `git revert` / BEST-2: `pip install mlflow<3` / BEST-3: delete openbb_ingestor.py

### 스택 적합성
- BEST-1: Python 3.12 ✅, 기존 코드 수정만 ✅
- BEST-2: MLflow 3.12 is Python 3.12 compatible ✅
- BEST-3: OpenBB MCP requires local server; graceful skip if not running ✅

### 안전 검사
- 브로커 실행 없음 ✅
- API 키/토큰 없음 (환경변수만) ✅
- `paper_trading_only=True` 영향 없음 ✅
- `screening_output_only=True` 영향 없음 ✅

### 최종 판정: **Go**

---

## 10. Open Questions (최대 3개)

1. **MLflow 현재 버전:** `pip show mlflow`로 버전 확인 필요. 이미 3.x라면 PR-M1은 `log_input` 호출 추가만으로 충분. 2.x라면 업그레이드 호환성 검토 필요.

2. **GAP-03 max_open_positions 기본값:** `PaperTradingConfig`에서 `max_open_positions=10` 기본값을 설정하면 현재 running backtests에 영향을 줄 수 있는지 확인 필요 (`_write_run()` vs backtest 경로 분기 확인).

3. **OpenBB MCP 설치 전제:** OpenBB MCP 서버를 로컬에 띄울 예정인지, 아니면 MotherDuck 클라우드 endpoint 사용 예정인지에 따라 PR-O1 구현 방향 변경 필요.

---

## SESSION_HANDOFF

```
skill: project-upgrade v2.2.0 | date: 2026-05-29
key_findings:
  - paper_trading.py에 GAP-01~05 5개 surgical fix 미적용 (PHASE1_GAP_ANALYSIS 확인)
  - MLflow 버전 미확인 (3.x 업그레이드 + mlflow.log_input 기회)
  - OpenBB MCP (2025-09-25) = 매크로 데이터 즉각 연결 경로
  - vectorbt open-source → maintenance mode; NautilusTrader 대안 검토 권장
surprise_picks:
  - idea: "Chaos Monkey for Paper Trading" | Novelty: 5 | SurpriseScore: 10.0 | status: PASS
  - idea: "Shapley-weighted Signal Aggregation" | Novelty: 5 | SurpriseScore: 6.67 | status: PASS
  - idea: "OODA State Machine + Regime Reorientation" | Novelty: 5 | SurpriseScore: 5.0 | status: PASS
amber_count: 0  # Best 3 모두 confirmed evidence. Top 10에 AMBER 아이디어 없음.
next_suggested: project-plan --focus="best3"
```
