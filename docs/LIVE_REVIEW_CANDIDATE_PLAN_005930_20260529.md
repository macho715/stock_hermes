# LIVE_REVIEW_CANDIDATE 전환 상세 Plan — STOCK·PRED v5.1 / 005930.KS

작성일: 2026-05-29  
현재 상태: `PAPER_PASS`  
다음 목표: `LIVE_REVIEW_CANDIDATE`  
운영 경계: `Report-only / Manual Review / broker_order_execution=false / new_capital_allowed=false`

---

## 0. Executive Summary

현재 005930.KS는 로컬 검증 기준으로 `PAPER_PASS`까지 도달했다.

확인된 PAPER_PASS 근거:

| Metric | Result | Gate | Status |
|---|---:|---:|---|
| OOF coverage | 100.00% | ≥85.00% | PASS |
| Accuracy | 59.80% | ≥52.00% | PASS |
| AUC | 0.602 | ≥0.55 | PASS |
| Completed trades | 81 | ≥80 | PASS |
| Cost stress | PASS | PASS | PASS |
| Alpha 1x | +5.32% | >0.00% | PASS |
| Alpha 3x | +1.35% | ≥0.00% | PASS |
| MDD | 1.60% | <20.00% | PASS |
| Sharpe | 0.934 | >0.00 기준 PASS / ≥1.20 기준 AMBER | CONDITIONAL |

`LIVE_REVIEW_CANDIDATE`는 자동매매 가능 상태가 아니다.  
의미는 “사람이 실제 투자 검토 테이블에 올릴 수 있을 만큼 검증 증거가 충분한 상태”다.

필수 통과 조건:

```text
1. CPCV path_pass_rate ≥ 60.00%
2. PBO ≤ 20.00%
3. Deflated Sharpe Ratio > 0.00
4. 30거래일 forward paper trading alpha ≥ 0.00%
5. model_card_005930.md 존재
6. dashboard/readiness snapshot에 live_review_candidate=true 표시
7. broker_order_execution=false 유지
8. new_capital_allowed=false 유지
```

---

## 1. Scope

### 1.1 In Scope

| No | Scope | Target |
|---:|---|---|
| 1 | CPCV 진단 | `CombinatorialPurgedCV` 기반 path별 OOS 성과 분포 |
| 2 | PBO 계산 | overfitting probability 산출 |
| 3 | Deflated Sharpe Ratio | multiple testing 보정 후 Sharpe 유효성 확인 |
| 4 | Forward paper trading | 30거래일 실제 forward-like 기록 |
| 5 | Model card | 005930.KS 후보 설명서 생성 |
| 6 | Dashboard readiness | `LIVE_REVIEW_CANDIDATE` 표시 계약 |
| 7 | Regression tests | 기존 전체 QA 유지 + 신규 live-review tests 추가 |

### 1.2 Out of Scope

| 항목 | 처리 |
|---|---|
| 브로커 주문 실행 | 금지 |
| 계좌 연동 | 금지 |
| 자동매매 | 금지 |
| 신규 자금 자동 투입 | 금지 |
| 수익 보장 문구 | 금지 |
| 임의 threshold 완화 | 금지 |
| 모델 성능 수치 조작 | 금지 |

---

## 2. Current Baseline

### 2.1 PAPER_PASS Snapshot

```json
{
  "symbol": "005930.KS",
  "readiness_status": "PAPER_PASS",
  "live_review_candidate": false,
  "new_capital_allowed": false,
  "manual_approval_required": true,
  "broker_order_execution": false,
  "screening_output_only": true,
  "metrics": {
    "oof_coverage": 1.0,
    "accuracy": 0.598,
    "auc": 0.602,
    "completed_trades": 81,
    "alpha_1x_pct": 5.32,
    "alpha_3x_pct": 1.35,
    "cost_stress": "PASS",
    "sharpe": 0.934,
    "mdd_pct": 1.60
  }
}
```

### 2.2 Risk Note

`PAPER_PASS`는 실거래 승인이 아니다.  
CPCV/PBO/DSR과 30거래일 forward paper trading이 없으면 live-review 후보로 올리면 안 된다.

---

## 3. Target Definition

