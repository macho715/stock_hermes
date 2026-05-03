# Phase 2: Validation Gate Design
## Real Data Ops Upgrade — provider selection & thresholds

**Date**: 2026-05-03
**Status**: ✅ APPROVED (2026-05-03) — all thresholds confirmed
**Phase 1**: ✅ APPROVED (Q-1=Y, Q-2=Y, Q-3=Y, Q-4=optional)

---

## Overview

Validation gates are check functions that run **before** a recommendation is approved. Each gate takes a `ProviderResult` + derived data and returns `PASS | AMBER | RED | ZERO`. Gates do NOT execute orders — they block or flag candidates.

---

## Gate Definitions

### G-01: DATA_FRESHNESS

**Input**: `ProviderResult.metadata.data_freshness_minutes`
**Logic**:

| Condition | Result |
|-----------|--------|
| KRX market, ≤1 business day | PASS |
| KRX market, 1–3 business days stale | AMBER |
| NYSE/NASDAQ, ≤1 calendar day | PASS |
| NYSE/NASDAQ, >1 calendar day | RED |
| Unknown market / no metadata | RED |
| KRX >3 business days stale | RED |

**Audit evidence**: `data_freshness_minutes`, `market`, `stale_days`

---

### G-02: PRICE_CROSSCHECK

**Input**: Latest close from provider vs. cross-reference provider
**Logic**:

| Condition | Result |
|-----------|--------|
| Δ ≤ 1.0% between two sources | PASS |
| Δ 1.0–3.0% | AMBER — flag for manual review |
| Δ > 3.0% | RED — data error suspected |
| Single source only (no cross-ref possible) | AMBER (warn) |

**Cross-reference pairs**:
- KRX: PyKRX ↔ FinanceDataReader
- NYSE/NASDAQ: yfinance ↔ OpenBB

**Audit evidence**: `price_provider_a`, `price_provider_b`, `delta_pct`, `crosscheck_passed`

---

### G-03: SCHEMA_COMPLETENESS

**Input**: `ProviderResult.frame` columns and row count
**Logic**:

| Condition | Result |
|-----------|--------|
| All required columns present: date, open, high, low, close, volume | PASS |
| Required columns present, <30 rows | RED — insufficient history |
| Any required column missing | RED |
| Volume column all zeros | RED — likely delayed data |
| Close ≤ 0 | RED — invalid price |

**Required columns** (case-insensitive, mapped internally):
`date, open, high, low, close, volume`

**Audit evidence**: `column_check`, `row_count`, `volume_all_zero`, `close_invalid`

---

### G-04: CORP_ACTION_SANITY

**Input**: OHLCV frame — detect sudden drops >20% without recovery
**Logic**:

| Condition | Result |
|-----------|--------|
| No sudden drop detected | PASS |
| Drop 10–20% (corporate action suspected) | AMBER — flag for manual check |
| Drop >20% unexplained | AMBER — manual review required |

**Note**: This is a flag, not a blocker. Corporate actions (stock splits, dividends) cause legitimate price jumps. Manual review before trading.

**Audit evidence**: `corp_action_detected`, `drop_pct`, `action_type`

---

### G-05: MODEL_HEALTH

**Input**: `model_stats` from walk-forward model
**Logic**:

| Condition | Result |
|-----------|--------|
| AUC ≥ 0.55, Accuracy ≥ 0.50 | PASS |
| AUC 0.50–0.55 | AMBER |
| AUC < 0.50 or Accuracy < 0.50 | RED |
| Model failed to train | RED |

**Audit evidence**: `auc`, `accuracy`, `model_type`

---

### G-06: OOF_COVERAGE

**Input**: `model_stats.oof_coverage`
**Logic**:

| Condition | Result |
|-----------|--------|
| Coverage ≥ 70% | PASS |
| Coverage 50–70% | AMBER |
| Coverage < 50% | RED |

**Audit evidence**: `oof_coverage_pct`, `cv_gap`

---

### G-07: RISK_PLAN

**Input**: `RiskPlan` (stop, target, risk budget, R/R ratio)
**Logic**:

