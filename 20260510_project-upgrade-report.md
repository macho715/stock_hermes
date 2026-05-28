# Project Upgrade Report — stock_1901 Dashboard
**날짜**: 2026-05-10 | **스킬**: project-upgrade v2.1 | **요청**: 헤지펀드 수준 대시보드 업그레이드 벤치마크

---

## Executive Summary

현재 `stock_1901` 대시보드는 **스크리닝 레벨(투자 아이디어 발굴)** 단계이며, 실제 매매 실행은 `screening_output_only=True` 불변 가드로 차단되어 있다. ML 백엔드(LightGBM·XGBoost·Logistic·LSTM), PurgedKFold CV, 백테스트(vectorbt+MC bootstrap), LLM 어드바이저(Claude), Prefect 플로우까지 헤지펀드급 분석 엔진을 갖추고 있으나, **프론트엔드 대시보드가 이 분석력을 충분히 전달하지 못하고 있다**. 핵심 격차: ① WebSocket 실시간 없음, ② 포트폴리오 리스크 메트릭(VaR/CVaR/Sharpe/드로우다운) 미표시, ③ SHAP 팩터 귀속 시각화 없음, ④ 멀티-심볼 비교 패널 없음, ⑤ 체제(Regime) 감지 결과 미노출.

---

## Current State Snapshot

| 영역 | 현 상태 | 갭 |
|---|---|---|
| **프론트엔드** | React/Vite, Recharts, 단일 JSX 컴포넌트 (~800줄) | 모듈화 미흡, 실시간 없음 |
| **백엔드 API** | Flask REST 7개 엔드포인트 (:5151) | WebSocket 없음, 캐싱 없음 |
| **데이터 표시** | OHLCV 차트 + 모델 점수(BUY/HOLD/SELL) | 리스크 메트릭, SHAP, 포트폴리오 뷰 없음 |
| **모델 근거** | 앙상블 점수 숫자 표시 | SHAP waterfall/beeswarm 없음 |
| **백테스트** | Sharpe/MDD/Sortino 필드 존재 (API 노출) | 대시보드에서 시각화 없음 |
| **포트폴리오** | skfolio HRP/NCO/CVaR 백엔드 존재 | 대시보드 연결 없음 |
| **어드바이저** | Claude 어드바이저 점수 필드 존재 | 패널에서 미노출 (텍스트 미표시) |
| **알림** | Slack/Discord 채널 존재 | 대시보드 알림 배너 없음 |
| **인증/접근 제어** | 없음 | 운영 환경 시 필수 |
| **Regime 감지** | macro_regime.py 존재 | 대시보드 시각화 없음 |

---

## Upgrade Ideas Top 10

| # | 아이디어 | 버킷 | Impact | Effort | Risk | Confidence | PriorityScore | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | **실시간 WebSocket 스트리밍** | Performance | 5 | 3 | 2 | 4 | 3.33 | [①②] |
| 2 | **리스크 메트릭 패널** (VaR/CVaR/Sharpe/MDD) | Reliability | 5 | 2 | 1 | 5 | 12.5 | [③④] |
| 3 | **SHAP 팩터 귀속 시각화** | Architecture | 4 | 2 | 1 | 5 | 10.0 | [⑤] |
| 4 | **멀티-심볼 Heat Map** | DX/Tooling | 4 | 2 | 1 | 4 | 8.0 | [①] |
| 5 | **Regime/체제 감지 패널** | Architecture | 5 | 3 | 2 | 4 | 3.33 | [⑥] |
| 6 | **LLM 어드바이저 근거 패널** | DX/Tooling | 4 | 1 | 1 | 5 | 20.0 | [⑦] |
| 7 | **포트폴리오 최적화 뷰** (HRP Efficient Frontier) | Architecture | 5 | 4 | 2 | 3 | 1.875 | [④] |
| 8 | **알림/Alert 배너** (실시간 임계값 경보) | Reliability | 4 | 2 | 1 | 4 | 8.0 | [③] |
| 9 | **대시보드 인증 레이어** (JWT/OAuth) | Security | 4 | 3 | 2 | 5 | 3.33 | [②] |
| 10 | **대시보드 컴포넌트 분리** (모듈화 리팩터) | DX/Tooling | 3 | 2 | 1 | 5 | 7.5 | [①②] |