### 3.1 Required Final State

```json
{
  "readiness_status": "LIVE_REVIEW_CANDIDATE",
  "live_review_candidate": true,
  "new_capital_allowed": false,
  "manual_approval_required": true,
  "broker_order_execution": false,
  "screening_output_only": true,
  "approval_required_for_any_trade": true
}
```

### 3.2 Required Evidence Files

| Evidence | Required | Target Path |
|---|---|---|
| PAPER_PASS baseline | YES | `reports/live_review/005930/paper_pass_snapshot.json` |
| CPCV report | YES | `reports/live_review/005930/cpcv_report_005930.json` |
| PBO report | YES | `reports/live_review/005930/pbo_report_005930.json` |
| DSR report | YES | `reports/live_review/005930/dsr_report_005930.json` |
| Forward paper log | YES | `reports/live_review/005930/paper_trading_log_005930.csv` |
| Forward paper summary | YES | `reports/live_review/005930/forward_paper_summary_005930.json` |
| Model card | YES | `reports/model_cards/model_card_005930.md` |
| Readiness snapshot | YES | `reports/live_review/005930/readiness_snapshot_005930_live_review.json` |
| Dashboard snapshot | YES | `reports/live_review/005930/dashboard_snapshot.v1.json` |

---

## 4. Gate Design

## 4.1 Hard Block Gate

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

### Hard Block Output

```json
{
  "readiness_status": "HARD_BLOCK",
  "live_review_candidate": false,
  "new_capital_allowed": false,
  "broker_order_execution": false
}
```

---

## 4.2 PAPER_PASS Gate

현재 달성 상태를 유지해야 한다.

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

### Sharpe Policy

| Field | 기준 | 의미 |
|---|---:|---|
| `sharpe_positive_gate` | `sharpe > 0.00` | PAPER_PASS 최소 조건 |
| `sharpe_strict_gate` | `sharpe ≥ 1.20` | LIVE_REVIEW 보조 품질 조건 |

현재 Sharpe 0.934는 최소 기준은 통과하지만 strict 기준은 미달이다.  
따라서 `PAPER_PASS_WITH_SHARPE_AMBER`로 기록한다.

---

## 4.3 LIVE_REVIEW Gate

```python
live_review_candidate = (
    paper_pass is True
    and cpcv_path_pass_rate >= 0.60
    and pbo <= 0.20
    and deflated_sharpe > 0.00
    and forward_paper_days >= 30
    and forward_paper_alpha >= 0.00
    and model_card_exists is True
    and broker_order_execution is False
    and new_capital_allowed is False
)
```

---

## 5. Phase Plan

## Phase 0 — Freeze PAPER_PASS Baseline

### Objective

현재 PAPER_PASS 결과를 기준 snapshot으로 고정한다.

### Tasks

| Task ID | Task | File |
|---|---|---|
| LRC-000 | 현재 005930.KS metrics JSON 저장 | `reports/live_review/005930/paper_pass_snapshot.json` |
| LRC-001 | 현재 backtest result 저장 | `reports/live_review/005930/backtest_snapshot.json` |
| LRC-002 | cost stress result 저장 | `reports/live_review/005930/cost_stress_snapshot.json` |
| LRC-003 | 현재 commit/full SHA 기록 | `reports/live_review/005930/provenance.json` |

### Acceptance Criteria

```text
paper_pass_snapshot.json exists
provenance.json contains branch, full_sha, generated_at_utc
broker_order_execution=false
new_capital_allowed=false
```

### Commands

```powershell
git status
git rev-parse HEAD
git branch --show-current
py -3.12 -m pytest -q
```

---

## Phase 1 — CPCV Path Distribution

### Objective

단일 backtest가 아니라 여러 purged test path에서 성과 분포를 확인한다.

### Target Files

| File | Action |
|---|---|
| `src/stock_rtx4060/ml/cv.py` | 기존 `CombinatorialPurgedCV` 사용 |
| `src/stock_rtx4060/backtest/cpcv_diagnostics.py` | 신규 생성 |
| `tests/test_cpcv_live_review.py` | 신규 테스트 |

### CPCV Config

