# 20260531 작업 종합 Plan — Dashboard Safety Gate + quant1901 병합

작성일: 2026-05-31 (Sun)
작성자: Claude (opus-4-8)
대상 repo: `macho715/stock_1901`
모드: research / paper-trading only · live trading & broker execution **금지**

---

## 0. Executive Summary

> **결론 먼저:** 3개 작업을 완료했다 — (1) 대시보드 안전 게이트 패치, (2) 6-에이전트 병렬 병합 전략 테스트, (3) 최고점 전략(C+A)으로 quant1901 백테스트 엔진을 stock_1901에 통합. 신규 테스트 23개(JS 11 + Python 12) 전부 통과, 회귀 0건, 모든 핵심 불변 유지.

| 작업 | 산출물 | 검증 |
|---|---|---|
| A. Dashboard Safety Gate | `dashboard/stock_pred_v5.jsx` 패치 + JS 테스트 11개 | 11/11 PASS |
| B. 병합 전략 병렬 테스트 | 6-agent workflow 평가 리포트 | 4개 전략 PASS, C 91점 BEST |
| C. quant1901 병합 구현 | runner + strategy + CLI + Python 테스트 12개 | 12/12 PASS, 회귀 96/96 |

**테스트 합계: 23개** (JS 11 + Python 12)

---

## 1. 작업 A — Dashboard Safety Gate Patch

### 1.1 Objective

검증 실패·약한 모델 근거·synthetic/stale 데이터·목표수익 미달 시 UI를
`NO TRADE / PAPER ONLY`로 강제하여, 실패한 신호를 거래 가능 신호로 오인하지 않게 한다.

근거: SEC AI 투자 광고 규제, Investor.gov 사기 red flag, AI action-bias 경고.

### 1.2 구현 내용

파일: `dashboard/stock_pred_v5.jsx` (2103줄 단일 React 파일)

| 추가/수정 | 내용 |
|---|---|
| `HARD_BLOCKERS[]` | 11개 하드 블로커 (BACKTEST_HONESTY_NOT_PASS, SYNTHETIC_DATA_SOURCE 등) |
| `SOFT_WARNINGS[]` | 7개 소프트 경고 (COST_FRAGILE, DATA_SOURCE_AMBER 등) |
| `SOURCE_RISK{}` | YAHOO/KRX=OK, pykrxcache=AMBER, SYN/synthetic=BLOCK |
| `buildDecisionSafetyState()` | 정규화된 UI 안전 상태 객체 생성 |
| `flagsFromBackendResult()` | 백엔드 validation → evidence flag 매핑 |
| `RiskGateBanner` | 하드 블록 시 최상단 빨간 배너 |
| `SignalTab` 전면 교체 | verdict/confidence/action-plan 안전 게이트 적용 |
| 차트 높이 | 260px → 210px (decision gate 우선순위 ↑) |
| Watchlist | SYN+BUY → `HOLD/BLOCKED` |

### 1.3 핵심 정책

```
하드 블로커 존재  → NO TRADE / PAPER ONLY  (confidence ≤ 50)
소프트 경고만     → WATCH ONLY / REVIEW    (confidence ≤ 65)
클린             → 원본 AI 추천 유지
liveTradingAllowed = false (항상)
brokerExecutionAllowed = false (항상)
```

### 1.4 검증 (Definition of Done 13항목)

```
tests/test_dashboard_safety_gate.js → 11/11 PASS
금지 문구 스캔(guaranteed return 등) → 0건
DoD 체크리스트 → 11/11 PASS
```

---

## 2. 작업 B — 다중 에이전트 병합 전략 테스트

### 2.1 Objective

`quant1901_executable_bundle`을 기존 시스템에 병합하는 5개 후보 전략을
병렬 테스트하여 데이터 기반으로 best 안을 선정한다.

### 2.2 후보 전략

| ID | 전략 | 통합 위치 |
|---|---|---|
| A | Thin Wrapper Import | `strategies/` |
| B | Factor Zoo 등록 | P2 `factors/` |
| C | Backtest Plugin | P5 `backtest/` |
| D | Prefect Flow 자동화 | P7 `flows/` (이번 제외) |
| E | Immediate Bridge | `tools/` |

