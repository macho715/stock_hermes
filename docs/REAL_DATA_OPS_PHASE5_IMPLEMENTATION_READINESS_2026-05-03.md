# Phase 5: Implementation Readiness Review
## Real Data Ops Upgrade

**Date**: 2026-05-03
**Status**: ✅ Phase 5 CONFIRMED — Task Group A+B IMPLEMENTED (2026-05-03)
**Phase 1–4**: ✅ ALL APPROVED
**Canonical document path**: `stock_rtx4060_unified/docs/REAL_DATA_OPS_PHASE5_IMPLEMENTATION_READINESS_2026-05-03.md`

This file is the Phase 5 readiness document referenced by the root `CHANGELOG.md`.
There is no separate active root document named `docs/PHASE5_IMPLEMENTATION_READINESS.md`.

---

## 1. Approved Deliverables Summary

| Phase | Document | Status |
|-------|----------|--------|
| Phase 0 | Baseline confirmation | ✅ Tests 19/19 PASS, active package confirmed |
| Phase 1 | `REAL_DATA_OPS_PHASE1_SOURCE_CONTRACT_2026-05-03.md` | ✅ APPROVED |
| Phase 2 | `REAL_DATA_OPS_PHASE2_VALIDATION_GATE_DESIGN_2026-05-03.md` | ✅ APPROVED |
| Phase 3 | `REAL_DATA_OPS_PHASE3_APPROVAL_AUDIT_DESIGN_2026-05-03.md` | ✅ APPROVED |
| Phase 4 | `REAL_DATA_OPS_PHASE4_REPORT_DASHBOARD_CONTRACT_2026-05-03.md` | ✅ APPROVED |

---

## 2. Implementation Task Split

### Task Group A: Provider & Data (Phase 1 owner) — ✅ IMPLEMENTED

| Task | File | Changes |
|------|------|---------|
| T-A1 | `data_providers.py` | ✅ Add `pykrx` and `fdr` to `ALLOWED_PROVIDERS`, add `_load_pykrx()`, `_load_fdr()` |
| T-A2 | `data_providers.py` | ✅ Add provider metadata: `ticker_type`, `data_freshness_minutes`, `source_timestamp` |
| T-A3 | `data_providers.py` | ✅ Implement fallback chain: PyKRX → FDR → FAIL |
| T-A4 | `audit_log.py` | ✅ `provider_result_metadata` already part of AuditEvent.metadata |
| T-A5 | Tests | ⏳ Pending |

### Task Group B: Validation Gates (Phase 2 owner) — ✅ IMPLEMENTED

| Task | File | Changes |
|------|------|---------|
| T-B1 | `validation_gates.py` (NEW) | ✅ G-01 DATA_FRESHNESS — freshness check |
| T-B2 | `validation_gates.py` | ✅ G-02 PRICE_CROSSCHECK — dual-source delta check |
| T-B3 | `validation_gates.py` | ✅ G-03 SCHEMA_COMPLETENESS — columns/rows/volume check |
| T-B4 | `validation_gates.py` | ✅ G-04 CORP_ACTION_SANITY — sudden drop detection |
| T-B5 | `validation_gates.py` | ✅ G-05 MODEL_HEALTH — AUC/accuracy check |
| T-B6 | `validation_gates.py` | ✅ G-06 OOF_COVERAGE — coverage check |
| T-B7 | `validation_gates.py` | ✅ G-07 RISK_PLAN — stop/target/RR check |
| T-B8 | `validation_gates.py` | ✅ G-08 BACKTEST_SANITY — Sharpe/MDD check |
| T-B9 | `validation_gates.py` | ✅ G-09 APPROVAL — state machine |
| T-B10 | `validation_gates.py` | ✅ G-10 AUDIT_EVIDENCE — trace completeness |
| T-B11 | Tests | ⏳ Pending |

### Task Group C: Approval & Audit (Phase 3 owner)

| Task | File | Changes |
|------|------|---------|
| T-C1 | `audit_log.py` | Add `ApprovalEvent` dataclass, `ApprovalEventType` enum |
| T-C2 | `audit_log.py` | Add secret masking for BL, DN, PO, account_id, token, email, phone |
| T-C3 | `journal.py` (NEW) | Journal entry writer, SHA-256 hashing, journal_id generator |
| T-C4 | `recommendation_engine.py` | Wire approval_state into `RecommendationResult` |
| T-C5 | `dashboard_bridge.py` | Add `gate_status`, `approval_state`, `report_hash` fields |
| T-C6 | Tests | `test_secret_masking.py`, `test_journal.py`, `test_approval_state.py` |

### Task Group D: Report & Dashboard (Phase 4 owner)

