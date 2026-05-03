# Phase 3: Approval & Audit Design
## Real Data Ops Upgrade

**Date**: 2026-05-03
**Status**: ✅ APPROVED (2026-05-03) — role matrix, state machine, masking, journal confirmed
**Phase 1**: ✅ APPROVED | **Phase 2**: ✅ APPROVED

---

## 1. Approval State Machine

```
PENDING_REVIEW
    │
    ├─── all gates PASS ────────────────────→ APPROVED
    │
    ├─── any gate RED ──────────────────────→ BLOCKED
    │
    ├─── AMBER gates cleared by analyst ──→ APPROVED_WITH_AMBER
    │
    └─── AMBER gates NOT cleared ───────────→ PENDING_REVIEW (remains)
```

### State Definitions

| State | Description | Is actionable? |
|-------|-------------|---------------|
| `PENDING_REVIEW` | Candidate passed all RED gates, has ≥1 AMBER | Yes — analyst must act |
| `APPROVED` | All gates PASS, analyst approved | Yes — moves to report |
| `APPROVED_WITH_AMBER` | All RED gates cleared, AMBER cleared explicitly | Yes — analyst acknowledged risk |
| `BLOCKED` | ≥1 RED gate failed | No — report shows blocked reason |
| `PENDING_REVIEW` | AMBER gates uncleared after 1 business day | Yes — escalation to reviewer |

---

## 2. Role Matrix

| Role | Can view | Can APPROVE | Can clear AMBER | Can BLOCK | Can escalate |
|------|---------|-----------|----------------|-----------|-------------|
| **Analyst** | ✅ All | ✅ PENDING → APPROVED | ✅ AMBER → cleared | ❌ | ✅ → Reviewer |
| **Reviewer** | ✅ All | ✅ BLOCKED → APPROVED | ✅ All AMBER | ✅ RED gates | ✅ → Approver |
| **Approver** | ✅ All | ✅ FINAL | ✅ All | ✅ All | ❌ |
| **Auditor** | ✅ audit logs | ❌ | ❌ | ❌ | ❌ |
| **SysAdmin** | ✅ config only | ❌ | ❌ | ❌ | ❌ |

---

## 3. State Transition Events

Each transition writes an append-only event to `audit_log.jsonl`:

```python
@dataclass
class ApprovalEvent:
    event_type: Literal[
        "approval_submitted",
        "approval_approved",
        "approval_approved_with_amber",
        "approval_blocked",
        "approval_escalated",
        "amber_cleared",
    ]
    ticker: str
    track: str
    from_state: str
    to_state: str
    actor: str          # role:user_id
    timestamp: str       # ISO UTC
    cleared_gates: list[str] | None  # for amber_cleared
    reason: str | None
    hash_report: str | None   # SHA-256 of recommendation JSON at approval time
    hash_snapshot: str | None # SHA-256 of dashboard snapshot at approval time
```

---

## 4. Append-Only Audit Requirements

| Requirement | Description |
|-------------|-------------|
| No event deletion | `audit_log.jsonl` is append-only — no `sed`, `awk`, or manual edits |
| No overwriting | Once written, `message`, `status`, `hash_*` fields cannot be changed |
| Secret masking | Account IDs, tokens, BL numbers, PO numbers masked in audit events |
| Report hash | SHA-256 of recommendation JSON frozen at approval time |
| Snapshot hash | SHA-256 of dashboard snapshot frozen at approval time |
| Sequential IDs | Each event has an incrementing `event_id` |

---

## 5. Secret Masking Rules

Fields automatically masked in audit output:

| Field name pattern | Masked as |
|--------------------|-----------|
| `account_id*` | `ACCT_***` |
| `token*` | `TOKEN_***` |
| `password*` | `PWD_***` |
| `po_number*`, `po_*` | `PO_***` |
| `bl_number*`, `bl_*` | `BL_***` |
| `dn_number*`, `dn_*` | `DN_***` |
| `email*` | `EMAIL_***` |
| `phone*` | `PHONE_***` |

---

## 6. Report Hash & Journal

At approval time, the following hashes are recorded:

```
report_hash = SHA-256(open(recommendations_algo_v2_*.json).read())
snapshot_hash = SHA-256(open(dashboard_snapshot.json).read())
```

These create an immutable link between:
- Approval event in audit log
- Recommendation JSON file
- Dashboard snapshot file

**Verification**: Any future audit can re-hash the files and compare against `audit_log.jsonl` to prove the report has not been altered.

---

## 7. Journal Fields (Recommendation Journal Entry)

For each approved recommendation, the journal entry includes:

```json
{
  "journal_id": "JRN-2026-0503-005930-KS-S-001",
  "generated_at_utc": "2026-05-03T10:00:00+00:00",
  "ticker": "005930.KS",
  "track": "S",
  "verdict": "ELIGIBLE_RECOMMENDATION",
  "approval_state": "APPROVED",
  "analyst": "analyst:user1",
  "approver": null,
  "cleared_gates": [],
  "report_hash": "sha256:abc123...",
  "snapshot_hash": "sha256:def456...",
  "kevpe_regime": "GREEN",
  "kevpe_score": 0.23,
  "risk_plan": {
    "entry": 72000,
    "stop": 69120,
    "tp2": 79200,
    "risk_reward": 2.5
  },
  "position_value": 18750.00,
  "quantity": 153
}
```

---

## 8. Next Phase Gate

Phase 4 (Report & Dashboard Contract) entry requires:
- ✅ Phase 1 approved
- ✅ Phase 2 approved
- ⏳ Phase 3 approval pending: role matrix, state machine, secret masking, journal format

**User action needed**: Confirm role matrix and journal fields are acceptable.

Reply: `confirm` = 수락 / `edit: <변경사항>` = 수정