### 2.3 실행 방법

Workflow 도구로 6개 에이전트 병렬 실행:
- Phase 1: baseline (quant1901 실행 + 005930.KS OHLCV 추출 시도)
- Phase 2: 4개 전략(E/A/C/B) 동시 테스트 — 실제 코드 작성 + 테스트 실행
- Phase 3: 4기준 가중 평가 (테스트 35% / 통합 25% / 노력 20% / 안전 20%)

소요: 5분 21초, 91 tool calls, 602k tokens

### 2.4 결과 매트릭스

| 전략 | Score | Test | Blockers | Lines |
|---|:---:|:---:|---|:---:|
| **C — Backtest Plugin** | **91** | PASS | 없음 | 290 |
| A — Thin Wrapper | 88 | PASS | 없음 | 126 |
| E — Bridge | 82 | PASS | 없음 | 236 |
| B — Factor Zoo | 75 | PASS | 3개 (PIT guard, HTF inflation, category) | 100 |

### 2.5 핵심 발견

- **데이터 소스:** `load_ohlcv_with_provider('005930.KS')`가 `period` 필수 인자 누락으로 실패 → synthetic fallback 사용. (data_providers.py 자체 버그 아님, 호출 측 문제)
- **Strategy C 우위:** P5 인프라 직접 연결 + dashboard_snapshot.v1 풀 정책 게이트 + 모듈 경계에서 execution lock 강제.
- **Strategy B 보류:** as_of 슬라이싱 rows<60 → ValueError, HTF 단기 패널 IC 부풀림, IC=0.058(120행 synthetic) 통계적 무의미.

### 2.6 권장

**Strategy C 우선 병합 → A guard 래퍼 추가 → E는 legacy 보관 → B는 별도 스프린트**

---

## 3. 작업 C — quant1901 병합 구현 (Strategy C + A)

### 3.1 Scope

| In | Out |
|---|---|
| `backtest/quant1901_runner.py` (C) | broker/, live trading, .env (금지) |
| `strategies/quant1901_strategy.py` (A) | Strategy B Factor Zoo (별도 스프린트) |
| `tests/test_quant1901_runner.py` | Prefect flow (C 검증 후) |
| `main.py` CLI 서브커맨드 | Strategy E (legacy 이동) |

### 3.2 Steps (7단계 실행 결과)

| Step | 작업 | 결과 |
|---|---|---|
| 1 | data_providers 시그니처 확인 | `period` 필수 인자 이미 존재 — 버그는 호출 측 누락이었음 (CLI에서 올바르게 전달하도록 구현) |
| 2 | `Quant1901Runner` 작성 | 경로 버그 `parents[5]→[3]` + `grid_search→optimize_parameters` 수정 |
| 3 | Strategy A guard 래퍼 | lowercase 컬럼 정규화 포함 |
| 4 | CLI `quant1901-backtest` | 서브커맨드 + handler + `_safe_ticker` |
| 5 | 테스트 작성 | 12 케이스 (계획 8 + 추가 4) |
| 6 | 검증 게이트 | 96/96 통합 회귀 PASS |
| 7 | Strategy E 처리 | `tools/legacy/`로 이동 (사용자 선택) |

### 3.3 Quant1901Runner 정책 게이트

```python
# 5개 validation
BACKTEST_HONESTY  : paper-only 모드 확인 → PASS/FAIL (CRITICAL)
SHARPE            : ≥0.50 PASS / <0.50 WARN
CALMAR            : ≥0.30 PASS / <0.30 WARN
MAX_DRAWDOWN      : ≤15% PASS / >15% FAIL (HIGH)
TARGET_RETURN_10PCT : monthly_hit ≥33% PASS / WARN + promotion_blocker

# verdict
risk_halt           → BLOCKED_RISK_HALT
all PASS            → CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE
그 외               → NOT_PASS

# 불변 (모듈 경계 강제)
execution_controls.live_trading_allowed    = False
execution_controls.broker_execution_allowed = False
screening_output_only = True
```

