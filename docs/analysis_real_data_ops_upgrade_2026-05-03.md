# Real Data Ops Upgrade Analysis

Date: 2026-05-03

Source document: `C:\Users\jichu\Downloads\주식\deep-research-report.md`

Target folder: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

## Executive Summary

`deep-research-report.md` proposes the next operating layer above the current report-only CLI: official or primary data ingestion, stronger validation gates, human approval, and append-only audit/journal records.

Current code already implements the first slice:

| Existing Capability | Evidence |
|---|---|
| Report-only CLI | `main.py`, `run.ps1`, `src/stock_rtx4060/main.py` |
| Optional OpenBB provider path | `src/stock_rtx4060/data_providers.py`, `requirements-openbb.txt` |
| Audit JSONL | `src/stock_rtx4060/audit_log.py` |
| MCP-safe adapter contract | `src/stock_rtx4060/mcp_adapter.py` |
| Ops v1 manual review artifacts | `src/stock_rtx4060/ops_workflow.py` |
| Dashboard snapshot bridge | `src/stock_rtx4060/dashboard_bridge.py`, `dashboard/` |
| Regression coverage | `tests/test_audit_log.py`, `tests/test_data_providers.py`, `tests/test_mcp_adapter.py`, `tests/test_dashboard_bridge.py`, `tests/test_core.py` |

The next safe unit is a Phase 2 design for real-data operating gates, not broker execution.

## Planner Summary

Objective: turn the research report into an approval-ready Plan and Spec for a real-data operational upgrade while preserving `screening_output_only` and manual approval boundaries.

Success criteria:

| Criterion | Meaning |
|---|---|
| Scope clarity | Phase 2 does not reopen broker, account, order, margin, options, or auto-trading behavior. |
| Traceability | Every planned capability maps back to `deep-research-report.md` or current source files. |
| Testability | Plan and Spec include measurable checks before future implementation starts. |
| Ambiguity visibility | Missing provider credentials, primary price feed, thresholds, and storage choices stay visible as open questions. |

Lane definitions:

| Lane | Scope |
|---|---|
| Data / Model | Official data source policy, source priority, feature freshness, leakage-safe extension, model promotion gates. |
| Risk / Compliance | Human-in-the-loop approval, ZERO/RED/AMBER rules, no broker execution, secret masking, audit requirements. |
| Operations / Execution | CLI workflows, storage, reports, dashboard bridge, tests, rollout evidence. |

Execution mode: single-agent local analysis in this session. Real parallel subagents were not started because the user invoked analysis skills but did not explicitly request live subagent execution in this turn.

## Specialist Findings

### Data / Model Lane

| Finding | Evidence | Recommendation |
|---|---|---|
| The current provider layer is a good insertion point. | `data_providers.py` already supports `synthetic`, `yfinance`, `openbb`, and `auto`. | Extend provider contracts before adding new downstream model logic. |
| The research report requires official-source priority. | `deep-research-report.md` lists SEC EDGAR, OpenDART, KRX, contract price feeds, issuer IR, and yfinance fallback. | Treat yfinance as research fallback, not production approval evidence. |
| Existing leak-safe model design must be preserved. | Current docs and report describe feature lag, walk-forward CV, OOF probability, and gap/embargo principles. | New filing/fundamental features must be joined by as-of timestamp and validated through tests. |

### Risk / Compliance Lane

| Finding | Evidence | Recommendation |
|---|---|---|
| The current safety boundary is still correct. | README and generated reports use `screening_output_only`, `manual_approval_required`, and no broker execution. | Keep Phase 2 report-only until separate broker-safety approval exists. |
| The research report calls for stronger approval state. | It defines Analyst, Reviewer, Approver, Auditor, and SysAdmin roles. | Model approval as a state machine and append-only journal, not as a broker action. |
| Audit records must be durable and masked. | `audit_log.py` masks secrets; the research report calls for immutable audit/journal. | Keep JSONL audit now, plan SQLite or DuckDB-backed append-only store as a separate approved step. |

### Operations / Execution Lane

| Finding | Evidence | Recommendation |
|---|---|---|
| The existing CLI can remain the operator entrypoint. | `run.ps1`, `recommend`, `ops-v1`, and `dashboard-export` already exist. | Add future commands only after Plan/Spec approval. |
| Dashboard should stay review-only. | `dashboard_snapshot.v1` is loaded through a file bridge and marks mode `report_only`. | Add gate and approval status fields to snapshots later, without order buttons. |
| Future implementation will be cross-module. | Likely touches providers, gates, approval/journal, reports, CLI, tests, docs, and dashboard. | Use a parallel ownership split for implementation after Plan/Spec approval. |

## Dispatch Recommendation

Chosen mode for this turn: document-first direct execution.

Future implementation mode: parallel team execution.

| Item | Estimate |
|---|---|
| Likely future changed files | 10-18 files |
| Coupling risk | Medium-High: providers, recommendation engine, reports, CLI, tests, and docs share contracts |
| API or CLI risk | Medium: new commands or flags may affect operator workflow |
| Rollback risk | Medium: provider and approval state must be additive and default-safe |

Future ownership split:

| Owner Lane | Files / Modules |
|---|---|
| Data provider owner | `data_providers.py`, provider config, provider tests |
| Gate owner | new or existing gate module, `recommendation_engine.py`, gate tests |
| Approval/audit owner | approval state module, `audit_log.py`, journal/report tests |
| CLI/report owner | `main.py`, `ops_workflow.py`, `reports.py`, docs |
| Dashboard owner | `dashboard_bridge.py`, dashboard snapshot docs, browser smoke |
| Lead reviewer | final cross-module consistency and regression validation |

## Verifier Verdict

| Check | Verdict |
|---|---|
| No code implementation included | PASS |
| Plan and Spec can be derived from source document | PASS |
| Safety boundary preserved | PASS |
| Critical unknowns visible | PASS |
| Approval-ready for implementation | FAIL until open questions are resolved |

## Final Recommendation

Create Phase 2 Plan and Spec documents for `real-data-ops-upgrade` and keep them separate from the already implemented Phase 1 MCP + OpenBB + audit work.

Do not implement code until the Plan/Spec open questions are reviewed.

## Assumptions And Evidence Gaps

| Item | Status |
|---|---|
| Primary paid price provider | Assumption: not selected yet. |
| OpenDART key availability | Assumption: not provided in this repo. |
| SEC EDGAR usage identity / fair-access policy | Assumption: not configured yet. |
| Production storage choice | Open question: JSONL only, SQLite, DuckDB, or Postgres. |
| Exact gate thresholds | Open question: must be approved before implementation. |
| Target universe | Open question: US only, KR only, or both. |
