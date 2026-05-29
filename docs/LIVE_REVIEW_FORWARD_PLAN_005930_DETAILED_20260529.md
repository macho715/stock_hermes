# LIVE_REVIEW_CANDIDATE Forward Evidence Plan
## STOCK·PRED v5.1 / 005930.KS

작성일: 2026-05-29  
현재 상태: `PAPER_PASS`  
다음 상태: `FORWARD_PAPER_RUNNING`  
최종 목표: `LIVE_REVIEW_CANDIDATE`  
운영 경계: `Report-only / Manual Review / broker_order_execution=false / new_capital_allowed=false`

---

## 0. Executive Summary

현재 005930.KS는 내부 로컬 결과 기준으로 `PAPER_PASS`까지 완료된 상태다.

이미 통과한 항목:

| Gate | 기준 | 현재 | 판정 |
|---|---:|---:|---|
| PAPER_PASS | acc/AUC/OOF/trades/cost stress | 달성 | PASS |
| CPCV path pass | ≥60.00% | 80.00% | PASS |
| PBO | ≤0.20 | 0.08 | PASS |
| Deflated Sharpe | >0.00 | 0.94 | PASS |
| Model card | 존재 | 존재 | PASS |
| Dashboard safety flags | 유지 | 유지 | PASS |

아직 통과하지 못한 항목:

| Gate | 기준 | 현재 | 판정 |
|---|---:|---:|---|
| Forward paper days | ≥30거래일 | 미실행 | BLOCK |
| Forward paper alpha | ≥0.00% | 미검증 | BLOCK |
| Rule violations | 0건 | 미검증 | BLOCK |

따라서 현재 최종 판정은 다음과 같다.

```json
{
  "readiness_status": "PAPER_PASS",
  "next_status": "FORWARD_PAPER_RUNNING",
  "live_review_candidate": false,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "manual_approval_required": true,
  "remaining_blocks": [
    "FORWARD_PAPER_TRADING_30D_NOT_DONE",
    "FORWARD_PAPER_ALPHA_NOT_VERIFIED",
    "FORWARD_RULE_VIOLATION_NOT_VERIFIED"
  ]
}
```

핵심 결론:

```text
성능 개선 단계는 일단 통과.
이제 필요한 것은 30거래일 동안 실제 forward paper evidence를 쌓는 것.
Historical replay나 backfilled CSV는 승격 증거로 사용 금지.
```

---

## 1. 검증 근거 요약

### 1.1 사용자 제공 증거

현재 상태 요약 기준:

```text
CPCV pass rate ≥ 60%     PASS 80.00%
PBO ≤ 0.20               PASS 0.08
Deflated Sharpe > 0      PASS 0.94
Model card present       PASS
Dashboard safety flags   PASS
Forward paper days       미실행
Forward paper alpha      미실행
Zero rule violations     미실행
```

### 1.2 코드 확인 결과

확인된 주요 코드 상태:

| File | 확인 내용 | 조치 |
|---|---|---|
| `src/stock_rtx4060/paper_trading.py` | paper-only virtual trading engine. broker order와 credential 접근 금지 문구 존재 | 유지 |
| `src/stock_rtx4060/paper_trading.py` | paper run 산출물 생성: config, signals, orders, fills, positions, equity_curve, daily_report | 30일 누적 forward log로 확장 |
| `src/stock_rtx4060/backtest_honesty.py` | COST_STRESS, CPCV_PBO, CPCV_DSR, CPCV_PATH_RATE check 존재 | classifier input으로 사용 |
| `src/stock_rtx4060/dashboard_bridge.py` | 기존 READY_FOR_MANUAL_REVIEW 경로에서 `new_capital_allowed=true` 가능 | LIVE_REVIEW 전용 safety override 필요 |

### 1.3 Remote Verification Gap

현재 remote default branch 기준으로는 일부 신규 파일이 확인되지 않을 수 있다.