> **PriorityScore** = (Impact × Confidence) / (Effort × Risk). #6 LLM 어드바이저 패널이 20.0으로 최고 — 이미 백엔드에 데이터 있고 프론트 노출만 없음.

---

## Best 3 Deep Report

### Best 1 — LLM 어드바이저 근거 패널 (PriorityScore 20.0)

> **이유**: 백엔드 `advisor_score`, `advisor_rationale` 필드가 이미 `dashboard_snapshot.v1` 스키마에 존재하나 프론트엔드에서 전혀 표시되지 않는다. 가장 작은 공수로 최대 정보 밀도 향상 가능.

#### Goal
- 각 추천 종목 카드에 Claude 어드바이저 점수(–1~+1)와 근거 텍스트(240자 클립) 표시
- GREEN/AMBER/RED 게이트 표시 (어드바이저는 GREEN→AMBER 다운그레이드만 가능)
- LLM 스코어가 없는 경우(`None`) 빈 섹션 graceful 처리

#### Non-goals
- 어드바이저가 GREEN 추천을 업그레이드하거나 주문 실행하는 것 (금지됨)
- 실시간 LLM 호출 (배치 결과만 표시)

#### Proposed Design

```
dashboard_snapshot.v1.results[n]
  ├── advisor_score: float | null      (이미 존재)
  ├── advisor_rationale: str | null    (이미 존재, 240자 클립됨)
  └── verdict: "GREEN" | "AMBER" | "RED"

프론트 컴포넌트:
  ResultCard
    └── AdvisorOverlay (신규)
          ├── ScoreBadge: [-1.0 ~ +1.0] 게이지
          ├── VerdictGate: 아이콘 (GREEN=✓, AMBER=⚠, RED=✗)
          └── RationaleText: 최대 3줄, 말줄임표
```

#### PR Plan

| PR | 범위 | 파일 | 롤백 |
|---|---|---|---|
| PR-1 | `AdvisorOverlay` 컴포넌트 신규 + 단위 테스트 | `dashboard/AdvisorOverlay.jsx`, `tests/test_advisor_panel.test.js` | 컴포넌트 삭제 |
| PR-2 | `ResultCard`에 `AdvisorOverlay` 마운트 + 조건부 렌더 | `dashboard/ResultCard.jsx` | 컴포넌트 언마운트 |
| PR-3 | FILE/API 모드 양쪽 E2E 검증 + 스냅샷 테스트 | `tests/e2e/advisor_panel.test.js` | 테스트 롤백 |

#### Tests
- 단위: `advisor_score=null` 시 패널 미표시, `-1.0/0.0/+1.0` 게이지 경계값
- 통합: FILE 모드 스냅샷 JSON → 어드바이저 패널 렌더링
- E2E: `npm run dev` → 대시보드 → 어드바이저 점수 텍스트 확인

#### KPI Targets
| 메트릭 | 현재 | 목표 |
|---|---|---|
| 대시보드 정보 밀도 (필드 수) | ~15/종목 | ~20/종목 |
| 어드바이저 점수 가시성 | 0% | 100% |
| 사용자 신뢰도 점수 (내부) | N/A | ≥4/5 |

#### Evidence
1. **platform**: official · **title**: `advisor_score` in `dashboard_bridge.py:266` · **date**: 2026-05-10 · **why**: 필드 이미 존재
2. **platform**: github · **title**: "Building High-Performance Trading Dashboards in 2026" · **url**: https://openwebsolutions.in/blog/high-performance-trading-dashboard-react-websockets/ · **date**: 2026 · **why**: 정보 밀도 + 신뢰도 향상이 핵심 가치

---

### Best 2 — 리스크 메트릭 패널 (VaR/CVaR/Sharpe/MDD) (PriorityScore 12.5)

> **이유**: `dashboard_snapshot.v1` 결과에 `backtest_sharpe`, `backtest_mdd_pct`, `backtest_sortino`, `backtest_return_pct` 가 이미 존재. P4(`portfolio/optimizer.py`)와 P5(`backtest/`) 모듈에 VaR/CVaR 계산이 있으나 API 미노출 상태. 헤지펀드 수준 진단의 핵심.

