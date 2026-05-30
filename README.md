# stock_1901 — 주식 추천 연구 시스템

**Python 3.12 · Flask API · React/Vite 대시보드 · Prefect 플로우 · hedge-fund grade (P0–P8)**

> ⚠️ **운영 현황:** `AMBER WATCHLIST` — 리서치·페이퍼트레이딩 전용. 라이브 주문 없음.

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [아키텍처](#2-아키텍처)
3. [데이터 계약 타입 맵](#3-데이터-계약-타입-맵)
4. [최신 반영 요약](#4-최신-반영-요약)
5. [빠른 시작](#5-빠른-시작)
6. [CLI 명령어](#6-cli-명령어)
7. [대시보드](#7-대시보드)
8. [일별 KRX 자동화 플로우](#8-일별-krx-자동화-플로우)
9. [AutoForwardRecorder 상태 머신](#9-autoforwardrecorder-상태-머신)
10. [투자 준비도 판정](#10-투자-준비도-판정)
11. [안전 경계](#11-안전-경계)
12. [테스트 및 CI](#12-테스트-및-ci)
13. [모듈 구성 (P0–P8)](#13-모듈-구성-p0p8)
14. [출력 파일 위치](#14-출력-파일-위치)
15. [알려진 이슈 및 워크어라운드](#15-알려진-이슈-및-워크어라운드)

---

## 1. 시스템 개요

### 운영 현황

| 항목 | 현재 정책 |
|---|---|
| 라이브 투자 상태 | `AMBER WATCHLIST` |
| 신규 자본 | `new_capital_allowed=false` |
| 실행 모드 | `paper_trading_only=true` |
| 허용 용도 | 리서치, 관심종목, 페이퍼트레이딩, 대시보드 모니터링 |
| 차단 용도 | 라이브 자본, 브로커 주문 실행, 자동 매수/매도 |

### 무엇을 하는가

| 영역 | 기능 |
|---|---|
| 추천 엔진 | OHLCV·팩터·모델점수·리스크룰·어드바이저 증거 기반 후보 추천 |
| 투자 준비도 | backtest_honesty·PBO·3x 비용생존·엠바고 스트레스·어드바이저 감사 게이트 |
| 대시보드 | REC탭 — 후보카드·PBO뱃지·어드바이저게이지·투자등급 |
| **Executive Dashboard v2.1** | **`VITE_DASHBOARD_LAYOUT=executive` — HeaderBar·KPI·AI Decision Panel·Watchlist·Scenario** |
| 모델 점수 | 앙상블·LogReg·XGBoost·GRU/RNN (LSTM 선택) |
| 어드바이저 | LiteLLM 게이트웨이 · MLflow span tracing · AMH memory · OpenBB tool-use |
| **Thompson Sampling MAB** | **`thompson_weights.py` — Beta 분포 기반 advisor 가중치 동적 결정 (`ADVISOR_WEIGHTS_MODE=mab`)** |
| **NotebookLM 뉴스** | **iran-war-notelm API 연동 — 뉴스→분석→LLM Advisor 주입 (NOTEBOOKLM_NEWS_MODE=cache)** |
| CMRS Sizing | Mondrian conformal sizing — `size_multiplier` 기반 downgrade-only score 감쇠 |
| 자동화 | Prefect `daily_krx_flow` 9단계, `research_weekly_flow` RD-Agent + SPRT 보조 태스크 |
| 검증 | Hypothesis PBT · Chaos 테스트 · CPCV/PBO 백테스트 |

---

## 2. 아키텍처

### 전체 시스템

```mermaid
flowchart LR
    User[운영자] --> CLI[run.ps1 / main.py]
    User --> UI[stock-pred-v5\n대시보드]

    subgraph Backend["Python 백엔드 (stock_1901)"]
        CLI --> Engine[recommendation_engine.py]
        Engine --> Feature[feature_engine.py]
        Feature --> Model[ensemble_model.py\nLGBM · XGB · GRU]
        Model --> BT[backtester.py\n+ CPCV/PBO]
        BT --> Honesty[backtest_honesty.py\npbo_status]
        Honesty --> Risk[risk_rules.py\n+ readiness]
        Risk --> Advisor[LLM Advisor\nadvisory_score −1~+1]
        Advisor -->|MLflow span| MLF[(MLflow Traces)]
        Risk --> Bridge[dashboard_bridge.py\npbo_summary_for_card]
        Bridge --> Snap[dashboard_snapshot.v1]
        API[api_server.py :5151] --> Engine
    end

    subgraph Frontend["React 프론트엔드 (stock-pred-v5)"]
        UI --> REC[REC 탭]
        REC --> Card[RecommendationCard]
        Card --> PBO[PBO Badge\n초록/노랑/빨강]
        Card --> Gauge[Advisor Gauge]
        Card --> Grade[Investment Grade]
        Snap --> Card
        Card -. API mode .-> API
    end

    subgraph Flows["Prefect 자동화"]
        KRX[daily_krx_flow\n16:30 KST] --> FT[forward_tracking_task]
        FT --> Ev[reports/live_review/]
    end

    Backend --> Flows
    Advisor -->|USE_MLFLOW_TRACING=true| MLF
```

### 데이터 제공자 및 감사 흐름

```mermaid
sequenceDiagram
    participant Op as 운영자
    participant CLI as recommend / ops-v1
    participant Prov as data_providers.py
    participant Audit as audit_log.jsonl
    participant Eng as RecommendationEngine

    Op->>CLI: universe, track, provider 선택
    CLI->>Prov: OHLCV 로드
    Prov->>Audit: provider 시도 이벤트 기록
    Prov-->>Eng: 정규화 OHLCV DataFrame
    Eng->>Eng: 팩터·모델·백테스트·리스크 평가
    Eng-->>Op: 추천 리포트 + 감사 경로
```

---

## 3. 데이터 계약 타입 맵

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

---

## 4. 최신 반영 요약

### 2026-05-30 — Executive Dashboard + NotebookLM 뉴스 연동

| 영역 | 최신 상태 |
|---|---|
| **Executive Dashboard v2.1** | `VITE_DASHBOARD_LAYOUT=executive` — 17개 컴포넌트, 자동 `/api/recommend` fetch |
| **NotebookLM 뉴스** | iran-war-notelm `:8088` API 연동 — `notebook_analysis`, `scenario_outlook` → AI Panel |
| **dashboard_bridge.py** | `notebook_analysis` passthrough + `scenario_outlook` fallback 자동 생성 |
| **advisors/notebooklm_news.py** | `fetch_notebooklm_analysis()` + `enrich_context_with_notebooklm()` 전면 재작성 |
| **테스트** | 116/116 passed (test_dashboard_bridge + test_risk_rules + test_reports) |

### 2026-05-29 GitHub main 상태

현재 `main`은 Wave 4 문서와 구현 반영분을 포함합니다. 이 섹션은 GitHub 첫 화면에서 최신 기능을 빠르게 확인하기 위한 요약입니다.

| 영역 | 최신 상태 |
|---|---|
| Dashboard REC | KRX 전체 데이터 표시, PBO Badge, LLM Advisor KRX 사용, 동일 in-flight REC 요청 dedupe |
| RD-Agent | `src/stock_rtx4060/factors/rd_agent/` Alpha Factory 패키지와 `factor-*` CLI 흐름 반영 |
| LLM Advisor | AMH memory, DuckDB L1/L2/L3 regime memory, STL proposition, OpenBB tool-use 구조 반영 |
| Readiness / Live Review | `new_capital_allowed=false`, `broker_order_execution=false`, `manual_approval_required=true` 불변 유지 |
| Docs | `CHANGELOG.md`, `docs/LAYOUT.md`, `docs/SYSTEM_ARCHITECTURE.md` 최신 구조 동기화 |

```mermaid
flowchart LR
    Main[GitHub main] --> Dashboard[Dashboard REC\nKRX + PBO + dedupe]
    Main --> RDAgent[RD-Agent Alpha Factory\nfactor-mine/list/approve/status]
    Main --> Advisor[LLM Advisor\nMemory + OpenBB tools]
    Main --> Readiness[Readiness / Live Review\nno capital, no broker]
    Main --> Docs[README + CHANGELOG\nLAYOUT + SYSTEM_ARCHITECTURE]
```

### Wave 3 / Wave 4 기능

### E1 — MLflow LLM Span Tracing

P6 어드바이저 호출을 MLflow에 기록합니다 (선택적).

```bash
export USE_MLFLOW_TRACING=true   # 기본값: false
mlflow server --host 127.0.0.1 --port 5000
# → http://127.0.0.1:5000 Traces 탭에서 advisor_call span 확인
```

| 항목 | 내용 |
|---|---|
| 구현 파일 | `src/stock_rtx4060/advisors/claude_client.py` |
| 환경변수 | `USE_MLFLOW_TRACING=true` |
| 메서드 | `_wrap_with_mlflow_span()` — LiteLLM/MiniMax/Anthropic 세 경로 래핑 |
| mlflow 버전 | `>=3.0,<4.0` |

### E2 — PBO 대시보드 통합

```mermaid
flowchart LR
    CPCV[CPCV 백테스트] --> PBO[pbo 계산\n0.0 ~ 1.0]
    PBO --> Gate{pbo_status}
    Gate -->|pbo ≤ 0.20| PASS[PASS 초록]
    Gate -->|0.20 < pbo ≤ 0.50| AMBER[AMBER 노랑]
    Gate -->|pbo > 0.50| RED[RED 빨강]
    Gate -->|미실행| ND[NO_DATA 회색]
    PASS --> Badge[REC 카드 PBO Badge]
    AMBER --> Badge
    RED --> Badge
    RED --> Down[readiness 강등\n반영금지]
    AMBER --> Down2[readiness 강등\n검토전용]
```

| 구현 파일 | 역할 |
|---|---|
| `backtest_honesty.py` | `_compute_pbo_status()` · `summarize_honesty()` pbo 집계 |
| `dashboard_bridge.py` | `_pbo_summary_for_card()` · per-candidate `backtest_honesty_summary` |
| `RecommendationCard.jsx` | `PboBadge` 컴포넌트 (WCAG AA) |

### E3 — AutoForwardRecorder Prefect 자동화

005930.KS 30일 실전 추적이 `daily_krx_flow`에서 매일 자동 실행됩니다.

```bash
# 비활성화
export FORWARD_TRACKING_ENABLED=false

# 수동 1회 기록
python -c "
from stock_rtx4060.live_review.auto_forward_recorder import AutoForwardRecorder
from pathlib import Path
r = AutoForwardRecorder(evidence_dir=Path('reports/live_review/005930'))
print(r.record_today())
"
```

### E4 — RD-Agent Alpha Factory (P2)

RD-Agent automates factor discovery via Docker subprocess.
Weekly cycle: `factor-mine` → `factor-list` → manual review → `factor-approve`.

#### Docker (Windows 필수 — WSL2)

RD-Agent는 Docker 컨테이너로 실행됩니다. Windows에서 사용시 **WSL2 백엔드 필수**.

```powershell
# WSL2 설치 확인 (PowerShell 관리자)
wsl --install
wsl --set-default-version 2

# Docker Desktop → Settings → General → "Use WSL2 instead of Hyper-V" 체크
# Docker 실행 확인
docker run hello-world
```

#### 환경변수

```bash
export RDAGENT_ENABLED=true
export RDAGENT_BUDGET_USD=10.0   # 사이클당 LLM 예산
export RDAGENT_CYCLES=2           # 발견 사이클 수
export RDAGENT_APPROVAL_REQUIRED=true  # true=수동 승인 (기본), false=자동 등록 (dev만)
```

#### 주간 팩터 마이닝 워크플로우

```bash
# 1단계: 팩터 마이닝 실행
PYTHONPATH=src python -m stock_rtx4060.main factor-mine --cycles 2 --budget-usd 10.0

# 2단계: 발견된 팩터 확인
PYTHONPATH=src python -m stock_rtx4060.main factor-list --status all

# 3단계: 팩터 검토 후 승인
PYTHONPATH=src python -m stock_rtx4060.main factor-approve --factor-id rd_momentum --run-date 2026-05-29

# 상태 확인
PYTHONPATH=src python -m stock_rtx4060.main factor-status
```

| 파일 | 역할 |
|---|---|
| `src/stock_rtx4060/factors/rd_agent/runner.py` | CLI 엔트리포인트 |
| `src/stock_rtx4060/factors/rd_agent/docker_runner.py` | Docker 서브프로세스 래퍼 |
| `src/stock_rtx4060/factors/rd_agent/qlib_exporter.py` | DuckDB → Qlib CSV/bin (PIT 가드) |
| `src/stock_rtx4060/factors/rd_agent/loader.py` | `.py` → Factor 인스턴스 동적 로드 |
| `src/stock_rtx4060/factors/rd_agent/provenance.py` | `audit_log/rd_agent.jsonl` JSONL 로깅 |
| `src/stock_rtx4060/factors/rd_agent/registry_hook.py` | validate → stage → approve → register |
| `src/stock_rtx4060/factors/rd_agent/validator.py` | IC/IR/상관관계/half-life 게이트 |

### E5 — Advisor Memory + OpenBB Tool Use

P6 어드바이저는 기본 동작을 유지하면서 선택 기능으로 메모리 검색과 OpenBB tool-use를 사용할 수 있습니다.

| 기능 | 기본값 | 구현 |
|---|---|---|
| AMH memory | 비활성 연결 기본 | `src/stock_rtx4060/advisors/memory/` |
| OpenBB tool-use | `OPENBB_TOOLS_ENABLED=false` | `src/stock_rtx4060/advisors/openbb_tools/` |
| backward compatibility | 유지 | `AdvisoryOutput.regime_label`, `logical_proposition` 기본값 `""` |

```bash
# OpenBB tool-use 활성화
export OPENBB_TOOLS_ENABLED=true
```

---

## 5. 빠른 시작

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901

# 1. 가상환경 설치
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 자가 진단
.\run.ps1 self-test

# 3. 합성 데이터로 추천 실행
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2

# 4. 대시보드 실행
.\.venv\Scripts\python.exe preview_server.py
# → http://127.0.0.1:5173
```

---

## 6. CLI 명령어

```bash
PYTHONPATH=.:src python main.py <command> [options]
```

| 명령어 | 설명 | 주요 출력 |
|---|---|---|
| `env` | 런타임·GPU 환경 확인 | `reports/runtime_status.json` |
| `benchmark` | CPU/GPU 벤치마크 | 벤치마크 Markdown/JSON |
| `report` | 일간 리포트 | Markdown/JSON |
| `recommend` | 추천 스캔 (Track-S/L) | 추천 Markdown/JSON · `audit_log.jsonl` |
| `backtest` | 백테스트 실행 | 백테스트 결과 |
| `ops-v1` | 수동 검토 워크플로우 패킷 | 승인 템플릿·ZERO 로그·요약 |
| `dashboard-export` | 추천 JSON → 대시보드 스냅샷 | `dashboard_snapshot.json` |
| `paper` | 페이퍼트레이딩 시뮬레이션 | 페이퍼 포지션 리포트 |
| `self-test` | 내부 스모크 테스트 | CLI PASS/FAIL |

---

## 7. 대시보드

### 구조

| 파일 | 역할 |
|---|---|
| `stock-pred-v5/src/StockPredV5.jsx` | 탭·상태·차트 메인 + Executive v2.1 레이아웃 (feature flag) |
| `stock-pred-v5/src/components/RecommendationCard.jsx` | 후보 카드 (PBO Badge 포함) |
| `stock-pred-v5/src/components/AiDecisionPanel.jsx` | AI 의사결정 패널 (LLM + NotebookLM + ActionPlan) |
| `stock-pred-v5/src/components/ScenarioOutlookPanel.jsx` | Bull/Base/Bear 시나리오 |
| `stock-pred-v5/src/components/` (17개) | Executive Dashboard v2.1 컴포넌트 전체 |
| `stock-pred-v5/public/dashboard_snapshot.json` | FILE 모드 스냅샷 |
| `stock-pred-v5/vite.config.js` | 포트 5173, `/api` → `:5151` 프록시 |

### Executive Dashboard 실행

```bash
# feature flag 설정 후 dev 서버 실행
VITE_DASHBOARD_LAYOUT=executive npx vite --port 5173

# 또는 빌드
VITE_DASHBOARD_LAYOUT=executive npm run build
```

종목 선택 시 `/api/recommend`가 자동 호출되어 AI Decision Panel이 실시간으로 채워집니다.

### 데이터 모드

```mermaid
flowchart TD
    REC[REC 탭] --> Mode{데이터 모드}
    Mode --> File[FILE 모드\npublic/dashboard_snapshot.json]
    Mode --> Api[API 모드\n/api/recommend → Flask :5151]
    File --> Cards[추천 카드]
    Api --> Cards
    Cards --> PBO[PBO Badge\npbo_status 뱃지]
    Cards --> Gauge[Advisor Gauge\nadvisory_score −1~+1]
    Cards --> Grade[Investment Grade\n반영금지/검토전용/조건부반영]
```

### 대시보드 export

```powershell
# 백엔드 추천 결과 → 대시보드 공개 디렉터리 복사
python main.py dashboard-export `
  --recommendation-json reports\recommendations\recommendations_algo_v2_*.json `
  --output reports\dashboard_public_export\dashboard_snapshot.json `
  --public-dir ..\stock-pred-v5\public
```

---

## 8. 일별 KRX 자동화 플로우

```mermaid
flowchart TD
    Start([16:30 KST Mon-Fri]) --> T1
    T1[1 ingest_kis_task\nKIS API 일봉 수집] --> T2
    T2[2 corp_actions_adjust_task\n분할·배당 역조정] --> T3
    T3[3 factor_compute_task\nAlpha101 팩터 계산] --> T4
    T4[4 model_predict_task\nMLflow 모델 추론] --> T5
    T5[5 portfolio_optimize_task\nHRP/CVaR 비중 최적화] --> T6
    T6[6 recommend_task\n추천 엔진 실행] --> T7
    T7[7 snapshot_dashboard_task\ndashboard_snapshot.v1 생성] --> T8
    T8[8 forward_tracking_task\nrecord_today 자동 기록] --> T9
    T9[9 alert_task\nSlack/Discord 알림]
    T9 --> End([완료])

    style T8 fill:#f0f9ff,stroke:#0ea5e9,color:#0369a1
```

> `FORWARD_TRACKING_ENABLED=false`로 T8 단계를 즉시 비활성화할 수 있습니다.

---

## 9. AutoForwardRecorder 상태 머신

```mermaid
stateDiagram-v2
    direction LR
    [*] --> FORWARD_PAPER_RUNNING : 초기 상태
    FORWARD_PAPER_RUNNING --> FORWARD_PAPER_RUNNING : 매 거래일\nrecord_today 호출
    FORWARD_PAPER_RUNNING --> SKIPPED : 비거래일 또는 장 마감 전
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

## 10. 투자 준비도 판정

```mermaid
flowchart LR
    subgraph Gates["통과 필요 게이트"]
        G1[CPCV pass rate ≥ 60%]
        G2[PBO ≤ 20%]
        G3[Deflated Sharpe > 0]
        G4[Forward Paper ≥ 30일]
        G5[Forward Alpha ≥ 0%]
        G6[Rule Violations = 0]
        G7[Model Card 존재]
    end

    Gates --> Verdict{판정}
    Verdict -->|모든 게이트 통과| LRC[LIVE_REVIEW_CANDIDATE]
    Verdict -->|핵심 게이트만 통과| PP[PAPER_PASS]
    Verdict -->|게이트 미달| AW[AMBER_WATCHLIST]

    LRC --> Grade1[조건부 반영 가능]
    PP --> Grade2[검토 전용]
    AW --> Grade3[반영 금지]
```

| 등급 | 의미 |
|---|---|
| `조건부 반영 가능` | 수동 투자 검토 가능 (매수/매도 명령 아님) |
| `검토 전용` | 증거 더 필요 또는 수동 판단 필요 |
| `반영 금지` | 이 후보를 투자 워크플로우에 사용하지 말 것 |

---

## 11. 안전 경계

| 경계 | 규칙 |
|---|---|
| 브로커 실행 | `--broker live-*` 플래그 + 명시적 사용자 승인 시에만 |
| 라이브 주문 | `status.get("reused")=True`이면 스킵 |
| API 키 | 절대 커밋 금지 — 환경변수 또는 `~/.config/stock_1901/` |
| LLM 어드바이저 | `advisory_score ∈ [-1,+1]`; RED/AMBER를 GREEN으로 승격 불가 |
| Kill Switch | `~/.cache/stock_1901/KILLED` 파일이 모든 라이브 주문 차단 |
| PIT as_of 가드 | 레이크 미스 + `as_of!=None` → `RuntimeError` (silent look-ahead 금지) |
| `screening_output_only` | 모든 `RecommendationResult`에 항상 `True` |

---

## 12. 테스트 및 CI

```bash
# 전체 테스트 스위트 (CI와 동일)
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 --tb=short -rfE -q

# 타입 검사 (non-blocking)
mypy src/stock_rtx4060/observability || true

# CLI 불변 검사
PYTHONPATH=.:src python main.py recommend --help
PYTHONPATH=.:src python main.py backtest --help
PYTHONPATH=.:src python main.py paper --help
```

| 게이트 | 조건 |
|---|---|
| `pytest --cov-fail-under=75` | 전체 통과, 커버리지 ≥75% |
| `dashboard_snapshot.v1` | `schema_version` 필드 존재 |
| `screening_output_only` | 모든 결과에 `True` |
| `PurgedKFold groups` | `cv.split()` 시 항상 `groups=` 전달 |
| numpy 버전 | `>=1.26,<3.0` |
| shap 버전 | `>=0.50.0` |

**현재 커버리지:** ~87% (line · branch)

---

## 13. 모듈 구성 (P0–P8)

| 페이즈 | 영역 | 핵심 모듈 |
|---|---|---|
| P0 | 관찰가능성·CI | `src/stock_rtx4060/observability/` · `.github/workflows/ci.yml` |
| P1 | PIT 데이터 레이크 | `src/stock_rtx4060/data_lake/` (DuckDB 1.5.3 + Parquet) |
| P2 | 팩터 라이브러리 | `src/stock_rtx4060/factors/` (Alpha101/158, Barra) |
| P3 | ML 업그레이드 | `src/stock_rtx4060/ml/` (LightGBM, Optuna HPO, MLflow) |
| P4 | 포트폴리오 최적화 | `src/stock_rtx4060/portfolio/` (skfolio HRP/NCO/CVaR) |
| P5 | 백테스트 | `src/stock_rtx4060/backtest/` (vectorbt, MC bootstrap, CPCV/PBO) |
| P6 | LLM 어드바이저 | `src/stock_rtx4060/advisors/` (LiteLLM, MLflow tracing) |
| P7 | 오케스트레이션 | `flows/` (Prefect 3 · daily_krx · daily_us · research_weekly) |
| P8 | 라이브 브로커 | `src/stock_rtx4060/broker/` (Alpaca · IBKR · KIS) |

---

## 14. 출력 파일 위치

| 출력 | 위치 |
|---|---|
| 추천 Markdown/JSON | `reports/recommendations*/` |
| Provider 감사 로그 | `reports/**/audit_log.jsonl` |
| MLflow 어드바이저 trace | `audit_log/advisor.jsonl` |
| 대시보드 스냅샷 | `dashboard_snapshot.json` (dashboard-export 명령) |
| forward tracking CSV | `reports/live_review/005930KS/paper_trading_log_005930KS.csv` |
| 대시보드 빌드 | `stock-pred-v5/dist/` |

---

## 15. 알려진 이슈 및 워크어라운드

| 이슈 | 워크어라운드 |
|---|---|
| `logging.basicConfig(force=True)`의 글로벌 `InterceptHandler` | `configure_logging()` 호출 테스트에서 `monkeypatch.setattr(logging, "basicConfig", lambda **kw: None)` 사용 |
| Python 3.14에서 `.corr().values` numpy read-only | `np.fill_diagonal()` 전에 `.copy()` 추가 — `portfolio/optimizer.py` 참고 |
| Pandas 4.x `pd.Timestamp.utcnow()` deprecated | `pd.Timestamp.now('UTC')` 사용 — `data_providers.py`, `recommendation_engine.py` 패치됨 |
| `_TorchLSTMNet` · `LSTMPredictor` · `GRUPredictor` CI 미커버 | `torch` 미설치 CI 환경 — `# pragma: no cover` 처리됨 |
| `reports.py` 커버리지 0% | `reports/` 패키지에 가려진 dead code — `pyproject.toml` omit 처리됨 |
| 이중 api_server 프로세스 (포트 5151 점거) | 구버전 Python 3.12 프로세스가 5151에 남아 수정 코드가 실행 안 됨 — `Get-NetTCPConnection -LocalPort 5151`로 PID 확인 후 `Stop-Process -Force` |
| KRX REC 로딩 타임아웃 | `period=5y` + 9개 종목 → Vite 프록시 초과 — `dashboard_config.json`의 `api_defaults.recommend_krx.period=3y`로 완화하고, KRX 전체 9개 종목은 `top=9`로 유지됨 |
| PBO badge 미표시 (CPCV 미실행) | `api_server.py`의 `cv_gap` 기본값을 5로 변경 완료. fold AUC proxy PBO 계산으로 `pbo_status` 채워짐 |

---

## 최근 변경 이력

| 날짜 | 커밋 | 내용 |
|---|---|---|
| 2026-05-30 | `c7af7fe` | docs: LAYOUT/COMPONENT_LAYOUT/SYSTEM_ARCHITECTURE 업데이트 |
| 2026-05-30 | `5c68df3` | feat(dashboard): Executive Decision Dashboard v2.1 — 17 components + feature flag |
| 2026-05-30 | `a212616` | feat(P6/NotebookLM): stock news intelligence layer + Thompson Sampling MAB + iran-war-notelm API |
| 2026-05-29 | `58a8018` | RD-Agent 문서, `research_weekly_flow` 보조 태스크, `pyqlib` optional requirement 정리 |
| 2026-05-29 | `e061b2a` | Advisor AMH memory와 OpenBB tool-use 추가 |
| 2026-05-29 | `8f6b030` | RD-Agent Alpha Factory 코드와 테스트 추가 |
| 2026-05-29 | `db2dea0` | REC 동일 in-flight 요청 dedupe 추가 |
| 2026-05-29 | `9c92917` | 루트 문서 inventory append 갱신 |
| 2026-05-29 | `fd24364` | E2: PBO badge end-to-end (fold AUC proxy PBO + RecommendationCard.jsx PboBadge) |
| 2026-05-29 | `f5570dd` | Dashboard: LLM Advisor KRX 제한 3곳 제거 |
| 2026-05-29 | `9664ca5` | Dashboard: XGBoost secondary score + LSTM/RNN null 숨김 + cv_gap=5 |
| 2026-05-29 | `ba4e81b` | E1-W3: MLflow LLM span tracing (`_USE_MLFLOW_TRACING` flag) |
| 2026-05-29 | `87047c3` | E3: `forward_tracking_task` + `record_today()` Prefect 자동화 |
| 2026-05-29 | `e485e1b` | 커버리지 ~83%→~87% (pragma + omit + 9개 테스트) |
| 2026-05-29 | `6909d0a` | mlflow `>=3.0,<4.0` requirements 동기화 |
| 2026-05-29 | `d746254` | E2: PBO 대시보드 갭 수정 (summarize_honesty + bridge) |
| 2026-05-11 | `26451eb` | P0: TimeSeriesSplit→PurgedKFold, API universe cap |
| 2026-05-10 | `717f3a0` | 커버리지 78.5%→85.82%, CORS 수정 |


## Codex Documentation Update — 2026-05-29T10:35:18.105307+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`
- `main.py`
- `preview_server.py`
- `reports\dashboard_browser_verification\snapshot_fixture.js`

**Documentation files sampled:**
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\root-docs-strict\docs\001-README.md`
- `.codex\root-docs-strict\docs\002-SYSTEM_ARCHITECTURE.md`
- `.codex\root-docs-strict\docs\003-LAYOUT.md`
- `.codex\root-docs-strict\docs\004-CHANGELOG.md`
- `.codex\root-docs-strict\docs\005-plan.md`
- `.codex\root-docs-strict\docs\006-codex-default-doc-agent.md`
- `.continue\checks\01-financial-safety-boundary.md`
- `.continue\checks\02-backtest-integrity.md`
- `.continue\checks\03-recommendation-contract.md`
- `.continue\checks\04-secret-and-pii-safety.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\root-docs-dry-run-latest.json`
- `.codex\root-docs-dry-run.json`
- `.codex\root-docs-scan-latest.json`
- `.codex\root-docs-scan.json`
- `.codex\root-docs-verify-latest.json`
- `.codex\root-docs-verify.json`
- `.codex\root-docs-write.json`
- `.github\workflows\ci.yml`
- `.hermes\root-docs-dry-run.json`
- `.hermes\root-docs-scan.json`
- `.hermes\root-docs-write.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2361, docs=1249, config=850, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## Codex Documentation Update — 2026-05-29T12:01:03.736036+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`
- `main.py`
- `preview_server.py`
- `reports\dashboard_browser_verification\snapshot_fixture.js`

**Documentation files sampled:**
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154237.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154543.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\dashboard_live_verify\final_endpoint_summary.json`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.json`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.json`
- `.codex\dashboard_live_verify\krx_after_cache_fix_response.json`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.json`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix_response.json`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.json`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.json`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix_response.json`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.json`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2393, docs=1302, config=903, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## Codex Documentation Update — 2026-05-29T12:28:54.428371+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`
- `main.py`
- `preview_server.py`
- `reports\dashboard_browser_verification\snapshot_fixture.js`

**Documentation files sampled:**
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154237.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154543.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\dashboard_live_verify\final_endpoint_summary.json`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.json`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.json`
- `.codex\dashboard_live_verify\krx_after_cache_fix_response.json`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.json`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix_response.json`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.json`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.json`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix_response.json`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.json`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2393, docs=1310, config=908, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## Codex Documentation Update — 2026-05-29T16:09:34.633357+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `.codex\dashboard_cmrs_actual_backend_verify\run_debug.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify_same_origin.js`
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`

**Documentation files sampled:**
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.md`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.md`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\api_recommend_cmrs_actual\direct_api_response_5162.json`
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.json`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.json`
- `.codex\changelog_dashboard_cross_verify\dashboard_krx_rec_models_cross_verify.json`
- `.codex\current_api_recommend_krx.json`
- `.codex\current_api_recommend_krx_5161.json`
- `.codex\current_api_recommend_krx_universe.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend-debug.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.json`
- `.codex\dashboard_cmrs_sizing_verify\rec-card-cmrs-sizing.json`
- `.codex\dashboard_cmrs_toggle_verify\cmrs-toggle-evidence.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2409, docs=1366, config=974, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## Codex Documentation Update — 2026-05-29T16:47:47.339618+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `.codex\dashboard_cmrs_actual_backend_verify\run_debug.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify_same_origin.js`
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`

**Documentation files sampled:**
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.md`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.md`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\api_recommend_cmrs_actual\direct_api_response_5162.json`
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.json`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.json`
- `.codex\changelog_dashboard_cross_verify\dashboard_krx_rec_models_cross_verify.json`
- `.codex\current_api_recommend_krx.json`
- `.codex\current_api_recommend_krx_5161.json`
- `.codex\current_api_recommend_krx_universe.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend-debug.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.json`
- `.codex\dashboard_cmrs_sizing_verify\rec-card-cmrs-sizing.json`
- `.codex\dashboard_cmrs_toggle_verify\cmrs-toggle-evidence.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2410, docs=1394, config=1002, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## README Update — CMRS Actual Backend Verification — 2026-05-29

This section records the latest verified dashboard behavior for optional CMRS sizing. The feature remains report-only and downgrade-only. It does not enable broker execution or new capital.

### Verified Runtime Path

- API server: `http://127.0.0.1:5162`
- Dashboard page: `http://127.0.0.1:5162/`
- Live endpoint: `/api/recommend?sizing_kind=auto&sizing_alpha=0.1&sizing_n_min=30`
- Data provider observed: `yfinance`
- Provider status observed: `PASS`
- Invalid input check: `sizing_kind=bad` returned HTTP `400`

### Observed CMRS Result

The real API calculation returned CMRS fields in the dashboard snapshot. The first displayed result showed:

- `raw_score=100`
- `score=0`
- `size_multiplier=0`
- `sizing_strategy_used=auto->mondrian`
- `sizing_coverage_status=PASS`
- `screening_output_only=true`
- `new_capital_allowed=false`
- `broker_order_execution=false`

The score was reduced from the raw score to the displayed ranking score. CMRS did not upgrade a verdict.

### Dashboard Evidence

- Backend response: `.codex\api_recommend_cmrs_actual\direct_api_response_5162.json`
- Backend recommendation artifact: `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.json`
- Dashboard verification report: `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.json`
- Dashboard screenshot: `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.png`

### CMRS Request Flow

```mermaid
flowchart LR
  Toggle[REC CMRS SIZING toggle] --> Request[/api/recommend sizing_kind=auto/]
  Request --> Engine[RecommendationEngine]
  Engine --> Sizer[CMRS AutoSizingRouter]
  Sizer --> Snapshot[Dashboard snapshot fields]
  Snapshot --> Card[RecommendationCard SIZE SIZER COVERAGE]
  Sizer --> Safety[screening only no broker execution]
```

### Operational Note

Keep `sizing_kind=off` as the default. Enable `auto`, `global`, or `mondrian` only for explicit research or dashboard review runs. Missing calibration data must degrade to `size_multiplier=0.0` and `sizing_coverage_status=NO_DATA`.


## Codex Documentation Update — 2026-05-29T17:01:44.330543+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `.codex\dashboard_cmrs_actual_backend_verify\run_debug.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify_same_origin.js`
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`

**Documentation files sampled:**
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.md`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.md`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\api_recommend_cmrs_actual\direct_api_response_5162.json`
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.json`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.json`
- `.codex\changelog_dashboard_cross_verify\dashboard_krx_rec_models_cross_verify.json`
- `.codex\current_api_recommend_krx.json`
- `.codex\current_api_recommend_krx_5161.json`
- `.codex\current_api_recommend_krx_universe.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend-debug.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.json`
- `.codex\dashboard_cmrs_sizing_verify\rec-card-cmrs-sizing.json`
- `.codex\dashboard_cmrs_toggle_verify\cmrs-toggle-evidence.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2410, docs=1405, config=1015, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.


## Codex Documentation Update — 2026-05-29T18:56:03.316404+00:00

**Update policy:** existing content above this section is preserved. This section was appended after scanning code, documentation, config, and agent profile files.

**Purpose:** This section summarizes the repository state for onboarding and operation.

### Evidence inventory

**Source/code files sampled:**
- `.codex\dashboard_cmrs_actual_backend_verify\run_debug.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify.js`
- `.codex\dashboard_cmrs_actual_backend_verify\run_verify_same_origin.js`
- `api_server.py`
- `dashboard\stock_pred_v5.jsx`
- `docs\purged_kfold_embargo.py`
- `docs\test_purged_kfold_embargo.py`
- `flows\__init__.py`
- `flows\daily_krx.py`
- `flows\daily_us.py`
- `flows\research_weekly.py`
- `flows\utils.py`

**Documentation files sampled:**
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.md`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.md`
- `.codex\dashboard_live_verify\krx\recommendations_algo_v2_20260529_145024.md`
- `.codex\dashboard_live_verify\krx_after_cache_fix\recommendations_algo_v2_20260529_150920.md`
- `.codex\dashboard_live_verify\krx_after_provider_validation_fix\recommendations_algo_v2_20260529_151147.md`
- `.codex\dashboard_live_verify\us\recommendations_algo_v2_20260529_144953.md`
- `.codex\dashboard_live_verify\us_after_provider_validation_fix\recommendations_algo_v2_20260529_151825.md`
- `.codex\goals\dashboard-report-bridge.goal.md`
- `.codex\goals\mcp-openbb-audit-phase1.goal.md`
- `.codex\llm_advisor_dashboard_before_lines.txt`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154221.md`
- `.codex\llm_advisor_dashboard_live_ui\recommendations_algo_v2_20260529_154236.md`

**Config/build files sampled:**
- `.claude\launch.json`
- `.codex\api_recommend_cmrs_actual\direct_api_response_5162.json`
- `.codex\api_recommend_cmrs_actual\recommendations_algo_v2_20260529_194503.json`
- `.codex\api_recommend_krx_5161\recommendations_algo_v2_20260529_165852.json`
- `.codex\changelog_dashboard_cross_verify\dashboard_krx_rec_models_cross_verify.json`
- `.codex\current_api_recommend_krx.json`
- `.codex\current_api_recommend_krx_5161.json`
- `.codex\current_api_recommend_krx_universe.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend-debug.json`
- `.codex\dashboard_cmrs_actual_backend_verify\dashboard-rec-cmrs-actual-backend.json`
- `.codex\dashboard_cmrs_sizing_verify\rec-card-cmrs-sizing.json`
- `.codex\dashboard_cmrs_toggle_verify\cmrs-toggle-evidence.json`

**Agent profile files sampled:**
- `docs\agents\codex-default-doc-agent.md` (`codex-default-doc-agent`)

### Mermaid graph

```mermaid
flowchart LR
  C[Code inventory] --> D[Root docs]
  A[Agent profiles] --> D
  D --> V[Verification report]
```

### Verification notes

- Append-only update generated by `root-docs-batch-update`.
- Code/config/doc/agent inventory counts: code=2417, docs=1446, config=1053, agent_profiles=1.
- Follow-up verification should confirm that newly added text matches actual implementation paths listed above.
