# Plan — README.md GitHub 업데이트
**Date:** 2026-05-29
**Type:** DOCS
**Branch:** main
**Scope:** README.md Wave 3 반영 + Mermaid 그래프 신규/수정

---

## 1. 현황 진단

### 1.1 README.md 기본 현황
- 총 **1,489줄**, `## ` 섹션 **35개**
- 기존 Mermaid 그래프: **16개** (flowchart, classDiagram, sequenceDiagram)
- Codex/Hermes 자동 추가 섹션: **7개** → 하단 1/3을 점령해 가독성 저해

### 1.2 Wave 3 미반영 항목 (코드 확인 완료)

| 기능 | 구현 위치 | README 반영 여부 |
|------|---------|----------------|
| `USE_MLFLOW_TRACING` flag | `advisors/claude_client.py:63` | ❌ 미반영 |
| `_wrap_with_mlflow_span()` | `advisors/claude_client.py:723` | ❌ 미반영 |
| `pbo` / `pbo_status` 필드 | `backtest_honesty.py:89,135` | ❌ 미반영 |
| `backtest_honesty_summary` per-candidate | `dashboard_bridge.py:264` | ❌ 미반영 |
| `PboBadge` React 컴포넌트 | `RecommendationCard.jsx` | ❌ 미반영 |
| `forward_tracking_task()` | `flows/daily_krx.py:207` | ❌ 미반영 |
| `FORWARD_TRACKING_ENABLED` flag | `flows/daily_krx.py:25` | ❌ 미반영 |
| `record_today()` 메서드 | `auto_forward_recorder.py` | ❌ 미반영 |

### 1.3 기존 그래프 업데이트 필요 항목

| 섹션 | 줄 | 누락 내용 |
|------|----|---------|
| `## Operating Flow` | 37-48 | forward_tracking, MLflow span 표시 없음 |
| `## Data Contract Type Graph` | 52-107 | `pbo`, `pbo_status`, `ForwardTracking` 클래스 없음 |
| `## 2. System Diagram` | 172-218 | PBO badge, MLflow tracing, forward_tracking 경로 없음 |

---

## 2. 업데이트 목표

1. 상단 3개 그래프를 Wave 3 현실에 맞게 수정
2. 신규 Mermaid 3개 추가 (PBO 흐름, 일별 KRX 플로우, AutoForward 상태 머신)
3. `## What It Does` 테이블에 Wave 3 기능 반영
4. Codex 자동 섹션 7개를 단일 Appendix로 접기

---

## 3. PR 계획

### PR-R1: 기존 그래프 3개 수정
**파일:** `README.md`
**변경 범위:** 줄 37-48, 52-107, 172-218

#### [수정 1] `## Operating Flow` (줄 37-48)
기존 단순 파이프라인 → **Wave 3 전체 흐름** 반영

```mermaid
flowchart LR
  subgraph Sources["데이터 소스"]
    S1[synthetic / yfinance]
    S2[OpenBB optional]
    S3[pykrx KRX]
  end

  subgraph Engine["추천 엔진"]
    E1[Feature Engine] --> E2[Ensemble Model]
    E2 --> E3[Backtester\n+ CPCV/PBO]
    E3 --> E4[Backtest Honesty\npbo_status ≤20% PASS]
    E4 --> E5[Risk Gate\n+ Readiness]
    E5 --> E6[LLM Advisor\nadvisory_score ∈ -1~+1]
    E6 -->|MLflow span\nUSE_MLFLOW_TRACING| E7[(MLflow Traces)]
  end

  subgraph Dashboard["대시보드 REC 탭"]
    D1[RecommendationCard]
    D1 --> D2[PBO Badge\n초록/노랑/빨강]
    D1 --> D3[Advisor Gauge]
    D1 --> D4[Investment Grade]
  end

  subgraph Automation["자동화 (daily_krx_flow 16:30 KST)"]
    A1[Ingest] --> A2[Factors] --> A3[Model]
    A3 --> A4[Portfolio] --> A5[Recommend]
    A5 --> A6[Snapshot] --> A7[forward_tracking\nrecord_today]
    A7 --> A8[Alert]
  end

  Sources --> Engine
  E5 --> Dashboard
  E5 --> Automation
  Automation -. paper only .-> Block[Live Capital\nDisabled]
```

#### [수정 2] `## Data Contract Type Graph` (줄 52-107)
Wave 3 신규 필드 및 클래스 추가

