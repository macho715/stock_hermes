# Real Data Ops Upgrade Plan

Date: 2026-05-03

Source document: `C:\Users\jichu\Downloads\주식\deep-research-report.md`

Target folder: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

Status: Draft for review.

## Overview

Purpose: convert the current report-only screening CLI into a stronger real-data review workflow by adding official-source data policy, validation gates, human approval state, and durable audit/journal evidence while keeping broker execution out of scope.

## Goals

| Goal | Description |
|---|---|
| G-001 | Preserve the current `screening_output_only` and manual-review operating boundary. |
| G-002 | Define a real-data source policy that prioritizes official or primary sources before research fallbacks. |
| G-003 | Define validation gates for data freshness, price cross-check, schema completeness, corporate actions, model health, risk plan, approval, and audit evidence. |
| G-004 | Define a human-in-the-loop approval workflow before any recommendation can move from review to approved state. |
| G-005 | Define append-only audit/journal requirements that are testable and secret-safe. |
| G-006 | Keep existing CLI, synthetic validation, OpenBB optional path, and dashboard snapshot bridge usable. |

## Scope

### In Scope

| Area | Included Work |
|---|---|
| Data source policy | SEC EDGAR, OpenDART, KRX, contract price feed as future primary sources; yfinance as research fallback. |
| Provider contract | Additive provider and metadata requirements for source, timestamp, status, and error reason. |
| Validation gates | PASS/AMBER/RED/ZERO gate definitions before approval. |
| Approval workflow | Analyst, Reviewer, Approver, Auditor, SysAdmin role boundary from the research report. |
| Audit/journal | Append-only event requirements, report hash, snapshot hash, and secret masking expectations. |
| CLI/report docs | Future command shape and output evidence expectations. |
| Dashboard bridge | Future snapshot fields for gate status and approval state; no order buttons. |
| Tests | Provider contract, gate behavior, approval state, audit masking, and regression checks. |

### Out of Scope

| Area | Excluded Work |
|---|---|
| Broker execution | No broker API, no order placement, no auto-buy, no auto-sell. |
| Account actions | No margin, options, short selling, leveraged account behavior, or account-affecting writes. |
| Full MCP server | Phase 1 remains adapter contract only; server runtime needs separate approval. |
| Paid data contract | No paid provider credential, secret, or internal URL is assumed. |
| TensorFlow production | TensorFlow/LSTM remains optional research only unless WSL2/Linux GPU validation is approved. |
| Personalized advice | Outputs remain screening reports for manual review. |

## Constraints

| Constraint | Source / Reason |
|---|---|
| `screening_output_only` must remain visible. | Current code and docs use report-only recommendation output. |
| Existing `recommend`, `ops-v1`, and `dashboard-export` must keep working. | Current unified package operator path. |
| OpenBB remains optional. | Existing `requirements-openbb.txt` and Phase 1 plan/spec. |
| Synthetic validation must not require internet or credentials. | Existing tests and smoke workflows. |
| Audit output must mask secrets and account identifiers. | Current `audit_log.py` and security boundary. |
| Assumption: primary price provider is not selected. | The research report marks contract feed as an assumption. |
| Assumption: exact gate thresholds are not approved. | The research report provides candidate gates, not implementation-approved thresholds. |

## Phases

| Phase | Name | Objective | Exit Criteria |
|---:|---|---|---|
| 0 | Baseline confirmation | Confirm current Phase 1 provider/audit/MCP adapter and dashboard bridge evidence. | Current tests and docs are referenced in the implementation brief. |
| 1 | Source contract design | Define data source priorities, provider metadata, freshness rules, and fallback states. | Plan/Spec questions for providers and thresholds are resolved. |
| 2 | Validation gate design | Define DATA_FRESHNESS, PRICE_CROSSCHECK, SCHEMA_COMPLETENESS, CORP_ACTION_SANITY, MODEL_HEALTH, OOF_QUALITY, RISK_PLAN, APPROVAL, and AUDIT behavior. | Gate table has measurable PASS/AMBER/RED/ZERO rules. |
| 3 | Approval and audit design | Define approval state machine, role permissions, append-only events, report hash, and journal fields. | State transitions and audit fields are testable. |
| 4 | Report and dashboard contract | Define Markdown/JSON/dashboard snapshot additions for gate status and approval evidence. | No dashboard order surface is introduced. |
| 5 | Implementation readiness review | Produce implementation task split and validation checklist. | No critical `[NEEDS CLARIFICATION]` remains. |

## Tasks

| Task | Owner Lane | Output |
|---|---|---|
| T-001 | Lead | Review `deep-research-report.md`, current Phase 1 docs, and active source files. |
| T-002 | Data provider owner | Draft source priority and provider metadata contract. |
| T-003 | Data provider owner | Define yfinance research-fallback behavior and production-approval limits. |
| T-004 | Gate owner | Draft gate names, inputs, outputs, and failure actions. |
| T-005 | Gate owner | Define threshold placeholders and mark unresolved values as `[NEEDS CLARIFICATION]`. |
| T-006 | Approval/audit owner | Draft role matrix and allowed state transitions. |
| T-007 | Approval/audit owner | Define append-only audit fields, hash fields, and secret masking checks. |
| T-008 | CLI/report owner | Define additive CLI/report output changes without breaking existing commands. |
| T-009 | Dashboard owner | Define dashboard snapshot additions for gate and approval evidence. |
| T-010 | QA owner | Define regression, smoke, and negative tests. |
| T-011 | Lead | Run cross-document review before implementation starts. |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Provider source not selected | Gate implementation could become speculative. | Keep provider choice as open question until approved. |
| Secrets in provider config | Audit or logs could expose sensitive values. | Keep example config non-secret and test masking with fake secrets. |
| Gate thresholds overfit | Candidates may be blocked or approved incorrectly. | Treat thresholds as configurable and require backtest evidence. |
| Approval workflow scope drift | Could be misread as broker authorization. | Keep approval state separate from order execution. |
| Dashboard misinterpretation | User may treat dashboard output as trade instruction. | Preserve report-only label and no order buttons. |
| Cross-module implementation risk | Providers, gates, reports, CLI, and tests share contracts. | Use parallel ownership split and final integration review. |

## Review Criteria

| Criterion | Required Result |
|---|---|
| Scope check | No broker, account, order, margin, options, or auto-trading behavior appears. |
| Source check | Every data-source claim maps to the research report or current code. |
| Compatibility check | Existing `recommend`, `ops-v1`, `dashboard-export`, and synthetic validation remain part of the plan. |
| Ambiguity check | Missing thresholds, provider credentials, target universe, and storage decisions are visible. |
| Testability check | Each future implementation phase has measurable tests. |
| Security check | Secret masking and no plaintext credentials are explicit. |

## Deliverables

| Deliverable | Path |
|---|---|
| Analysis artifact | `docs/analysis_real_data_ops_upgrade_2026-05-03.md` |
| Plan draft | `docs/plan_real_data_ops_upgrade_2026-05-03.md` |
| Spec draft | `docs/SPEC_REAL_DATA_OPS_UPGRADE_2026-05-03.md` |
| Future implementation task document | Assumption: to be created only after Plan/Spec approval. |

## Approval Readiness

Status: Not approval-ready for implementation.

Reason: primary price provider, target universe, storage choice, approval roles, and gate thresholds still need explicit approval.