| Condition | Result |
|-----------|--------|
| Stop > 0, Target > Stop, R/R ≥ track threshold | PASS |
| R/R below track threshold but ≥ 1.5 | AMBER |
| Stop ≤ 0 or Target ≤ Stop | RED — invalid plan |
| R/R < 1.5 | AMBER — marginal plan |

**Track thresholds** (configurable):
- Track-S: R/R ≥ 2.0
- Track-L: R/R ≥ 1.5

**Audit evidence**: `stop_pct`, `tp2_pct`, `risk_reward`, `risk_budget_pct`

---

### G-08: BACKTEST_SANITY

**Input**: `backtest` results (return, Sharpe, MDD)
**Logic**:

| Condition | Result |
|-----------|--------|
| Sharpe ≥ 0, MDD < 20% | PASS |
| Sharpe < 0 but > -0.5, MDD < 20% | AMBER |
| MDD ≥ 20% | RED — risk exceeded |
| Sharpe ≤ -0.5 | AMBER — negative trend |

**Note**: AMBER backtest does not block — analyst reviews. RED always blocks.

**Audit evidence**: `backtest_return_pct`, `sharpe`, `mdd_pct`

---

### G-09: APPROVAL

**Input**: Analyst manually reviews AMBER flags
**Logic**:

| Condition | Result |
|-----------|--------|
| All gates PASS | APPROVED |
| Any gate RED | BLOCKED |
| AMBER gates all manually cleared by analyst | APPROVED_WITH_AMBER |
| AMBER not cleared | PENDING_REVIEW |

**Human-in-the-loop**: This gate requires analyst action. No automatic approval of AMBER candidates.

**Audit evidence**: `approval_status`, `analyst`, `cleared_flags`, `approval_timestamp`

---

### G-10: AUDIT_EVIDENCE

**Input**: `audit_log` completeness check
**Logic**:

| Condition | Result |
|-----------|--------|
| audit_log.jsonl has provider_attempt + recommend events for this run | PASS |
| Missing provider_attempt event | RED — trace broken |
| Missing recommend event | RED — trace broken |

**Audit evidence**: `audit_event_count`, `provider_event_present`, `recommend_event_present`

---

## Gate Summary Table

| Gate | PASS | AMBER | RED | ZERO |
|------|------|-------|-----|------|
| G-01 DATA_FRESHNESS | ≤1bd (KRX) / ≤1cd (NYSE) | 1–3bd stale KRX | >3bd stale / unknown | — |
| G-02 PRICE_CROSSCHECK | Δ ≤1.0% | Δ 1–3% | Δ >3% | — |
| G-03 SCHEMA_COMPLETENESS | All cols, ≥30 rows, valid prices | — | Missing col / <30 rows / zero vol / close≤0 | — |
| G-04 CORP_ACTION_SANITY | No drop | Drop 10–20% | — | Drop >20% unexplained |
| G-05 MODEL_HEALTH | AUC≥0.55, Acc≥0.50 | AUC 0.50–0.55 | AUC<0.50 or Acc<0.50 | — |
| G-06 OOF_COVERAGE | ≥70% | 50–70% | <50% | — |
| G-07 RISK_PLAN | Valid stop/target, R/R ≥ threshold | R/R marginal | Invalid plan | — |
| G-08 BACKTEST_SANITY | Sharpe≥0, MDD<20% | Sharpe<0, MDD<20% | MDD≥20% | — |
| G-09 APPROVAL | All PASS or cleared | AMBER cleared | Any RED | — |
| G-10 AUDIT_EVIDENCE | Full trace present | — | Trace broken | — |

---

## AMBER / RED Blocking Rules

| Verdict | When |
|---------|------|
| `AMBER_REVIEW_ONLY` | Any AMBER gate, no RED gates |
| `AMBER_WATCHLIST` | AMBER cleared but pending full review |
| `RED_*` | Any RED gate |
| `ZERO_RISK_PLAN_FAILED` | G-07 returns RED |

---

## Next Phase Gate

Phase 3 (Approval & Audit Design) entry requires:
- ✅ Q-1~Q-4 answered
- ✅ Phase 1 provider contract approved
- ⏳ This Phase 2 gate document needs approval

**User action needed**: Confirm gate thresholds (G-05 MODEL_HEALTH AUC cutoff, G-07 R/R thresholds, G-08 MDD threshold) are acceptable as-is, or specify changes.