```json
{
  "n_splits": 6,
  "n_test_splits": 2,
  "embargo_pct": 0.01,
  "horizon": 10,
  "min_path_pass_rate": 0.60
}
```

### Path Pass Definition

```python
path_pass = (
    path_auc >= 0.50
    and path_alpha_after_1x_cost > 0
    and path_mdd_pct <= max_mdd_limit
    and path_completed_trades >= min_trades_per_path
)
```

### Output Schema

```json
{
  "schema_version": "cpcv_report.v1",
  "symbol": "005930.KS",
  "cv_method": "combinatorial_purged_cv",
  "n_splits": 6,
  "n_test_splits": 2,
  "path_count": 15,
  "path_pass_count": 10,
  "path_pass_rate": 0.6667,
  "status": "PASS",
  "paths": [
    {
      "path_id": 1,
      "test_folds": [0, 1],
      "auc": 0.57,
      "alpha_after_1x_cost": 1.22,
      "mdd_pct": 2.10,
      "n_trades": 12,
      "status": "PASS"
    }
  ]
}
```

### Acceptance Criteria

```text
path_count >= 10
path_pass_rate >= 0.60
all paths use purged split
no train/test label overlap
```

---

## Phase 2 — PBO Calculation

### Objective

Backtest overfitting probability를 계산한다.

### Target

```text
PBO ≤ 20.00%
```

### Target Files

| File | Action |
|---|---|
| `src/stock_rtx4060/backtest/pbo.py` | 신규 생성 |
| `tests/test_pbo.py` | 신규 테스트 |

### Output Schema

```json
{
  "schema_version": "pbo_report.v1",
  "symbol": "005930.KS",
  "pbo": 0.18,
  "threshold": 0.20,
  "status": "PASS",
  "method": "cpcv_rank_logit"
}
```

### Acceptance Criteria

```text
PBO value in [0, 1]
PBO <= 0.20 => PASS
PBO > 0.20 => AMBER or FAIL
```

---

## Phase 3 — Deflated Sharpe Ratio

### Objective

Sharpe가 multiple testing과 non-normal return distribution을 견딜 수 있는지 확인한다.

### Target

```text
deflated_sharpe > 0.00
```

### Target Files

| File | Action |
|---|---|
| `src/stock_rtx4060/backtester.py` | 기존 advanced stats 사용 |
| `src/stock_rtx4060/backtest_honesty.py` | DSR gate 추가 |
| `tests/test_deflated_sharpe_gate.py` | 신규 테스트 |

### Output Schema

```json
{
  "schema_version": "dsr_report.v1",
  "symbol": "005930.KS",
  "deflated_sharpe": 0.14,
  "psr_vs_zero": 0.71,
  "mc_drawdown_p95": 4.80,
  "status": "PASS"
}
```

### Acceptance Criteria

```text
deflated_sharpe is not null
deflated_sharpe > 0
psr_vs_zero is reported
mc_drawdown_p95 is reported
```

---

## Phase 4 — 30 Trading Days Forward Paper Trading

### Objective

백테스트가 아닌 forward-like 환경에서 신호가 유지되는지 확인한다.

### Duration

```text
Minimum: 30 trading days
Recommended: 60 trading days
```

### Required Daily Log Columns

| Column | Type | Required |
|---|---|---|
| date | ISO date | YES |
| symbol | string | YES |
| signal | BUY/HOLD/SELL | YES |
| raw_score | float | YES |
| readiness_status | string | YES |
| close | float | YES |
| action | ENTER/EXIT/HOLD/NO_ACTION | YES |
| position_qty | float | YES |
| equity | float | YES |
| benchmark_equity | float | YES |
| daily_alpha_pct | float | YES |
| cumulative_alpha_pct | float | YES |
| rule_violation | bool | YES |
| notes | string | NO |

### Output File

```text
reports/live_review/005930/paper_trading_log_005930.csv
```

### Forward Pass Criteria

```python
forward_pass = (
    paper_trading_days >= 30
    and forward_paper_alpha >= 0
    and rule_violation_count == 0
    and critical_data_missing_count == 0
    and max_forward_drawdown_pct <= forward_mdd_limit
)
```

### Acceptance Criteria