확인 필요 파일:

```text
src/stock_rtx4060/readiness/snapshots.py
src/stock_rtx4060/readiness/classifier.py
src/stock_rtx4060/backtest/cpcv_diagnostics.py
src/stock_rtx4060/backtest/pbo.py
src/stock_rtx4060/reports/model_card.py
```

따라서 로컬 구현 완료 후 반드시 아래 provenance를 고정한다.

```powershell
git status
git branch --show-current
git rev-parse HEAD
git log --oneline -10
git push
```

---

## 2. LIVE_REVIEW_CANDIDATE 정의

`LIVE_REVIEW_CANDIDATE`는 실거래 승인 상태가 아니다.  
의미는 사람이 실전 투자 검토 테이블에 올릴 수 있을 만큼 검증 증거가 충분하다는 뜻이다.

최종 상태에서도 아래는 고정이다.

```json
{
  "live_review_candidate": true,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "manual_approval_required": true,
  "screening_output_only": true,
  "approval_required_for_any_trade": true
}
```

---

## 3. 승격 조건

### 3.1 Hard Block

아래 중 하나라도 true면 즉시 `HARD_BLOCK`.

```python
hard_block = (
    broker_order_execution is True
    or screening_output_only is not True
    or manual_approval_required is not True
    or provider_audit_exists is False
    or point_in_time_safe is False
    or oof_only_backtest is False
    or data_leakage_detected is True
)
```

### 3.2 PAPER_PASS 유지 조건

```python
paper_pass = (
    oof_coverage >= 0.85
    and accuracy >= 0.52
    and auc >= 0.55
    and completed_trades >= 80
    and cost_stress_status == "PASS"
    and alpha_after_1x_cost > 0
    and alpha_after_3x_cost >= 0
    and max_drawdown_pct <= max_mdd_limit
)
```

### 3.3 LIVE_REVIEW_CANDIDATE 조건

```python
live_review_candidate = (
    paper_pass
    and cpcv_path_pass_rate >= 0.60
    and pbo <= 0.20
    and deflated_sharpe > 0.00
    and forward_paper_days >= 30
    and forward_paper_alpha >= 0.00
    and rule_violation_count == 0
    and critical_data_missing_count == 0
    and model_card_exists
    and broker_order_execution is False
    and new_capital_allowed is False
    and manual_approval_required is True
)
```

---

## 4. Forward Paper Evidence 설계

## 4.1 핵심 정책

```text
Historical replay는 테스트 fixture로만 허용.
LIVE_REVIEW 승격 증거는 실제 날짜별 forward append 기록만 허용.
Backfilled 30일 CSV는 승격 근거로 금지.
```

## 4.2 누적 CSV 경로

```text
reports/live_review/005930/paper_trading_log_005930.csv
```

## 4.3 필수 컬럼

| Column | Type | Required | 설명 |
|---|---|---|---|
| date | ISO date | YES | KRX 거래일 |
| symbol | string | YES | 005930.KS |
| market | string | YES | KRX |
| close | float | YES | EOD close |
| raw_signal | BUY/HOLD/SELL | YES | 모델 신호 |
| raw_score | float | YES | 모델 점수 |
| readiness_status | string | YES | PAPER_PASS 또는 FORWARD_PAPER_RUNNING |
| paper_action | ENTER/EXIT/HOLD/NO_ACTION | YES | paper action |
| paper_position_qty | float | YES | 가상 수량 |
| paper_cash | float | YES | paper cash |
| paper_equity | float | YES | paper equity |
| benchmark_symbol | string | YES | 069500.KS |
| benchmark_close | float | YES | benchmark EOD close |
| benchmark_equity | float | YES | benchmark equity |
| daily_return_pct | float | YES | paper daily return |
| benchmark_daily_return_pct | float | YES | benchmark daily return |
| daily_alpha_pct | float | YES | daily alpha |
| cumulative_alpha_pct | float | YES | cumulative alpha |
| max_drawdown_pct | float | YES | rolling drawdown |
| rule_violation | bool | YES | rule violation 여부 |
| rule_violation_reason | string | NO | violation reason |
| data_quality_status | PASS/AMBER/FAIL | YES | data quality |
| provider | string | YES | data provider |
| generated_at_utc | ISO datetime | YES | 생성 시각 |

