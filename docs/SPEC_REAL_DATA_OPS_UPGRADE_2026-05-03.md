# SPEC: Real Data Ops Upgrade

Status: Draft for review.

Source plan: `docs/plan_real_data_ops_upgrade_2026-05-03.md`

Source research: `C:\Users\jichu\Downloads\주식\deep-research-report.md`

Target folder: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

## Summary

This spec defines the next upgrade contract for `stock_rtx4060_unified`: real-data source policy, validation gates, human approval state, and append-only audit/journal evidence.

The system must remain report-only. It must not add broker execution, account actions, auto-trading, margin, options, short selling, or personalized financial advice.

Current baseline:

| Area | Current Evidence |
|---|---|
| Active CLI | `main.py`, `run.ps1`, `src/stock_rtx4060/main.py` |
| Provider abstraction | `src/stock_rtx4060/data_providers.py` |
| Audit JSONL | `src/stock_rtx4060/audit_log.py` |
| MCP adapter contract | `src/stock_rtx4060/mcp_adapter.py` |
| Recommendation engine | `src/stock_rtx4060/recommendation_engine.py` |
| Ops v1 workflow | `src/stock_rtx4060/ops_workflow.py` |
| Dashboard bridge | `src/stock_rtx4060/dashboard_bridge.py`, `dashboard/` |
| Regression tests | `tests/test_core.py`, `tests/test_audit_log.py`, `tests/test_data_providers.py`, `tests/test_mcp_adapter.py`, `tests/test_dashboard_bridge.py` |

## User Scenarios & Testing

### US-001 Official-source candidate review

Given an operator runs a future real-data candidate review
When provider data is loaded from approved official or primary sources
Then each candidate must include source, timestamp, provider, and freshness evidence
And a candidate with missing required source evidence must not become approval-ready.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Provider metadata contract validation. |
| Integration | Candidate report includes provider metadata and audit path. |
| Negative | Missing source timestamp returns AMBER/RED evidence. |

### US-002 Research fallback remains review-only

Given yfinance or another research fallback is used
When a candidate report is generated
Then the report must clearly mark the fallback source
And production approval must be blocked unless a separate approved primary source validates the data.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Fallback source policy returns review-only status. |
| Integration | Report includes fallback warning. |
| Negative | Fallback-only candidate cannot pass approval gate. |

### US-003 Multi-validation gate blocks unsafe candidates

Given a candidate has data, model, risk, or compliance failures
When the validation gate runs
Then the gate must return PASS, AMBER, RED, or ZERO
And ZERO must block the workflow and write incident/audit evidence.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Each gate returns expected status for valid and invalid input. |
| Integration | Failed candidate is excluded from approval queue. |
| Negative | Missing risk plan or failed leakage check returns ZERO. |

### US-004 Human approval state is required

Given a candidate passes data, model, risk, and compliance gates
When the workflow reaches approval
Then reviewer and approver decisions must be recorded before an approved state is created
And no broker order or account action may be created.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Allowed state transitions only. |
| Unit | Self-approval is rejected. |
| Integration | Approval artifact records reviewer, approver, timestamp, and reason. |

### US-005 Append-only audit and journal evidence is durable

Given any provider load, gate result, approval decision, or report generation event
When the system writes audit evidence
Then the event must be append-only, secret-masked, timestamped, and linked to the report or snapshot hash.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Secret masking covers fake tokens, keys, account IDs, bearer values, and private URLs. |
| Integration | Report path, audit path, and snapshot hash are linked. |
| Negative | Existing audit events are not overwritten. |

### US-006 Dashboard remains review-only

Given a dashboard snapshot contains gate and approval evidence
When the dashboard loads that snapshot
Then it must show report-only status, validation state, audit path, and approval state
And it must not show order buttons or broker actions.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Browser smoke | Snapshot loads and displays mode `report_only`. |
| Source check | No order button, broker action, account write, or auto-buy UI is introduced. |

## Requirements

### Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FR-001 | Existing CLI commands must remain available: `recommend`, `ops-v1`, `dashboard-export`, `env`, `benchmark`, `report`, `predict`, `journal`, and `self-test`. | US-001, US-006 |
| FR-002 | Real-data providers must emit metadata for source, provider, ticker, period or date range, timestamp, freshness, and status. | US-001 |
| FR-003 | The data-source policy must distinguish approved primary/official sources from research fallback sources. | US-001, US-002 |
| FR-004 | yfinance or fallback-only data must not be sufficient for production approval without cross-check evidence. | US-002 |
| FR-005 | Validation gates must support PASS, AMBER, RED, and ZERO statuses. | US-003 |
| FR-006 | Gates must cover data freshness, price cross-check, schema completeness, corporate action sanity, liquidity, leakage, model health, OOF quality, backtest robustness, risk plan, compliance, approval, and audit evidence. | US-003 |
| FR-007 | ZERO status must block approval and write audit evidence. | US-003 |
| FR-008 | Approval state must require human reviewer and approver evidence before an approved state is created. | US-004 |
| FR-009 | The system must prevent self-approval unless a separate policy explicitly allows it. | US-004 |
| FR-010 | Audit and journal events must be append-only and secret-masked. | US-005 |
| FR-011 | Reports must include audit path, provider evidence, gate status, and report-only disclaimer. | US-001, US-005 |
| FR-012 | Dashboard snapshots must remain `report_only` and may include gate and approval evidence. | US-006 |
| FR-013 | No feature may create broker orders, auto-trading, account writes, margin, options, short selling, or personalized advice. | US-004, US-006 |