#### Goal
- 각 추천 종목에 대한 리스크 요약 카드: Sharpe / Sortino / Max Drawdown / Return %
- 포트폴리오 전체에 대한 VaR(95%) / CVaR(95%) 집계 표시
- 색상 코드: Sharpe ≥2.0=GREEN, 1.0~2.0=AMBER, <1.0=RED

#### Non-goals
- 실시간 리스크 재계산 (배치 백테스트 결과 기반)
- IBKR/Alpaca 라이브 포트폴리오 연결 (P8 범위)

#### Proposed Design

**신규 Flask 엔드포인트** `/api/risk-metrics?symbols=AAPL,MSFT&period=3y`:
```python
{
  "schema_version": "risk_metrics.v1",
  "symbols": [...],
  "portfolio_var_95": float,
  "portfolio_cvar_95": float,
  "per_symbol": [
    {
      "ticker": str,
      "sharpe": float,
      "sortino": float,
      "max_drawdown_pct": float,
      "cagr_pct": float,
      "profit_factor": float
    }
  ]
}
```

**프론트엔드 컴포넌트**:
```
RiskMetricsPanel (신규)
  ├── PortfolioVaRCard: 95% VaR / CVaR 게이지
  ├── SharpeSortino 테이블: 색상 코드
  └── DrawdownMiniChart: sparkline (Recharts Area)
```

#### PR Plan

| PR | 범위 | 파일 | 롤백 |
|---|---|---|---|
| PR-1 | `/api/risk-metrics` Flask 엔드포인트 | `api_server.py` | 엔드포인트 제거 |
| PR-2 | `RiskMetricsPanel` 컴포넌트 | `dashboard/RiskMetricsPanel.jsx` | 컴포넌트 삭제 |
| PR-3 | CORS 확장 + API 연결 + 테스트 | `api_server.py`, `tests/test_risk_metrics.py` | 설정 되돌리기 |
| PR-4 | FILE 모드 스냅샷에 `risk_metrics` 블록 추가 (additive) | `dashboard_bridge.py` | 필드 제거 |

#### Tests
- 단위: `backtest_sharpe=None` graceful, VaR 계산 수치 정확도
- 통합: `RecommendationEngine` → `risk_metrics.v1` JSON 포함 확인
- 회귀: `build_dashboard_snapshot` `schema_version="dashboard_snapshot.v1"` 불변 확인

#### KPI Targets
| 메트릭 | 현재 | 목표 |
|---|---|---|
| 리스크 메트릭 가시성 | 0% | 100% |
| Sharpe 기반 경보 | 없음 | Sharpe<1.0 자동 AMBER 게이트 |
| VaR 표시 정확도 | N/A | 95% 신뢰구간 히스토리컬 방법론 |

#### Evidence
1. **platform**: official · **title**: Genesis Risk Monitor — "VaR, CVaR, Beta, Sharpe, Max Drawdown in one dashboard" · **url**: https://genesis-rm.com · **date**: 2026 · **why**: 헤지펀드급 리스크 대시보드 레퍼런스 아키텍처
2. **platform**: official · **title**: `backtest_sharpe`, `backtest_mdd_pct` in `dashboard_bridge.py:245-247` · **date**: 2026-05-10 · **why**: 데이터 이미 백엔드에 존재

---

### Best 3 — SHAP 팩터 귀속 시각화 (PriorityScore 10.0)

> **이유**: `EnsemblePredictor`가 이미 SHAP 값을 계산하며 `ensemble_model.py`에 shap dependency가 존재. 이를 API로 노출하고 프론트에서 waterfall 차트로 표시하면 "왜 BUY인가"에 대한 해석 가능성(explainability)을 헤지펀드 수준으로 끌어올릴 수 있다.

#### Goal
- `/api/model-scores` 응답에 `shap_top_features` (상위 10개 피처 + SHAP 값) 추가
- 대시보드에 SHAP waterfall / horizontal bar 차트 표시
- 피처 이름 → 가독성 레이블 매핑 (RSI_14 → "RSI(14)", SMA_20_pct → "MA(20) 편차")

#### Non-goals
- 전체 학습셋 beeswarm plot (성능 이유로 배제)
- 실시간 SHAP 재계산 (요청별 배치만)

#### Proposed Design