```text
30 trading rows exist
cumulative_alpha_pct >= 0
rule_violation_count == 0
dashboard can show paper status
```

---

## Phase 5 — Model Card

### Objective

실전 검토자가 이해할 수 있는 모델 설명서를 만든다.

### Output File

```text
reports/model_cards/model_card_005930.md
```

### Required Sections

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

### Required Statements

```text
This report is not a buy/sell instruction.
This system does not execute broker orders.
Manual approval is required for any real trade.
new_capital_allowed=false until human approval.
```

### Acceptance Criteria

```text
model_card_005930.md exists
contains latest metrics
contains blocking/remaining risks
contains broker_order_execution=false
contains manual_approval_required=true
```

---

## Phase 6 — Dashboard Readiness Contract

### Objective

Dashboard가 `PAPER_PASS`와 `LIVE_REVIEW_CANDIDATE`를 정확히 구분하게 한다.

### Required Fields

```json
{
  "readiness_status": "LIVE_REVIEW_CANDIDATE",
  "live_review_candidate": true,
  "paper_pass": true,
  "new_capital_allowed": false,
  "manual_approval_required": true,
  "broker_order_execution": false,
  "cpcv": {
    "path_pass_rate": 0.6667,
    "pbo": 0.18,
    "deflated_sharpe": 0.14
  },
  "forward_paper": {
    "days": 30,
    "alpha_pct": 0.82,
    "status": "PASS"
  },
  "model_card_path": "reports/model_cards/model_card_005930.md"
}
```

### Target Files

| File | Action |
|---|---|
| `src/stock_rtx4060/dashboard_bridge.py` | readiness fields 추가 |
| `tests/test_dashboard_live_review.py` | 신규 테스트 |

### Acceptance Criteria

```text
LIVE_REVIEW_CANDIDATE 표시 가능
new_capital_allowed=false 유지
broker_order_execution=false 유지
PAPER_PASS와 LIVE_REVIEW가 UI에서 분리 표시
```

---

## Phase 7 — Final Regression and Promotion

### Objective

모든 gate를 통과한 경우에만 `LIVE_REVIEW_CANDIDATE`로 승격한다.

### Final Test Commands

```powershell
py -3.12 -m pytest tests\test_cpcv_live_review.py tests\test_pbo.py tests\test_deflated_sharpe_gate.py -q
py -3.12 -m pytest tests\test_paper_trading_forward.py tests\test_model_card.py tests\test_dashboard_live_review.py -q
py -3.12 -m pytest -q
```

### Final Promotion Logic

```python
if hard_block:
    readiness_status = "HARD_BLOCK"
elif not paper_pass:
    readiness_status = "AMBER_WATCHLIST"
elif not cpcv_pbo_dsr_pass:
    readiness_status = "PAPER_PASS"
elif not forward_paper_pass:
    readiness_status = "PAPER_PASS"
elif not model_card_exists:
    readiness_status = "PAPER_PASS"
else:
    readiness_status = "LIVE_REVIEW_CANDIDATE"
```

---

## 6. Task Breakdown

| ID | Priority | Task | File | Test First |
|---|---:|---|---|---|
| LRC-001 | P0 | PAPER_PASS snapshot writer | `src/stock_rtx4060/readiness/snapshot.py` | YES |
| LRC-002 | P0 | CPCV diagnostic runner | `src/stock_rtx4060/backtest/cpcv_diagnostics.py` | YES |
| LRC-003 | P0 | PBO calculator | `src/stock_rtx4060/backtest/pbo.py` | YES |
| LRC-004 | P0 | DSR gate integration | `src/stock_rtx4060/backtest_honesty.py` | YES |
| LRC-005 | P0 | Live-review classifier | `src/stock_rtx4060/readiness/classifier.py` | YES |
| LRC-006 | P1 | Forward paper trading logger | `src/stock_rtx4060/paper_trading.py` | YES |
| LRC-007 | P1 | Model card generator | `src/stock_rtx4060/reports/model_card.py` | YES |
| LRC-008 | P1 | Dashboard live-review fields | `src/stock_rtx4060/dashboard_bridge.py` | YES |
| LRC-009 | P2 | CLI command for live-review check | `main.py` or `cli.py` | YES |
| LRC-010 | P2 | Documentation update | `docs/LIVE_REVIEW_CANDIDATE_PLAN.md` | NO |