### Non-Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| NFR-001 | Backward compatibility: current synthetic validation and existing tests must continue to pass. | US-001 |
| NFR-002 | Auditability: a reviewer must trace each recommendation to source data, gate results, approval state, and report hash. | US-005 |
| NFR-003 | Security: no secrets, tokens, provider keys, account IDs, private URLs, or private financial identifiers may appear in generated logs. | US-005 |
| NFR-004 | Financial safety: all outputs remain screening or review artifacts only. | US-004, US-006 |
| NFR-005 | Failure transparency: missing data, failed checks, and fallback-only data must be visible in reports. | US-001, US-002, US-003 |
| NFR-006 | Extensibility: future MCP server runtime, broker integration, or paid data-provider credentials require separate approval. | US-004 |

## Assumptions & Dependencies

| ID | Item | Status |
|---|---|---|
| AD-001 | Active target folder is `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`. | Verified |
| AD-002 | Source research document is `C:\Users\jichu\Downloads\주식\deep-research-report.md`. | Verified |
| AD-003 | Phase 1 OpenBB/audit/MCP adapter contract already exists. | Verified from local source and reports |
| AD-004 | Primary paid price provider is selected. | [NEEDS CLARIFICATION: choose provider or keep contract feed as future placeholder] |
| AD-005 | SEC EDGAR identity and fair-access user-agent policy are defined. | [NEEDS CLARIFICATION: define operator identity/contact policy before implementation] |
| AD-006 | OpenDART key availability is known. | [NEEDS CLARIFICATION: key exists, not needed yet, or KR support postponed] |
| AD-007 | Storage choice is approved. | [NEEDS CLARIFICATION: JSONL only, SQLite, DuckDB, or Postgres] |
| AD-008 | Gate thresholds are approved. | [NEEDS CLARIFICATION: freshness window, price tolerance, OOF thresholds, liquidity minimums, and risk thresholds] |
| AD-009 | Target universe is approved. | [NEEDS CLARIFICATION: US only, KR only, or both] |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | Existing package still compiles. | `.\.venv\Scripts\python.exe -m compileall main.py src tests` exits `0`. |
| SC-002 | Existing tests still pass. | `.\.venv\Scripts\python.exe -m pytest -q` passes. |
| SC-003 | Existing `recommend` synthetic smoke still works. | Synthetic run creates recommendation Markdown, JSON, and audit JSONL. |
| SC-004 | Existing `ops-v1` synthetic smoke still works. | Ops v1 run creates recommendation reports, daily brief, approval template, ZERO log, summary JSON, and audit JSONL. |
| SC-005 | Fallback-only data cannot become production approval-ready. | Gate test returns AMBER/RED for fallback-only approval attempt. |
| SC-006 | ZERO gate blocks unsafe candidate. | Gate test writes audit event and excludes candidate from approval queue. |
| SC-007 | Approval requires reviewer and approver evidence. | Approval test rejects missing reviewer, missing approver, and self-approval where prohibited. |
| SC-008 | Audit events are append-only and masked. | Test appends multiple events and confirms fake secrets are masked. |
| SC-009 | Dashboard remains report-only. | Browser or source check confirms no order buttons or broker action fields. |
| SC-010 | Documentation stays aligned. | README, SYSTEM_ARCHITECTURE, LAYOUT, SETUP, and CHANGELOG explain the approved scope after implementation. |

## Non-Goals

- Do not add broker API integration.
- Do not add order placement, auto-buy, auto-sell, account access, margin, options, short selling, or leveraged account behavior.
- Do not turn reports into personalized financial advice.
- Do not require OpenBB or any primary provider for offline synthetic validation.
- Do not start a local MCP server in this phase.
- Do not store real provider credentials in the repository.
- Do not make TensorFlow/LSTM a production default.

## Open Questions

| ID | Question | Impact |
|---|---|---|
| OQ-001 | Which target universe is first: US only, KR only, or both? | Affects provider scope and tests. |
| OQ-002 | Which source is the primary price source? | Affects price cross-check and approval readiness. |
| OQ-003 | Is OpenDART included in the first implementation slice? | Affects Korean filing support and secret handling. |
| OQ-004 | What storage layer should be used for append-only approval/audit state? | Affects migration and durability tests. |
| OQ-005 | What exact gate thresholds are acceptable? | Affects PASS/AMBER/RED/ZERO behavior. |
| OQ-006 | Who may act as reviewer and approver in local operation? | Affects role and self-approval rules. |

## Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-03 | The source document is `deep-research-report.md`. | User-provided path |
| 2026-05-03 | The current implementation remains report-only and includes Phase 1 provider/audit/MCP adapter work. | Local source and docs |
| 2026-05-03 | This spec is a draft and does not authorize implementation while critical open questions remain. | Spec guardrail |

## Reviewer Checklist

| Check | Status |
|---|---|
| Mandatory sections present | PASS |
| Stable FR/NFR/SC IDs present | PASS |
| Given/When/Then scenarios present | PASS |
| Measurable success criteria present | PASS |
| Critical ambiguity visible | PASS |
| Broker/order execution excluded | PASS |
| Approval-ready for implementation | FAIL: open questions remain |

## Approval Readiness

Status: Not approval-ready for implementation.

Required decisions before implementation:

1. Target universe.
2. Primary price source.
3. OpenDART inclusion.
4. Storage layer.
5. Gate thresholds.
6. Reviewer/approver rule.