```python
# api_server.py /api/model-scores 응답 추가 필드
"shap_features": [
  {"feature": "RSI_14", "shap_value": 0.34, "label": "RSI(14)"},
  {"feature": "SMA_20_pct", "shap_value": -0.21, "label": "MA(20) 편차"},
  ...  # top 10
]
```

```jsx
// SHAPPanel.jsx
<HorizontalBarChart>
  {shapFeatures.map(f => (
    <Bar fill={f.shap_value > 0 ? C.buy : C.sell}
         value={f.shap_value} label={f.label} />
  ))}
</HorizontalBarChart>
```

#### PR Plan

| PR | 범위 | 파일 | 롤백 |
|---|---|---|---|
| PR-1 | `EnsemblePredictor.get_shap_top_n()` 메서드 | `ensemble_model.py` | 메서드 제거 |
| PR-2 | `/api/model-scores` 응답에 `shap_features` 추가 | `api_server.py` | 필드 제거 |
| PR-3 | `SHAPPanel` 컴포넌트 + 단위 테스트 | `dashboard/SHAPPanel.jsx` | 컴포넌트 삭제 |

#### Tests
- 단위: SHAP 없을 때 graceful (lite=True 모드), top-10 정렬 검증
- 통합: `EnsemblePredictor.fit()` → `get_shap_top_n()` → API 응답 확인
- 시각: 양수/음수 바 색상 검증

#### KPI Targets
| 메트릭 | 현재 | 목표 |
|---|---|---|
| 모델 해석 가능성 | 점수만 | SHAP top-10 시각화 |
| 신호 설명 클릭률 | N/A | ≥60% 사용자 탐색 |
| SHAP 응답 지연 | N/A | <3초 (lite 모드) |

#### Evidence
1. **platform**: official · **title**: SHAP docs — "Census income classification with LightGBM" · **url**: https://shap.readthedocs.io/en/latest/ · **date**: 2025 · **why**: SHAP Tree Explainer가 LightGBM에 이미 통합됨
2. **platform**: official · **title**: `shap>=0.50.0` in CLAUDE.md dependency rules · **date**: 2026-05-10 · **why**: 의존성 이미 설치됨

---

## Options A / B / C

| 옵션 | 범위 | 기간 | 리스크 |
|---|---|---|---|
| **A (보수)** | Best 1만 구현 (LLM 어드바이저 패널) — 2 PR | 1~2일 | 낮음 — 기존 데이터 필드 노출만 |
| **B (중간, 권장)** | Best 1 + Best 2 + Best 3 — 10 PR | 1~2주 | 중간 — Flask 엔드포인트 추가, schema additive |
| **C (공격)** | 위 + WebSocket 실시간 + Regime 패널 + 인증 레이어 | 3~4주 | 높음 — 아키텍처 변경, 인증 도입 |

---

## 30 / 60 / 90-day Roadmap

### 30일 (Sprint 1) — 즉각 가시성 향상
- [ ] **D+2**: Best 1 — `AdvisorOverlay` 컴포넌트 (PR-1, PR-2)
- [ ] **D+5**: Best 1 — E2E 테스트 + 병합 (PR-3)
- [ ] **D+8**: Best 2 — `/api/risk-metrics` Flask 엔드포인트 (PR-1)
- [ ] **D+12**: Best 2 — `RiskMetricsPanel` 컴포넌트 (PR-2, PR-3)
- [ ] **D+15**: Best 3 — `get_shap_top_n()` + API 노출 (PR-1, PR-2)

### 60일 (Sprint 2) — 헤지펀드 핵심 기능
- [ ] **D+20**: Best 3 — `SHAPPanel` 컴포넌트 (PR-3)
- [ ] **D+25**: Best 4 — 멀티-심볼 Heat Map
- [ ] **D+35**: Best 5 — Regime/체제 감지 패널 (`macro_regime.py` 연결)
- [ ] **D+45**: Best 8 — 알림/Alert 배너

### 90일 (Sprint 3) — 운영 견고성
- [ ] **D+55**: Best 9 — 인증 레이어 (JWT/OAuth)
- [ ] **D+65**: Best 1-5 — WebSocket 실시간 스트리밍
- [ ] **D+75**: 포트폴리오 최적화 뷰 (HRP Efficient Frontier)
- [ ] **D+85**: 전체 통합 테스트 + 문서 업데이트

---