| Task | File | Changes |
|------|------|---------|
| T-D1 | `recommendation_engine.py` | Add `report_hash`, `snapshot_hash`, `approval_timestamp` to JSON output |
| T-D2 | `dashboard_bridge.py` | Add `gate_status` dict to snapshot schema |
| T-D3 | `ops_v1.py` (or existing) | Add gate_summary and candidate counts to daily brief |
| T-D4 | `stock-pred-v5/` | Update `RecommendationCard.jsx` to display approval_state badge |
| T-D5 | Tests | `test_report_hash.py`, `test_dashboard_snapshot_v2.py` |

### Task Group E: Integration & E2E

| Task | Description |
|------|-------------|
| T-E1 | Full smoke test: `python main.py recommend --data-provider pykrx --universe 005930.KS` |
| T-E2 | Full smoke test: `python main.py recommend --data-provider synthetic --universe SYNTH-A` |
| T-E3 | Dashboard smoke: load snapshot, verify gate_status, verify approval_state badge |
| T-E4 | Regression: all existing tests must PASS (19/19 + new gate tests) |

---

## 3. Dependencies Between Task Groups

```
T-A1 → T-A2 → T-A3    (Provider chain)
T-B1 → T-B2 → ... → T-B11  (Gates depend on provider metadata from T-A2)
T-C1 → T-C2 → T-C3 → T-C4 → T-C5  (Audit → Journal → Integration)
T-D1 → T-D2 → T-D3 → T-D4       (Reports → Dashboard → Card)
T-E1 → T-E2 → T-E3 → T-E4       (E2E smoke — run last)
```

**Parallel execution**: Groups A and B can run in parallel. Group C depends on A+B. Group D depends on C. Group E is final.

---

## 4. Implementation Order Recommendation

1. **Week 1**: Task Group A (provider) + T-B1 through T-B4 (basic gates)
2. **Week 2**: Task Group B (remaining gates) + Task Group C (audit)
3. **Week 3**: Task Group D (reports/dashboard) + integration
4. **Week 4**: Task Group E (smoke + regression) + Phase 5 closeout

---

## 5. Remaining [NEEDS CLARIFICATION] Items

| Item | Area | Status |
|------|------|--------|
| PyKRX ticker list for universe | Phase 1 | ⚠️ KRX universe not yet defined — use "all KRX" for Phase 1 |
| FinanceDataReader installation | Phase 1 | ⚠️ Package not yet installed |
| Gate threshold backtest evidence | Phase 2 | ⚠️ AUC 0.55 cutoff not yet validated by backtest |
| Analyst/Reviewer/Approver user IDs | Phase 3 | ⚠️ Role mapping to actual user IDs pending |
| Report storage path | Phase 4 | ⚠️ Default: `reports/{YYYY-MM}/` — confirm? |
| Dashboard host URL | Phase 4 | ⚠️ Vite dev server vs. production URL — confirm? |

---

## 6. Critical Path Items (must resolve before Phase 1 implementation)

| Item | Owner | Blocker? |
|------|-------|----------|
| FinanceDataReader installation | ✅ Agent | ✅ RESOLVED — installed and verified (`import FinanceDataReader` OK) |
| KRX ticker universe | ✅ User | ✅ RESOLVED — "all KRX" accepted for Phase 1 scope |

---

## 7. Phase 5 Approval Checklist

- [x] All 4 phase documents approved
- [x] FinanceDataReader installed (`pip install finance-datareader`) — verified: `import FinanceDataReader` OK
- [x] PyKRX ticker universe defined or "all KRX" accepted — confirmed by user (Q-2=Y)
- [x] No `[NEEDS CLARIFICATION]` items that block implementation remain
- [x] Implementation task list reviewed and accepted

---

## 8. Implementation Evidence

- FDR import verified: `.venv/Scripts/python.exe -c "import FinanceDataReader; print('OK')"` → OK
- PyKRX import verified: `.venv/Scripts/python.exe -c "from pykrx import stock; print('OK')"` → OK (KRX login failure is expected — no KRX_ID/PW needed for historical OHLCV)
- `main.py --test`: PASS
- `pytest -q`: 19/19 PASS
- Gate smoke tests: G-01 PASS, G-02 PASS (Δ=0.139%), G-05 PASS, G-07 PASS (RR=2.5 Track-S)

---

## 9. Next Action After Phase 5

Task Group A+B ✅ IMPLEMENTED. Next steps (pending user confirmation to proceed):

1. **Task Group C** (Audit & Approval wiring): Wire `ApprovalEvent`, `ApprovalEventType`, secret masking into `audit_log.py`; integrate journal.py into `recommendation_engine.py`
2. **Task Group D** (Report & Dashboard): Add `report_hash`, `snapshot_hash`, `approval_timestamp` to JSON output; wire `gate_status` dict into dashboard_bridge; update RecommendationCard.jsx with approval_state badge
3. **Task Group E** (E2E smoke): Full smoke test with `--data-provider pykrx --universe 005930.KS`

**User action needed**: Confirm to proceed with Task Group C, or specify changes.
