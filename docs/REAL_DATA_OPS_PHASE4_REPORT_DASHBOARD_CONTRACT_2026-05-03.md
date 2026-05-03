# Phase 4: Report & Dashboard Contract
## Real Data Ops Upgrade

**Date**: 2026-05-03
**Status**: ✅ APPROVED (2026-05-03) — report additions, dashboard fields, journal format confirmed
**Phase 1**: ✅ APPROVED | **Phase 2**: ✅ APPROVED | **Phase 3**: ✅ APPROVED

---

## 1. Recommendation Report Additions

### Markdown Report (`.md`)

Existing fields retained. Add new sections:

```markdown
## Approval Evidence
| Field | Value |
|-------|-------|
| Approval State | APPROVED |
| Analyst | analyst:user1 |
| Cleared Gates | — |
| Report Hash | sha256:abc123... |
| Snapshot Hash | sha256:def456... |

## KEVPE Risk Overlay
| Field | Value |
|-------|-------|
| Regime | GREEN |
| Score | 0.23 |
| Confidence | HIGH |
| E[RV] | +4.2% |
| CI | [-1.5%, +9.8%] |
| Reason | Low volatility window, positive pattern match |
```

---

### JSON Report (`recommendations_algo_v2_*.json`)

Existing fields retained. Add top-level fields:

```json
{
  "approval_state": "APPROVED",
  "analyst": "analyst:user1",
  "approver": null,
  "cleared_gates": [],
  "report_hash": "sha256:...",
  "snapshot_hash": "sha256:...",
  "approval_timestamp_utc": "2026-05-03T10:00:00+00:00",
  "journal_id": "JRN-2026-0503-005930-KS-S-001"
}
```

---

## 2. Dashboard Snapshot Additions

Existing `dashboard_snapshot.v1` schema extended with:

```json
{
  "schema_version": "dashboard_snapshot.v1",
  "gate_status": {
    "G-01_DATA_FRESHNESS": "PASS",
    "G-02_PRICE_CROSSCHECK": "PASS",
    "G-03_SCHEMA_COMPLETENESS": "PASS",
    "G-04_CORP_ACTION_SANITY": "AMBER",
    "G-05_MODEL_HEALTH": "AMBER",
    "G-06_OOF_COVERAGE": "PASS",
    "G-07_RISK_PLAN": "PASS",
    "G-08_BACKTEST_SANITY": "AMBER",
    "G-09_APPROVAL": "APPROVED",
    "G-10_AUDIT_EVIDENCE": "PASS"
  },
  "approval_state": "APPROVED",
  "analyst": "analyst:user1",
  "approval_timestamp_utc": "2026-05-03T10:00:00+00:00",
  "report_hash": "sha256:...",
  "snapshot_hash": "sha256:...",
  "journal_id": "JRN-2026-0503-005930-KS-S-001"
}
```

### Dashboard Display Rules

| Condition | Display |
|-----------|---------|
| Any gate RED | Red banner: "BLOCKED — [gate name]" |
| Any gate AMBER | Amber banner: "REVIEW REQUIRED — [gate name] cleared by analyst" |
| All PASS, APPROVED | Green: "APPROVED" badge |
| `screening_output_only` | Always visible — "SCREENING OUTPUT ONLY — MANUAL APPROVAL REQUIRED" |

---

## 3. Journal Output

For each approved candidate, write a journal entry:

```
journal/
  2026-05/
    JRN-2026-0503-005930-KS-S-001.json
    JRN-2026-0503-068270-KS-L-002.json
```

**Filename pattern**: `JRN-{YYYY}-{MMDD}-{TICKER}-{TRACK}-{SEQ}.json`

---

## 4. Ops-v1 Report Additions

Existing ops-v1 daily brief format extended:

```json
{
  "date": "2026-05-03",
  "candidates_submitted": 5,
  "candidates_approved": 3,
  "candidates_blocked": 1,
  "candidates_pending": 1,
  "gate_summary": {
    "G-01": "5/5 PASS",
    "G-02": "4/5 PASS, 1/5 AMBER",
    "G-07": "5/5 PASS"
  }
}
```

---

## 5. Next Phase Gate

Phase 5 (Implementation Readiness Review) entry requires:
- ✅ Phase 1 approved (provider contract)
- ✅ Phase 2 approved (gate design)
- ✅ Phase 3 approved (approval/audit)
- ⏳ Phase 4 approval pending: report additions, dashboard fields, journal format

**User action needed**: Confirm report additions and dashboard fields.

Reply: `confirm` = 수락 / `edit: <변경사항>` = 수정