## Evidence Table

| ID | Platform | Title | URL | Published | Accessed | Relevance |
|---|---|---|---|---|---|---|
| ① | official/web | "Building High-Performance Trading Dashboards in 2026" | https://openwebsolutions.in/blog/high-performance-trading-dashboard-react-websockets/ | 2026 | 2026-05-10 | WebSocket + React 아키텍처 패턴 |
| ② | official | Flask-SocketIO docs | https://flask-socketio.readthedocs.io/ | 2025 | 2026-05-10 | WebSocket 백엔드 구현 |
| ③ | official | MetricStream Risk Dashboard Guide | https://www.metricstream.com/learn/risk-management-dashboard.html | 2025 | 2026-05-10 | 리스크 대시보드 설계 원칙 |
| ④ | official | Genesis Risk Monitor | https://genesis-rm.com | 2026 | 2026-05-10 | 헤지펀드급 VaR/CVaR 대시보드 참조 |
| ⑤ | official | SHAP + LightGBM docs | https://shap.readthedocs.io/en/latest/ | 2025 | 2026-05-10 | SHAP Tree Explainer LightGBM 통합 |
| ⑥ | research | Alpha Architect Regime Detection | https://alphaarchitect.com/regime-detection/ | 2025 | 2026-05-10 | 팩터 타이밍 + 체제 감지 투자 가치 |
| ⑦ | codebase | `advisor_score` in dashboard_bridge.py:266 | 내부 | 2026-05-10 | 2026-05-10 | 어드바이저 데이터 이미 존재 |

---

## AMBER_BUCKET (날짜 불명확 / 근거 부족)

| 아이디어 | 이유 |
|---|---|
| Bloomberg API 연동 | 라이선스 비용 불명확, 공개 날짜 없음 |
| AI 에이전트 자율 매매 | 안전 경계(`screening_output_only`) 위반 가능성 |
| IBKR 라이브 포트폴리오 실시간 PnL | P8 범위, 외부 인증 필요 |

---

## Verification Gate

### Evidence Completeness
| 항목 | 상태 |
|---|---|
| Best 3 각 evidence ≥2개 | ✅ PASS |
| 모든 evidence 날짜 명시 | ✅ PASS |
| 백엔드 데이터 필드 존재 확인 | ✅ PASS (`dashboard_bridge.py` 직접 확인) |

### Deep Dive Completeness
| 항목 | 상태 |
|---|---|
| PR plan ≥3개 | ✅ PASS |
| 테스트 계획 | ✅ PASS |
| 롤백 계획 | ✅ PASS |
| KPI 목표 | ✅ PASS |

### Stack Compatibility
| 항목 | 상태 |
|---|---|
| `shap>=0.50.0` 의존성 존재 | ✅ PASS (CLAUDE.md 확인) |
| `dashboard_snapshot.v1` additive 불변 | ✅ PASS |
| `screening_output_only=True` 불변 | ✅ PASS |
| Flask CORS 호환 | ✅ PASS |

### Apply Gates
- **Gate 0 (Dry-run)**: 이 보고서는 코드 변경 없음 ✅
- **Gate 1 (Change list)**: Best 1 = 2개 파일, Best 2 = 4개 파일, Best 3 = 3개 파일
- **Gate 2 (Approval)**: 사용자 명시적 승인 후 구현 시작
- **Gate 3 (Canary)**: 컴포넌트별 feature flag (`VITE_ENABLE_ADVISOR_PANEL=true`)
- **Gate 4 (Rollback)**: 각 컴포넌트 독립 삭제 가능

### 최종 판정: **✅ Go (Option B 권장)**

---

## Open Questions (최대 3개)

1. **실시간 데이터 소스**: WebSocket 구현 시 Yahoo Finance allorigins 프록시 의존성 유지? 아니면 유료 Market Data API(Polygon.io, Finnhub) 도입?
2. **인증 시점**: 대시보드를 내부 전용으로만 사용한다면 인증 레이어(Best 9)는 90일 이후로 미뤄도 되는가?
3. **SHAP lite 모드 성능**: `lite=True`(CV n_splits=3) 모드에서 SHAP 계산이 3초 이내 응답 가능한지 실측 필요 — `api_server.py`의 `/api/model-scores` 응답 시간 측정 권장.
