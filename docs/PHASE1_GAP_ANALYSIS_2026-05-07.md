# Phase 1 Gap Analysis — Paper Trading Quality Upgrade
- 작성일: 2026-05-07
- 분석 대상: `paper_trading.py` (748 lines), `test_paper_trading.py` (445 lines)
- 기준 문서: `SPEC_PAPER_TRADING_QUALITY_UPGRADE_2026-05-05.md` (59 FR, 26 SC)
- 기준 문서: `TASK_PAPER_TRADING_QUALITY_UPGRADE_2026-05-05.md` (Phase 1 Tasks)

---

## 1. Phase 1 Task 카테고리 × 구현 현황

| # | Task 카테고리 | PLAN/SPEC 요구사항 | 코드 위치 | 상태 |
|---|---|---|---|---|
| T-01 | Config defaults | `PaperTradingConfig`: starting_cash, cash_buffer_pct, slippage, commission, phase1_us_only | `paper_trading.py:27-55` | ✅ IMPLEMENTED |
| T-02 | signal_gate — model AUC ≥ 0.55 | `min_model_auc=0.55` gate | `paper_trading.py:213-220` | ✅ IMPLEMENTED |
| T-03 | signal_gate — accuracy ≥ 0.52 | `min_model_accuracy=0.52` gate | `paper_trading.py:221-229` | ✅ IMPLEMENTED |
| T-04 | signal_gate — OOF coverage ≥ 0.80 | `min_oof_coverage=0.80` gate | `paper_trading.py:230-238` | ✅ IMPLEMENTED |
| T-05 | signal_gate — warning state block | `model_warning=True` → rejected | `paper_trading.py:205-212` | ✅ IMPLEMENTED |
| T-06 | signal_gate — HOLD block | `normalized_signal == "HOLD"` → rejected | `paper_trading.py:239-246` | ✅ IMPLEMENTED |
| T-07 | signal_gate — BUY/SELL score threshold (FR-007) | BUY ≥ 56, SELL ≤ 44 score threshold | `paper_trading.py:247-254` | ⚠️ PARTIAL |
| T-08 | data quality — stale bars | `stale_days=10` gate | `paper_trading.py:270-280` | ✅ IMPLEMENTED |
| T-09 | data quality — missing bars count (FR-014) | `missing_bars` count reported | `paper_trading.py:257-268` | ✅ IMPLEMENTED |
| T-10 | data quality — invalid OHLCV | `high < low` / negative price / zero volume checks | `paper_trading.py:281-300` | ✅ IMPLEMENTED |
| T-11 | data quality — split/dividend uncertainty | `dividend_yield > 0.35` / `split_ratio > 0.03` checks | `paper_trading.py:301-325` | ✅ IMPLEMENTED |
| T-12 | data quality — fill price validation | Close price filled before order write | `paper_trading.py:355-370` | ✅ IMPLEMENTED |
| T-13 | rejected-signal record — timestamp (FR-010) | Record MUST include `timestamp` field | `paper_trading.py:155-175` | ❌ MISSING |
| T-14 | rejected-signal record — ticker, signal, gate result, reason | Present in `PaperDecision.to_record()` | `paper_trading.py:155-175` | ✅ IMPLEMENTED |
| T-15 | rejected-signal record — `paper_trading_only=True` | Present in all records | `paper_trading.py:174` | ✅ IMPLEMENTED |
| T-16 | KRX Phase 1 rejection | `ticker.endswith(('.KS', '.KQ'))` → rejected | `paper_trading.py:198-204` | ✅ IMPLEMENTED |
| T-17 | Idempotent run — deterministic run_id | `{run_date}-{strategy_id}-{universe_hash}` | `paper_trading.py:390-405` | ✅ IMPLEMENTED |
| T-18 | Position limits — max exposure 60% (A-010) | `max_exposure_pct=0.60` in Config | `paper_trading.py:50` | ✅ IMPLEMENTED |
| T-19 | Position limits — max open positions 10 (A-011) | Enforced in `_write_run()` | Not found | ❌ MISSING |
| T-20 | Position limits — max daily new positions 3 (A-012) | Enforced in `_write_run()` | Not found | ❌ MISSING |
| T-21 | Forced rerun — require `rerun_reason` (FR-033) | Validated when `force_rerun=True` | `paper_trading.py:410-430` | ⚠️ PARTIAL |
| T-22 | Tests — weak model quality block | `test_paper_trading_rejects_weak_model_quality` | `test_paper_trading.py:60-90` | ✅ IMPLEMENTED |
| T-23 | Tests — missing evidence block | `test_paper_trading_rejects_missing_evidence` | `test_paper_trading.py:91-115` | ✅ IMPLEMENTED |
| T-24 | Tests — HOLD block | `test_paper_trading_rejects_hold_signal` | `test_paper_trading.py:116-135` | ✅ IMPLEMENTED |
| T-25 | Tests — stale data block | `test_paper_trading_rejects_stale_data` | `test_paper_trading.py:136-160` | ✅ IMPLEMENTED |

---

## 2. 갭 상세 분석

### GAP-01 (⚠️ PARTIAL) — FR-007: BUY 점수 임계치 미적용

**SPEC 요구사항** (FR-007):  
`BUY >= 56, SELL <= 44` — 점수 임계치 이하/이상이면 HOLD로 처리