---

## 7. Test Plan

### Unit Tests

| Test | Purpose |
|---|---|
| `test_cpcv_path_count` | CPCV path count correct |
| `test_cpcv_no_label_leakage` | no train/test label overlap |
| `test_pbo_range` | PBO in [0,1] |
| `test_pbo_gate` | PBO threshold works |
| `test_dsr_gate` | DSR >0 pass |
| `test_live_review_requires_paper_pass` | no paper pass, no live review |
| `test_live_review_blocks_broker_execution` | broker execution true hard block |
| `test_model_card_contains_safety_boundary` | required safety wording |

### Integration Tests

| Test | Purpose |
|---|---|
| `test_005930_live_review_pipeline` | 005930 full evidence pipeline |
| `test_dashboard_live_review_snapshot` | dashboard fields |
| `test_forward_paper_summary` | paper log → summary |
| `test_report_only_boundary` | no broker order output |

### Regression Target

```text
>= 1345 passed
0 failed
coverage >= 85.00%
```

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| CPCV path count increases runtime | Medium | Use `n_splits=6`, `n_test_splits=2` default |
| PBO calculation unstable with few paths | Medium | Minimum path count ≥10 |
| DSR fails despite PAPER_PASS | Medium | Keep status at PAPER_PASS, do not force promotion |
| 30-day forward paper trading delays promotion | High | Intended gate; do not bypass |
| Model card becomes stale | Medium | Regenerate on each live-review run |
| Dashboard misleads user as trade approval | High | Keep `new_capital_allowed=false`, `manual_approval_required=true` |
| Python 3.14 dependency drift | Medium | Use project `.venv` Python 3.12 |

---

## 9. Governance

### Non-Negotiable Rules

```text
No broker order execution.
No account write.
No automatic trading.
No return guarantee.
No live capital without human approval.
No live-review promotion without CPCV/PBO/DSR + forward paper + model card.
```

### Required Metadata

Every live-review output must include:

```json
{
  "generated_at_utc": "...",
  "branch": "...",
  "commit_sha": "...",
  "symbol": "005930.KS",
  "schema_version": "...",
  "data_provider": "...",
  "model_kind": "...",
  "cv_method": "...",
  "evidence_paths": []
}
```

---

## 10. Definition of Done

`LIVE_REVIEW_CANDIDATE` is complete only when all are true:

```text
[ ] Full SHA recorded
[ ] QA full test passed
[ ] PAPER_PASS snapshot saved
[ ] CPCV path_pass_rate ≥60.00%
[ ] PBO ≤20.00%
[ ] Deflated Sharpe >0.00
[ ] Forward paper trading ≥30 trading days
[ ] Forward paper alpha ≥0.00%
[ ] Model card exists
[ ] Dashboard snapshot validates live_review_candidate=true
[ ] new_capital_allowed=false
[ ] broker_order_execution=false
[ ] Manual approval required
```

---

## 11. Recommended Commands

```powershell
# Baseline
git status
git rev-parse HEAD
py -3.12 -m pytest -q

# CPCV / PBO / DSR
py -3.12 -m pytest tests\test_cpcv_live_review.py tests\test_pbo.py tests\test_deflated_sharpe_gate.py -q

# Forward paper + model card
py -3.12 -m pytest tests\test_paper_trading_forward.py tests\test_model_card.py -q

# Dashboard
py -3.12 -m pytest tests\test_dashboard_live_review.py tests\test_dashboard_bridge.py -q

# Final
py -3.12 -m pytest -q
```

---

## 12. Final Verdict

현재 005930.KS는 `PAPER_PASS`다.

다음 단계는 투자 실행이 아니라 아래 3대 증거를 추가하는 것이다.

```text
1. CPCV/PBO/DSR
2. 30거래일 forward paper trading
3. model card
```

이 3개가 통과되어야만 `LIVE_REVIEW_CANDIDATE`로 승격한다.

그 이후에도 아래는 유지한다.

```text
new_capital_allowed=false
broker_order_execution=false
manual_approval_required=true
```