---

## 5. Forward Summary 설계

## 5.1 Summary JSON 경로

```text
reports/live_review/005930/forward_paper_summary_005930.json
```

## 5.2 Summary JSON 스키마

```json
{
  "schema_version": "forward_paper_summary.v1",
  "symbol": "005930.KS",
  "benchmark_symbol": "069500.KS",
  "days": 30,
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "forward_paper_alpha_pct": 0.00,
  "rule_violation_count": 0,
  "critical_data_missing_count": 0,
  "max_forward_drawdown_pct": 0.00,
  "status": "PASS"
}
```

## 5.3 Summary pass 조건

```python
forward_paper_pass = (
    days >= 30
    and forward_paper_alpha_pct >= 0.00
    and rule_violation_count == 0
    and critical_data_missing_count == 0
    and max_forward_drawdown_pct <= forward_mdd_limit
)
```

---

## 6. Phase Plan

## Phase 0 — Provenance Freeze

목적: 현재 로컬 구현과 evidence를 고정한다.

### 산출물

```text
reports/live_review/005930/provenance.json
reports/live_review/005930/paper_pass_snapshot.json
reports/live_review/005930/cpcv_report_005930.json
reports/live_review/005930/pbo_report_005930.json
reports/live_review/005930/dsr_report_005930.json
reports/live_review/005930/cost_stress_snapshot.json
reports/model_cards/model_card_005930.md
```

### `provenance.json`

```json
{
  "schema_version": "provenance.v1",
  "symbol": "005930.KS",
  "branch": "claude/openbb-chaos-20260529",
  "commit_sha": "<full_sha>",
  "generated_at_utc": "<iso_datetime>",
  "qa": {
    "tests_passed": 1345,
    "tests_failed": 0
  },
  "status": "PAPER_PASS"
}
```

### 완료 기준

```text
[ ] full SHA recorded
[ ] QA result recorded
[ ] CPCV/PBO/DSR reports exist
[ ] model_card_005930.md exists
[ ] broker_order_execution=false
```

---

## Phase 1 — Daily Forward Runner

목적: 매 KRX EOD 이후 1개 row를 append한다.

### 권장 명령

```powershell
py -3.12 -m stock_rtx4060.paper_trading `
  --symbol 005930.KS `
  --market KRX `
  --mode forward `
  --readiness PAPER_PASS `
  --benchmark 069500.KS `
  --out reports/live_review/005930/paper_trading_log_005930.csv
```

### 실행 정책

```text
EOD close 확정 이후 1회 실행
휴장일은 SKIP
중복 date/symbol row는 기본 거부
force_rerun은 rerun_reason 필수
```

### 완료 기준

```text
[ ] 1 trading day adds exactly 1 row
[ ] duplicate date rejected unless force_rerun=true and rerun_reason exists
[ ] broker_order_execution=false
[ ] paper_trading_only=true
[ ] benchmark close exists
[ ] data_quality_status != FAIL
```

---

## Phase 2 — Forward Summary Aggregator

목적: 30거래일 누적 CSV에서 승격 가능 여부를 계산한다.

### 함수

```python
def summarize_forward_paper(log_path: Path) -> dict:
    ...
```

### 테스트

| Case | Expected |
|---|---|
| 29 rows | FAIL |
| 30 rows + alpha negative | FAIL |
| 30 rows + rule_violation > 0 | FAIL |
| 30 rows + critical missing data | FAIL |
| 30 rows + alpha ≥0 + no violation | PASS |

---