```mermaid
classDiagram
  class RecommendationRun {
    string schema_version
    string generated_at
    BacktestHonestySummary backtest_honesty_summary
    Candidate[] results
  }

  class BacktestHonestySummary {
    string status
    int result_count
    float pbo
    string pbo_status
  }

  class Candidate {
    string symbol
    string signal
    float raw_score
    ModelScores model_scores
    BacktestHonesty backtest_honesty
    BacktestHonestySummary backtest_honesty_summary
    ReadinessResult investment_readiness
  }

  class BacktestHonesty {
    string status
    float pbo
    string pbo_status
    float deflated_sharpe
    float path_pass_rate
  }

  class ModelScores {
    float ensemble
    float logistic
    float xgboost
    float rnn
    float lstm
  }

  class ReadinessResult {
    string status
    bool investable
    bool new_capital_allowed
    bool paper_trading_only
    int investment_readiness_score
    string[] blocking_reasons
  }

  class AdvisorAudit {
    string provider
    float advisory_score
    bool json_strict
    string evidence_path
    string mlflow_span_id
  }

  class ForwardTracking {
    string status
    string date
    string symbol
    int row_count
    string reason
  }

  RecommendationRun --> BacktestHonestySummary
  RecommendationRun --> Candidate
  Candidate --> ModelScores
  Candidate --> BacktestHonesty
  Candidate --> BacktestHonestySummary
  Candidate --> ReadinessResult
  Candidate --> AdvisorAudit
  AdvisorAudit --> ForwardTracking
```

#### [수정 3] `## 2. System Diagram` (줄 172-218)
PBO badge + MLflow tracing + forward_tracking 경로 추가

```mermaid
flowchart LR
    User[Operator] --> BackendCLI[run.ps1 / main.py]
    User --> DashboardUI[stock-pred-v5 dashboard]

    subgraph Backend["stock_1901 - Python backend"]
        BackendCLI --> PackageCLI[src/stock_rtx4060/main.py]
        PackageCLI --> Provider[data_providers.py]
        Provider --> Synthetic[synthetic OHLCV]
        Provider --> YFinance[yfinance]
        Provider --> OpenBB[OpenBB optional]
        Provider --> Audit[audit_log.jsonl]
        PackageCLI --> Engine[recommendation_engine.py]
        Engine --> Feature[feature_engine.py]
        Feature --> Model[ensemble_model.py]
        Model --> Backtest[backtester.py + CPCV/PBO]
        Backtest --> Risk[risk_rules.py]
        Risk --> Reports[Markdown / JSON reports]
        Engine --> Bridge[dashboard_bridge.py\npbo_summary_for_card]
        Bridge --> Snapshot[dashboard_snapshot.v1\n+ pbo_status]
        API[api_server.py :5151] --> Engine
    end

    subgraph Frontend["stock-pred-v5 - React/Vite frontend"]
        Vite[vite.config.js :5173] --> App[src/StockPredV5.jsx]
        App --> RecTab[REC]
        RecTab --> RecCard[RecommendationCard.jsx]
        RecCard --> PBOBadge[PBO Badge\n초록/노랑/빨강]
        RecCard --> AdvisorGauge[Advisor Gauge −1~+1]
        PublicSnapshot[public/dashboard_snapshot.json] --> RecCard
    end

    subgraph Flows["Prefect Flows (자동화)"]
        KRX[daily_krx_flow\n16:30 KST Mon-Fri]
        KRX --> FT[forward_tracking_task\nrecord_today]
        FT --> Evidence[reports/live_review/]
    end

    subgraph Observability["Observability (선택)"]
        MLF[MLflow Traces\nUSE_MLFLOW_TRACING=true]
    end

    Snapshot --> PublicSnapshot
    RecCard -. API mode .-> API
    Engine --> MLF
    Backend --> Flows
```

---

### PR-R2: 신규 Mermaid 섹션 3개 추가

**파일:** `README.md` — `## 22. Wave 3 Upgrade` 섹션 내부에 삽입

#### [신규 1] PBO 판정 흐름도 (flowchart)

```mermaid
flowchart LR
    CPCV[CPCV 백테스트\npath_pass_rate / deflated_sharpe] --> PBO[pbo 계산\n0.0 ~ 1.0]
    PBO --> Gate{pbo_status\n임계값 판정}
    Gate -->|pbo ≤ 0.20| PASS[PASS\n초록 배지]
    Gate -->|0.20 < pbo ≤ 0.50| AMBER[AMBER\n노란 배지]
    Gate -->|pbo > 0.50| RED[RED\n빨간 배지]
    Gate -->|CPCV 미실행| ND[NO_DATA\n회색 배지]
    PASS --> Card[REC 카드\nPBO Badge]
    AMBER --> Card
    RED --> Card
    RED --> Down[readiness 강등\n반영금지]
    AMBER --> Down2[readiness 강등\n검토전용]
    Card --> Snapshot[dashboard_snapshot.v1\nbacktest_honesty_summary.pbo_status]
```

#### [신규 2] daily_krx_flow 9단계 (flowchart TD)