**현재 코드** (`paper_trading.py` ~247):  
```python
if normalized_signal != "BUY":
    # rejected as HOLD/SELL
```
코드는 `normalized_signal == "BUY"` 여부만 확인하고, **`score >= 56`인지는 검사하지 않는다**.  
`recommendation_engine.py`에서 이미 `normalized_signal`을 score 기준으로 분류해 전달하는 경우라면 이 검사가 중복일 수 있으나, `paper_trading.py` 내부에서는 score 직접 검증이 없다.

**영향**: 점수 55인 BUY 신호가 통과할 수 있음. FR-007 명시적 위반.

**Fix 범위**: `evaluate_signal()` 내 score 직접 검증 1줄 추가 + 거부 이유 레코드 업데이트

---

### GAP-02 (❌ MISSING) — FR-010: rejected-signal 레코드에 timestamp 없음

**SPEC 요구사항** (FR-010):  
rejected-signal 레코드: `{timestamp, ticker, source_signal, gate_result, reason, paper_trading_only=true}`

**현재 코드** (`PaperDecision.to_record()`, ~155-175):  
`timestamp` 필드가 없음. 다른 필드(ticker, signal, gate_result, reason, paper_trading_only)는 모두 있음.

**영향**: 감사 추적(audit trail) 불완전. 언제 어떤 신호가 거부됐는지 알 수 없음.

**Fix 범위**: `PaperDecision` dataclass에 `timestamp: str` 필드 추가, `to_record()` 에 포함

---

### GAP-03 (❌ MISSING) — A-011: max open positions 10 미적용

**SPEC 요구사항** (A-011):  
최대 동시 보유 포지션 10개. 초과 시 신규 매수 거부.

**현재 코드** (`_write_run()` ~355-420):  
`open_tickers` set을 통해 중복 종목 거부는 구현됨. 그러나 **총 보유 포지션 수 ≤ 10 강제가 없음**.

**Fix 범위**: `_write_run()` 내 `len(positions) >= max_open_positions` 체크 추가

---

### GAP-04 (❌ MISSING) — A-012: max daily new positions 3 미적용

**SPEC 요구사항** (A-012):  
하루 최대 신규 진입 3개. 초과 시 당일 추가 매수 거부.

**현재 코드**: 일별 신규 진입 카운트 변수 없음.

**Fix 범위**: `_write_run()` 내 `daily_new_count` 카운터 추가, 임계치 초과 시 거부 레코드 생성

---

### GAP-05 (⚠️ PARTIAL) — FR-033: force_rerun 시 rerun_reason 미검증

**SPEC 요구사항** (FR-033):  
강제 재실행 시 `rerun_reason` 필수.

**현재 코드** (`paper_trading.py` ~410-430):  
`rerun_reason` 필드는 존재하나, `force_rerun=True`일 때 `rerun_reason` 가 빈 문자열이어도 차단되지 않음.

**영향**: 감사 추적 불완전 (why rerun was forced 없이 재실행 가능).

**Fix 범위**: `run()` 내 early validation: `if force_rerun and not rerun_reason: raise ValueError`

---

## 3. 테스트 갭

| # | 테스트 대상 | 현재 상태 | Gap |
|---|---|---|---|
| TC-01 | BUY score < 56 거부 | ❌ 없음 | test_rejects_low_score_buy 추가 필요 |
| TC-02 | timestamp in rejected-signal record | ❌ 없음 | timestamp 필드 확인 테스트 필요 |
| TC-03 | max open positions 10 초과 거부 | ❌ 없음 | test_max_open_positions_limit 추가 필요 |
| TC-04 | max daily new positions 3 초과 거부 | ❌ 없음 | test_max_daily_new_positions_limit 추가 필요 |
| TC-05 | force_rerun without rerun_reason 거부 | ❌ 없음 | test_force_rerun_requires_reason 추가 필요 |

기존 19개 테스트 모두 ✅ 통과 유지 필요 (현재 구현 회귀 없음).

---

## 4. 요약 표

| 상태 | 항목 수 | 항목 |
|---|---|---|
| ✅ IMPLEMENTED | 20 | T-01~T-06, T-08~T-12, T-14~T-18, T-22~T-25 |
| ⚠️ PARTIAL | 2 | GAP-01 (FR-007 score threshold), GAP-05 (FR-033 rerun_reason) |
| ❌ MISSING | 3 | GAP-02 (FR-010 timestamp), GAP-03 (A-011 max positions), GAP-04 (A-012 daily limit) |

**코드 변경 범위**: `paper_trading.py` 내 5개 surgical fix, `test_paper_trading.py` 내 5개 테스트 추가.  
**기존 코드 회귀 위험**: 낮음 — 모두 gate 강화 또는 필드 추가, 기존 로직 삭제 없음.

---

## 5. Step 2 진행 전 재승인 요청

위 갭 표 기준으로 Step 2(잔여 구현)를 진행하려면 다음 작업이 필요합니다:

1. `paper_trading.py` — 5개 surgical fix (GAP-01 ~ GAP-05)
2. `test_paper_trading.py` — 5개 테스트 추가 (TC-01 ~ TC-05)

**Step 2를 진행해도 됩니까? (yes / abort)**