## Phase 3 — Classifier Integration

목적: PAPER_PASS + CPCV/PBO/DSR + forward paper + model card를 통합해 최종 상태를 결정한다.

### 입력 파일

```text
reports/live_review/005930/paper_pass_snapshot.json
reports/live_review/005930/cpcv_report_005930.json
reports/live_review/005930/pbo_report_005930.json
reports/live_review/005930/dsr_report_005930.json
reports/live_review/005930/forward_paper_summary_005930.json
reports/model_cards/model_card_005930.md
```

### 출력 파일

```text
reports/live_review/005930/readiness_snapshot_005930_live_review.json
```

### 상태 전이

```text
PAPER_PASS
  → FORWARD_PAPER_RUNNING
  → LIVE_REVIEW_CANDIDATE
```

단, forward paper 실패 시:

```text
PAPER_PASS 유지
```

---

## Phase 4 — Dashboard Safety Patch

목적: Dashboard가 LIVE_REVIEW_CANDIDATE를 투자 승인으로 오해하지 않게 한다.

### 필수 출력

```json
{
  "dashboard_status": "LIVE_REVIEW_CANDIDATE",
  "readiness_status": "LIVE_REVIEW_CANDIDATE",
  "live_review_candidate": true,
  "live_investable": false,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "manual_approval_required": true,
  "approval_required_for_any_trade": true,
  "paper_trading_only": false,
  "dashboard_warning": true,
  "dashboard_warning_message": "LIVE REVIEW ONLY - manual approval required; no broker order execution"
}
```

### 테스트

```text
test_live_review_never_allows_new_capital
test_live_review_never_enables_broker_execution
test_live_review_requires_manual_approval
test_paper_pass_not_equal_live_review
test_ready_for_manual_review_does_not_override_live_review_safety
```

---

## Phase 5 — Model Card Refresh

목적: 30거래일 forward evidence까지 포함한 최종 model card를 재생성한다.

### 파일

```text
reports/model_cards/model_card_005930.md
```

### 필수 섹션

```text
1. Summary
2. Intended Use
3. Out of Scope
4. Data Sources
5. Feature Set
6. Validation Method
7. Backtest Summary
8. CPCV/PBO/DSR Summary
9. Cost Stress Summary
10. Forward Paper Trading Summary
11. Risk and Limitations
12. Governance and Approval Boundary
13. Latest Readiness Status
```

### 필수 문구

```text
This report is not a buy/sell instruction.
This system does not execute broker orders.
Manual approval is required for any real trade.
new_capital_allowed=false until separate human approval.
```

---

## Phase 6 — Final QA and Promotion

### 테스트 명령

```powershell
py -3.12 -m pytest tests\test_paper_trading_forward.py tests\test_dashboard_live_review.py -q
py -3.12 -m pytest tests\test_readiness_classifier.py tests\test_model_card.py -q
py -3.12 -m pytest -q
```

### 승격 체크리스트

```text
[ ] 30 forward trading days exist
[ ] forward_paper_alpha_pct >= 0.00%
[ ] rule_violation_count == 0
[ ] critical_data_missing_count == 0
[ ] CPCV path_pass_rate >= 60.00%
[ ] PBO <= 0.20
[ ] DSR > 0.00
[ ] model_card_005930.md exists and refreshed
[ ] dashboard_snapshot validates live_review_candidate=true
[ ] new_capital_allowed=false
[ ] broker_order_execution=false
[ ] manual_approval_required=true
[ ] full pytest pass
```

---

## 7. TDD Task List