```mermaid
flowchart TD
    Start([16:30 KST\nMon-Fri]) --> T1
    T1[1 ingest_kis_task\nKIS API 일봉 수집] --> T2
    T2[2 corp_actions_adjust_task\n분할·배당 역조정] --> T3
    T3[3 factor_compute_task\nAlpha101 등 팩터 계산] --> T4
    T4[4 model_predict_task\nMLflow 프로덕션 모델 추론] --> T5
    T5[5 portfolio_optimize_task\nHRP/CVaR 비중 최적화] --> T6
    T6[6 recommend_task\n추천 엔진 실행] --> T7
    T7[7 snapshot_dashboard_task\ndashboard_snapshot.v1 생성] --> T8
    T8[8 forward_tracking_task ★\nrecord_today 자동 기록\nFORWARD_TRACKING_ENABLED] --> T9
    T9[9 alert_task\nSlack/Discord 알림\n+ forward_tracking_status]
    T9 --> End([완료])

    style T8 fill:#f0f9ff,stroke:#0ea5e9
```

#### [신규 3] AutoForwardRecorder 상태 머신 (stateDiagram-v2)

```mermaid
stateDiagram-v2
    direction LR
    [*] --> FORWARD_PAPER_RUNNING : 초기 상태
    FORWARD_PAPER_RUNNING --> FORWARD_PAPER_RUNNING : 매 거래일\nrecord_today() 호출\n(FORWARD_TRACKING_ENABLED=true)
    FORWARD_PAPER_RUNNING --> SKIPPED : 비거래일 또는\n장 마감 전\n(KRX 15:30 KST 이전)
    SKIPPED --> FORWARD_PAPER_RUNNING : 다음 거래일
    FORWARD_PAPER_RUNNING --> FORWARD_COMPLETE_USER_REVIEW_REQUIRED : 30거래일 달성
    FORWARD_COMPLETE_USER_REVIEW_REQUIRED --> [*] : 수동 검토 완료

    note right of FORWARD_PAPER_RUNNING
        auto_promote = False (불변)
        new_capital_allowed = False (불변)
        broker_order_execution = False (불변)
        manual_approval_required = True (불변)
    end note
```

---

### PR-R3: 구조 정리

**파일:** `README.md`

#### 작업 목록

| 번호 | 작업 | 상세 |
|------|------|------|
| 1 | Codex/Hermes 자동 섹션 축소 | 7개 섹션(`## Codex Documentation Update...`, `## Hermes Documentation Update...`) → `## Appendix — Auto-generated Documentation Logs` 하나로 접기 |
| 2 | `## What It Does` 테이블 업데이트 | Advisor layer 행: LiteLLM + MLflow tracing 추가<br/>Data and validation 행: PBO(backtest_honesty_summary) 추가 |
| 3 | `## 7. Dashboard` 구조 테이블 | `RecommendationCard.jsx`에 PBO Badge 행 추가 |
| 4 | `## 13. Validation Commands` | MLflow tracing 확인 커맨드 추가 |

---

## 4. 실행 순서 및 타임라인

```
Day 1 오전 (1h)
  PR-R1: 기존 그래프 3개 수정
    - Operating Flow
    - Data Contract classDiagram
    - System Diagram

Day 1 오후 (1h)
  PR-R2: 신규 섹션 3개 추가
    - PBO 판정 flowchart
    - daily_krx_flow 9단계 flowchart
    - AutoForwardRecorder stateDiagram

Day 2 (30min)
  PR-R3: 구조 정리
    - Codex 자동 섹션 축소
    - What It Does 테이블 업데이트
    - Dashboard 구조 테이블 업데이트
```

---

## 5. 검증 게이트

각 PR 전 확인:

```bash
# Mermaid syntax 검증 (Node.js)
npx @mermaid-js/mermaid-cli -i README.md -o /tmp/readme_check.svg

# 링크 유효성
grep -oP '\(\.\/[^)]+\)' README.md | tr -d '()' | while read f; do
  [ -e "$f" ] && echo "OK: $f" || echo "BROKEN: $f"
done

# 용어 일관성 (pbo_status 표기 통일)
grep -c "pbo_status" README.md
```

---

## 6. 변경 범위 요약

| PR | 변경 줄 (예상) | 그래프 수 | 리스크 |
|----|--------------|---------|--------|
| PR-R1 | ~120줄 교체 | 3개 수정 | 낮음 (기존 그래프 교체) |
| PR-R2 | ~100줄 추가 | 3개 신규 | 낮음 (additive) |
| PR-R3 | ~400줄 축소 | 0 | 중간 (Codex 섹션 축소) |
| **합계** | **~620줄** | **6개** | — |

---

## 7. 승인 체크리스트

- [ ] PR-R1 그래프 3개 Mermaid syntax 오류 없음
- [ ] PR-R2 신규 섹션 3개 기존 내용 삭제 없음 (additive)
- [ ] PR-R3 Codex 섹션 내용 Appendix에 보존됨 (삭제 아님)
- [ ] GitHub Actions CI green
- [ ] `## Current Operating Verdict` 상단 표 변경 없음 (운영 현황 불변)