### 3.4 CLI 사용법

```bash
# synthetic
python -m stock_rtx4060.main quant1901-backtest \
  --synthetic --rows 360 --seed 1901 --optimize --ticker SYNTH1901

# 실데이터 (provider 경로)
python -m stock_rtx4060.main quant1901-backtest \
  --ticker 005930.KS --period 2y --optimize

# CSV
python -m stock_rtx4060.main quant1901-backtest \
  --csv data.csv --ticker 005930 --optimize

# 출력: reports/quant1901/<ticker>/snapshot.json (dashboard_snapshot.v1)
```

### 3.5 검증 증거 (fresh, 2026-05-31)

```
신규 테스트:     test_quant1901_runner.py 12/12 passed
통합 회귀:       96/96 passed (runner+dashboard_bridge+backtester_sizing+main_extra)
Bundle 원본:     test_quant1901_executor.py 4/4 passed (회귀 없음)
CLI 회귀:        test_cli_compat.py 통과
compileall:      ALL_COMPILE_OK
CLI 불변:        env/recommend/paper-run/dashboard-export/quant1901-backtest exit=0
dashboard_bridge: build_dashboard_snapshot import OK
참조 무결성:     NO_BROKEN_REFERENCES (legacy 이동 후)
```

---

## 4. 변경 파일 전체 목록

### 신규 (this session)

```
src/stock_rtx4060/backtest/quant1901_runner.py        296 lines  (Strategy C)
src/stock_rtx4060/strategies/__init__.py                         (패키지 init)
src/stock_rtx4060/strategies/quant1901_strategy.py    126 lines  (Strategy A)
tests/test_quant1901_runner.py                        185 lines  (12 케이스)
tests/test_dashboard_safety_gate.js                   287 lines  (11 케이스)
tools/legacy/quant1901_to_snapshot.py                            (Strategy E, 이동)
tools/legacy/README.md                                           (deprecation 노트)
docs/20260531_quant1901_merge_safety_gate_v1.md                  (본 문서)
```

### 수정

```
dashboard/stock_pred_v5.jsx        Safety gate 패치 (상수+헬퍼+UI 7개 영역)
src/stock_rtx4060/main.py          quant1901-backtest 서브커맨드 추가
```

---

## 5. Risk / 남은 작업

| 리스크 | 상태 | 대응 |
|---|---|---|
| synthetic verdict가 NOT_PASS | 예상된 동작 | **실데이터 검증 필요** (가장 시급) |
| `load_ohlcv_with_provider` period | CLI에서 올바르게 전달 | 완료 |
| 번들 경로 하드코딩 | `parents[3]` 수정 | 다른 머신 시 env var fallback 고려 |
| Strategy B 3개 블로커 | 보류 | 별도 스프린트 |
| 커버리지 83% 유지 | 신규 파일 TDD | 통합 회귀 96/96 |

---

## 6. 다음 추천 작업 (우선순위)

1. **실데이터 검증 (시급)** — `quant1901-backtest --ticker 005930.KS --period 2y --optimize` 실행하여 실데이터 policy verdict 확인. synthetic NOT_PASS가 실데이터에서 어떻게 바뀌는지 검증.
2. **C + A 결합** — A의 import-time execution guard를 C 래퍼로 추가 (방어 심층화).
3. **Strategy B 스프린트** — `_compute_single()` 60행 early-exit, HTF 최소 주봉 체크, category 재검토.
4. **Prefect flow (Strategy D)** — C 검증 통과 후 `flows/quant1901_daily.py` 자동화.

---

## 7. 안전 경계 (전 작업 공통 준수)

```
✓ broker order placement     — 추가 안 함
✓ live order router          — 추가 안 함
✓ auto buy/sell              — 추가 안 함
✓ credential / .env / secret — 수정 안 함
✓ financial advice claim     — 없음
✓ return guarantee wording   — 0건 (스캔 확인)
✓ live_trading_allowed       — false (모듈 경계 강제)
✓ broker_execution_allowed   — false
✓ screening_output_only      — true
```