| ID | Phase | RED Test | GREEN Implementation | File |
|---|---|---|---|---|
| T001 | Contract | 29일 forward log면 FAIL | forward summary day count | `tests/test_paper_trading_forward.py` |
| T002 | Contract | 30일 alpha<0이면 FAIL | alpha gate | `tests/test_paper_trading_forward.py` |
| T003 | Contract | rule_violation>0이면 FAIL | violation gate | `tests/test_paper_trading_forward.py` |
| T004 | Contract | duplicate date append 금지 | idempotent daily append | `tests/test_paper_trading_forward.py` |
| T005 | Core | summary JSON schema 검증 실패 | summary writer | `src/stock_rtx4060/paper_trading.py` |
| T006 | Core | forward 미완료면 classifier가 FORWARD_RUNNING 유지 | classifier integration | `src/stock_rtx4060/readiness/classifier.py` |
| T007 | Core | forward PASS이면 LIVE_REVIEW 가능 | classifier final gate | `src/stock_rtx4060/readiness/classifier.py` |
| T008 | Dashboard | LIVE_REVIEW에서 new_capital_allowed true면 FAIL | dashboard patch | `src/stock_rtx4060/dashboard_bridge.py` |
| T009 | Dashboard | broker_order_execution true면 FAIL | dashboard safety field | `src/stock_rtx4060/dashboard_bridge.py` |
| T010 | Docs | model card missing이면 승격 실패 | model card existence check | `src/stock_rtx4060/reports/model_card.py` |

---

## 8. Evidence Folder Structure

```text
reports/
  live_review/
    005930/
      provenance.json
      paper_pass_snapshot.json
      cpcv_report_005930.json
      pbo_report_005930.json
      dsr_report_005930.json
      cost_stress_snapshot.json
      paper_trading_log_005930.csv
      forward_paper_summary_005930.json
      readiness_snapshot_005930_live_review.json
      dashboard_snapshot.v1.json
  model_cards/
    model_card_005930.md
```

---

## 9. Daily Runbook

```powershell
git pull

py -3.12 -m stock_rtx4060.paper_trading `
  --symbol 005930.KS `
  --market KRX `
  --mode forward `
  --readiness PAPER_PASS `
  --benchmark 069500.KS `
  --out reports/live_review/005930/paper_trading_log_005930.csv

py -3.12 -m stock_rtx4060.paper_trading `
  --summarize-forward `
  --log reports/live_review/005930/paper_trading_log_005930.csv `
  --out reports/live_review/005930/forward_paper_summary_005930.json

py -3.12 -m stock_rtx4060.readiness.classifier `
  --symbol 005930.KS `
  --evidence-dir reports/live_review/005930 `
  --out reports/live_review/005930/readiness_snapshot_005930_live_review.json
```

---

## 10. ZERO Stop Log

| 단계 | 중단 조건 | 위험 | 요청 데이터 | 다음 조치 |
|---|---|---|---|---|
| Forward run | EOD close 없음 | 잘못된 alpha 계산 | KRX EOD close | 다음 거래일 재시도 |
| Forward run | benchmark 069500.KS 없음 | 상대성과 검증 불가 | benchmark OHLCV | 승격 차단 |
| Summary | 30일 미만 | forward evidence 부족 | 추가 거래일 | FORWARD_PAPER_RUNNING 유지 |
| Summary | alpha<0 | forward 성과 부족 | 30일 log | LIVE_REVIEW 차단 |
| Summary | rule violation>0 | 운영 룰 위반 | violation detail | 원인 수정 |
| Classifier | model card 없음 | 검토 증거 부족 | model card | 재생성 |
| Dashboard | new_capital_allowed=true | 안전 경계 위반 | dashboard snapshot | 즉시 수정 |
| Dashboard | broker_order_execution=true | 금지 기능 노출 | dashboard snapshot | HARD_BLOCK |

---

## 11. 최종 판정

현재 상태:

```text
PAPER_PASS
```

다음 운영 상태:

```text
FORWARD_PAPER_RUNNING
```

최종 목표:

```text
LIVE_REVIEW_CANDIDATE
```

최종 상태에서도 아래는 계속 유지한다.

```text
new_capital_allowed=false
broker_order_execution=false
manual_approval_required=true
```
