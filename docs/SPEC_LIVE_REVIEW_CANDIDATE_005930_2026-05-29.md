# SPEC - LIVE_REVIEW_CANDIDATE Gate for 005930.KS

Feature ID: `live-review-candidate-005930`

Created: 2026-05-29

Status: Draft. Not approved.

Input plan: `docs/LIVE_REVIEW_CANDIDATE_PLAN_005930_20260529.md`

Owner: Codex Spec draft using `spec-studio`.

Version: v0.1.0

## Summary

### Problem

005930.KS has reached `PAPER_PASS` according to the input plan, but `PAPER_PASS` is not enough to put the candidate into a human live-review table.

The remaining problem is evidence quality. The system must prove that the candidate survives CPCV path testing, PBO overfit checks, Deflated Sharpe validation, and at least 30 trading days of forward paper tracking before it can be labeled `LIVE_REVIEW_CANDIDATE`.

### Goals

| ID | Goal |
|---|---|
| G-001 | Define a testable contract for promoting 005930.KS from `PAPER_PASS` to `LIVE_REVIEW_CANDIDATE`. |
| G-002 | Keep the workflow report-only and manual-review-only. |
| G-003 | Require CPCV, PBO, Deflated Sharpe, forward paper trading, model card, and dashboard readiness evidence before promotion. |
| G-004 | Preserve `new_capital_allowed=false`, `broker_order_execution=false`, and `manual_approval_required=true` in all live-review outputs. |
| G-005 | Make failed, missing, stale, or ambiguous evidence block promotion instead of being silently ignored. |

### Non-Goals

| ID | Non-goal |
|---|---|
| NG-001 | Do not execute broker orders. |
| NG-002 | Do not connect to or write to a brokerage account. |
| NG-003 | Do not create automatic trading behavior. |
| NG-004 | Do not approve new live capital. |
| NG-005 | Do not state or imply a guaranteed return. |
| NG-006 | Do not relax thresholds to force promotion. |
| NG-007 | Do not treat `LIVE_REVIEW_CANDIDATE` as a buy, sell, or hold instruction. |

## User Scenarios & Testing

### US-001 - Operator freezes the PAPER_PASS baseline (Priority: P1)

As an operator, I need the current `PAPER_PASS` evidence to be frozen with provenance before any live-review checks run.

Why this priority: all later promotion evidence must be traceable to a specific code and data state.

Independent test: generate baseline evidence under `reports/live_review/005930/` and verify the files include symbol, branch, full SHA, timestamps, and safety flags.

Acceptance scenarios:

1. Given 005930.KS is in `PAPER_PASS`, When the baseline snapshot is generated, Then `paper_pass_snapshot.json` exists and records the current metrics.
2. Given the baseline snapshot is generated, When provenance is checked, Then branch, full commit SHA, and `generated_at_utc` are present.
3. Given baseline generation completes, When the safety flags are inspected, Then `broker_order_execution=false`, `new_capital_allowed=false`, and `manual_approval_required=true` are present.

### US-002 - Reviewer sees CPCV, PBO, and DSR evidence (Priority: P1)

As a reviewer, I need evidence that the model is not passing only because of a single favorable backtest.

Why this priority: live-review promotion depends on robustness across purged paths and overfit controls.

Independent test: run the live-review diagnostic tests and inspect generated CPCV, PBO, and DSR reports.

Acceptance scenarios:

1. Given CPCV diagnostics run, When `cpcv_report_005930.json` is written, Then it includes path count, path pass count, path pass rate, and per-path status.
2. Given PBO diagnostics run, When `pbo_report_005930.json` is written, Then `pbo` is in `[0, 1]` and the report compares it against `0.20`.
3. Given DSR diagnostics run, When `dsr_report_005930.json` is written, Then `deflated_sharpe`, `psr_vs_zero`, and `mc_drawdown_p95` are present.

### US-003 - Operator tracks 30 trading days of forward paper results (Priority: P1)

As an operator, I need forward paper evidence before the candidate can be treated as live-review-ready.

Why this priority: backtest-only evidence is not enough for live-review promotion.

Independent test: validate the forward paper CSV and summary JSON after at least 30 trading rows.

Acceptance scenarios:

1. Given daily forward paper tracking is active, When 30 trading rows exist, Then every required column is present in `paper_trading_log_005930.csv`.
2. Given the forward paper summary is generated, When the summary is inspected, Then it reports days, cumulative alpha, rule violation count, critical missing data count, and drawdown.
3. Given forward paper evidence fails any required threshold, When readiness is classified, Then the status remains `PAPER_PASS` or lower and does not become `LIVE_REVIEW_CANDIDATE`.

### US-004 - Reviewer reads a model card before live review (Priority: P1)

As a human reviewer, I need a model card that explains intended use, validation evidence, risks, and safety boundaries.

Why this priority: a dashboard status alone is not enough for responsible manual review.

Independent test: inspect `reports/model_cards/model_card_005930.md` for required sections and safety statements.

Acceptance scenarios:

1. Given all diagnostic reports exist, When the model card is generated, Then it includes summary, intended use, out-of-scope items, data sources, feature set, validation method, backtest summary, CPCV/PBO/DSR summary, cost stress summary, forward paper summary, risks, governance, and latest readiness status.
2. Given the model card exists, When safety statements are inspected, Then it states that the report is not a buy/sell instruction and does not execute broker orders.
3. Given evidence is missing or stale, When the model card is generated, Then missing evidence is marked explicitly instead of being presented as passed.

### US-005 - Dashboard separates PAPER_PASS from LIVE_REVIEW_CANDIDATE (Priority: P1)

As a dashboard user, I need `PAPER_PASS` and `LIVE_REVIEW_CANDIDATE` to be visibly different states.

Why this priority: mislabeling a review candidate as trade-approved would create operational risk.

Independent test: generate `dashboard_snapshot.v1.json` and verify live-review fields and safety flags.

Acceptance scenarios:

1. Given live-review evidence passes, When the dashboard snapshot is generated, Then `readiness_status=LIVE_REVIEW_CANDIDATE` and `live_review_candidate=true` are present.
2. Given live-review evidence passes, When the dashboard snapshot is generated, Then `new_capital_allowed=false`, `broker_order_execution=false`, and `manual_approval_required=true` remain present.
3. Given any hard block is true, When the dashboard snapshot is generated, Then `live_review_candidate=false` and the status is not promoted.

### Edge Cases

| ID | Edge case | Expected behavior |
|---|---|---|
| EC-001 | CPCV path pass rate is below 60.00%. | Keep status at `PAPER_PASS`; do not promote. |
| EC-002 | PBO is greater than 20.00%. | Keep status at `PAPER_PASS` or lower and record overfit risk. |
| EC-003 | Deflated Sharpe is missing, null, or `<= 0.00`. | Block live-review promotion. |
| EC-004 | Forward paper rows are fewer than 30 trading days. | Block live-review promotion. |
| EC-005 | Forward paper alpha is below 0.00%. | Block live-review promotion. |
| EC-006 | Any rule violation appears in the forward paper log. | Block live-review promotion until reviewed. |
| EC-007 | Required model card is missing. | Block live-review promotion. |
| EC-008 | Dashboard snapshot omits safety flags. | Block promotion and mark dashboard contract invalid. |
| EC-009 | `broker_order_execution=true` appears anywhere in readiness evidence. | Force `HARD_BLOCK`. |
| EC-010 | `new_capital_allowed=true` appears before human approval. | Force `HARD_BLOCK`. |
| EC-011 | Provider audit, point-in-time guard, or OOF-only backtest evidence is missing. | Force `HARD_BLOCK` unless explicitly resolved by an approved clarification. |

## Requirements

### Functional Requirements

| ID | Requirement | Scenario |
|---|---|---|
| FR-001 | The system MUST create a frozen `PAPER_PASS` baseline snapshot for 005930.KS before live-review promotion checks. | US-001 |
| FR-002 | The baseline snapshot MUST include symbol, readiness status, current metrics, safety flags, and generated timestamp. | US-001 |
| FR-003 | The provenance report MUST include branch, full commit SHA, generated timestamp, and evidence paths. | US-001 |
| FR-004 | The live-review gate MUST require `paper_pass=true` before evaluating live-review promotion. | US-002, US-005 |
| FR-005 | The live-review gate MUST require CPCV path pass rate `>= 0.60`. | US-002 |
| FR-006 | The CPCV report MUST include path count, path pass count, path pass rate, path-level metrics, and status. | US-002 |
| FR-007 | CPCV diagnostics MUST use purged splits and MUST detect train/test label overlap. | US-002 |
| FR-008 | The live-review gate MUST require PBO `<= 0.20`. | US-002 |
| FR-009 | The PBO report MUST include `pbo`, threshold, method, symbol, and status. | US-002 |
| FR-010 | The live-review gate MUST require Deflated Sharpe Ratio `> 0.00`. | US-002 |
| FR-011 | The DSR report MUST include `deflated_sharpe`, `psr_vs_zero`, `mc_drawdown_p95`, symbol, and status. | US-002 |
| FR-012 | The live-review gate MUST require at least 30 trading days of forward paper records. | US-003 |
| FR-013 | The forward paper log MUST include date, symbol, signal, raw score, readiness status, close, action, position quantity, equity, benchmark equity, daily alpha, cumulative alpha, rule violation, and optional notes. | US-003 |
| FR-014 | The forward paper summary MUST include trading days, forward alpha, rule violation count, critical missing data count, and forward drawdown. | US-003 |
| FR-015 | The live-review gate MUST require forward paper alpha `>= 0.00%`. | US-003 |
| FR-016 | The live-review gate MUST require `rule_violation_count=0`. | US-003 |
| FR-017 | The live-review gate MUST require a model card at `reports/model_cards/model_card_005930.md`. | US-004 |
| FR-018 | The model card MUST include required safety statements that the report is not a buy/sell instruction and that manual approval is required for any real trade. | US-004 |
| FR-019 | The dashboard readiness contract MUST write a snapshot that can distinguish `PAPER_PASS` from `LIVE_REVIEW_CANDIDATE`. | US-005 |
| FR-020 | The dashboard snapshot MUST preserve `new_capital_allowed=false`, `broker_order_execution=false`, `manual_approval_required=true`, and `screening_output_only=true`. | US-005 |
| FR-021 | Any hard block condition MUST prevent `LIVE_REVIEW_CANDIDATE` and return or record `live_review_candidate=false`. | US-005 |
| FR-022 | Missing, stale, malformed, or contradictory evidence MUST be reported as blocking evidence, not ignored. | US-001, US-002, US-003, US-004, US-005 |
| FR-023 | Final promotion MUST run targeted live-review tests and the full regression suite before status is considered complete. | US-005 |

### Non-Functional Requirements

| ID | Requirement | Measurement |
|---|---|---|
| NFR-001 | Safety: no live-review workflow may emit broker orders or account-writing actions. | Generated outputs and tests confirm `broker_order_execution=false`. |
| NFR-002 | Auditability: every promotion artifact must include enough metadata to trace when and from what code state it was produced. | Evidence files include `generated_at_utc`, branch, commit SHA, symbol, schema version, and evidence paths. |
| NFR-003 | Point-in-time discipline: promotion evidence must not use future data leakage. | CPCV and PIT guard tests pass. |
| NFR-004 | Report-only UX: dashboard and model card language must not present the candidate as trade-approved. | Model card and dashboard checks confirm manual-review-only wording. |
| NFR-005 | Compatibility: existing report-only workflows must continue to run after live-review fields are added. | Full regression suite passes. |
| NFR-006 | Reproducibility: generated readiness evidence must be file-based under `reports/live_review/005930/` and `reports/model_cards/`. | Required evidence paths exist after the run. |
| NFR-007 | Maintainability: readiness status logic should be centralized enough that dashboard, model card, and reports cannot disagree silently. | Tests compare status and safety fields across generated artifacts. |

## Key Entities / Data

| Entity | Meaning | Key fields |
|---|---|---|
| `PaperPassSnapshot` | Frozen baseline for 005930.KS before live-review diagnostics. | `symbol`, `readiness_status`, `metrics`, `generated_at_utc`, safety flags |
| `CpcvReport` | CPCV path distribution report. | `schema_version`, `symbol`, `cv_method`, `path_count`, `path_pass_rate`, `paths`, `status` |
| `PboReport` | Backtest overfit probability report. | `schema_version`, `symbol`, `pbo`, `threshold`, `method`, `status` |
| `DsrReport` | Deflated Sharpe and related risk-adjusted evidence. | `schema_version`, `symbol`, `deflated_sharpe`, `psr_vs_zero`, `mc_drawdown_p95`, `status` |
| `ForwardPaperLog` | Daily forward paper trading evidence. | `date`, `symbol`, `signal`, `equity`, `benchmark_equity`, `daily_alpha_pct`, `cumulative_alpha_pct`, `rule_violation` |
| `ForwardPaperSummary` | Aggregated forward paper result. | `days`, `alpha_pct`, `rule_violation_count`, `critical_data_missing_count`, `max_forward_drawdown_pct`, `status` |
| `ModelCard` | Human-readable review document. | intended use, validation method, evidence summary, risks, governance, latest readiness status |
| `ReadinessSnapshot` | Machine-readable final status. | `readiness_status`, `live_review_candidate`, safety flags, evidence paths |
| `DashboardSnapshot` | Dashboard-facing readiness payload. | `readiness_status`, `live_review_candidate`, `paper_pass`, CPCV/PBO/DSR, forward paper, model card path, safety flags |

## Interfaces & Contracts

### Files

| File contract | Requirement |
|---|---|
| `reports/live_review/005930/paper_pass_snapshot.json` | MUST exist before live-review promotion checks can pass. |
| `reports/live_review/005930/backtest_snapshot.json` | MUST preserve the backtest baseline used by the promotion run. |
| `reports/live_review/005930/cost_stress_snapshot.json` | MUST preserve cost stress evidence used by the promotion run. |
| `reports/live_review/005930/provenance.json` | MUST include branch, full commit SHA, generated timestamp, and evidence paths. |
| `reports/live_review/005930/cpcv_report_005930.json` | MUST report CPCV path distribution and pass/fail status. |
| `reports/live_review/005930/pbo_report_005930.json` | MUST report PBO and threshold status. |
| `reports/live_review/005930/dsr_report_005930.json` | MUST report Deflated Sharpe and supporting risk-adjusted evidence. |
| `reports/live_review/005930/paper_trading_log_005930.csv` | MUST contain at least 30 trading rows before forward evidence can pass. |
| `reports/live_review/005930/forward_paper_summary_005930.json` | MUST summarize forward alpha, rule violations, missing data, and drawdown. |
| `reports/model_cards/model_card_005930.md` | MUST exist before promotion and must include safety statements. |
| `reports/live_review/005930/readiness_snapshot_005930_live_review.json` | MUST record final machine-readable status. |
| `reports/live_review/005930/dashboard_snapshot.v1.json` | MUST expose dashboard readiness fields without enabling trade execution. |

### Commands

| Command | Expected contract |
|---|---|
| `git status` | Used to reveal local changes before freezing provenance. |
| `git rev-parse HEAD` | Used to record full SHA. |
| `git branch --show-current` | Used to record branch. |
| `py -3.12 -m pytest tests\test_cpcv_live_review.py tests\test_pbo.py tests\test_deflated_sharpe_gate.py -q` | Targeted diagnostic tests for CPCV, PBO, and DSR. |
| `py -3.12 -m pytest tests\test_paper_trading_forward.py tests\test_model_card.py tests\test_dashboard_live_review.py -q` | Targeted forward paper, model card, and dashboard tests. |
| `py -3.12 -m pytest -q` | Full regression gate before final promotion. |

## Assumptions & Dependencies

### Assumptions

| ID | Assumption |
|---|---|
| A-001 | The input plan's `PAPER_PASS` metrics are source-plan claims until regenerated in the current implementation. |
| A-002 | 005930.KS is the only ticker in scope for this Spec. |
| A-003 | `LIVE_REVIEW_CANDIDATE` means human review candidate only. It does not mean automatic trading approval. |
| A-004 | All outputs remain file-based under `reports/`. |
| A-005 | The project runtime should use the project `.venv` Python 3.12 path where available, because `docs/AGENTS.md` marks global Python 3.14 as AMBER. |
| A-006 | Existing report-only commands and safety labels remain active. |
| A-007 | CPCV uses the existing `CombinatorialPurgedCV` contract unless explicitly revised. |
| A-008 | The dashboard snapshot contract remains `dashboard_snapshot.v1`. |

### Dependencies

| ID | Dependency | Impact |
|---|---|---|
| D-001 | `src/stock_rtx4060/ml/cv.py` | Provides or hosts the CPCV split behavior. |
| D-002 | `src/stock_rtx4060/backtest/cpcv_diagnostics.py` | Required for CPCV diagnostics output. |
| D-003 | `src/stock_rtx4060/backtest/pbo.py` | Required for PBO output. |
| D-004 | `src/stock_rtx4060/backtest_honesty.py` | Required for DSR gate integration. |
| D-005 | `src/stock_rtx4060/readiness/classifier.py` | Required for final readiness status logic. |
| D-006 | `src/stock_rtx4060/paper_trading.py` | Required for forward paper tracking and summary. |
| D-007 | `src/stock_rtx4060/reports/model_card.py` | Required for model card generation. |
| D-008 | `src/stock_rtx4060/dashboard_bridge.py` | Required for dashboard live-review fields. |
| D-009 | Project `.venv` Python 3.12 | Preferred runtime for tests and validation. |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | Baseline is frozen with provenance. | `paper_pass_snapshot.json` and `provenance.json` exist and include symbol, branch, full SHA, and timestamp. |
| SC-002 | Safety boundary remains intact. | All readiness, dashboard, and model-card artifacts show `new_capital_allowed=false`, `broker_order_execution=false`, and `manual_approval_required=true`. |
| SC-003 | CPCV evidence passes. | `cpcv_report_005930.json` reports `path_count>=10` and `path_pass_rate>=0.60`. |
| SC-004 | CPCV split safety passes. | Tests confirm purged split behavior and no train/test label overlap. |
| SC-005 | PBO evidence passes. | `pbo_report_005930.json` reports `0<=pbo<=0.20`. |
| SC-006 | DSR evidence passes. | `dsr_report_005930.json` reports `deflated_sharpe>0.00`. |
| SC-007 | Forward paper duration passes. | `paper_trading_log_005930.csv` contains at least 30 trading rows. |
| SC-008 | Forward paper result passes. | `forward_paper_summary_005930.json` reports alpha `>=0.00%`, zero rule violations, zero critical missing-data rows, and drawdown within approved limit. |
| SC-009 | Model card is complete. | `model_card_005930.md` exists and contains all required sections and safety statements. |
| SC-010 | Dashboard snapshot is valid. | `dashboard_snapshot.v1.json` distinguishes `PAPER_PASS` from `LIVE_REVIEW_CANDIDATE` and preserves safety flags. |
| SC-011 | Final readiness snapshot is valid. | `readiness_snapshot_005930_live_review.json` reports `readiness_status=LIVE_REVIEW_CANDIDATE` only when every gate passes. |
| SC-012 | Targeted tests pass. | Live-review diagnostic, forward paper, model card, and dashboard tests exit `0`. |
| SC-013 | Full regression passes. | Full project pytest exits `0` using the approved project runtime. |

## Open Questions & Clarifications

### Open Questions

| ID | Question | Impact |
|---|---|---|
| OQ-001 | What exact value should `max_mdd_limit` use for CPCV path pass checks? | Needed to make CPCV path pass deterministic. |
| OQ-002 | What exact value should `min_trades_per_path` use? | Needed to validate CPCV paths consistently. |
| OQ-003 | What exact value should `forward_mdd_limit` use? | Needed to determine forward paper pass/fail. |
| OQ-004 | Should `PAPER_PASS_WITH_SHARPE_AMBER` block promotion or remain a non-blocking warning if DSR passes? | Needed to define final promotion behavior. |
| OQ-005 | The input plan says final regression target is `>= 1345 passed`, while `docs/AGENTS.md` records `1,210 tests, 85.82% coverage` as of 2026-05-10. Which target is current for this phase? | Needed for SC-013 approval. |
| OQ-006 | Which data provider and model kind should the model card treat as authoritative for the 005930.KS candidate? | Needed for model card completeness. |
| OQ-007 | What freshness window makes generated evidence stale? | Needed to prevent old diagnostics from being reused silently. |

### Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-29 | Source plan states current 005930.KS status is `PAPER_PASS`. | `docs/LIVE_REVIEW_CANDIDATE_PLAN_005930_20260529.md` |
| 2026-05-29 | Source plan states live-review is manual review only, not automatic trading. | `docs/LIVE_REVIEW_CANDIDATE_PLAN_005930_20260529.md` |
| 2026-05-29 | Repository docs require report-only behavior and prohibit broker execution, credentials, and destructive account actions. | `docs/AGENTS.md` |
| 2026-05-29 | Project runtime guidance prefers `.venv` Python 3.12 and treats global Python 3.14 as AMBER. | `docs/AGENTS.md` |

## Risks & Mitigations

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| R-001 | Forward paper evidence requires at least 30 trading days. | Promotion cannot be completed immediately from backtest evidence alone. | Keep status at `PAPER_PASS` until required rows exist. |
| R-002 | Dashboard wording may be misunderstood as trade approval. | User may confuse review candidate with buy/sell instruction. | Preserve safety flags and explicit manual-review language in dashboard and model card. |
| R-003 | Missing PIT or provider audit evidence could hide leakage. | Promotion would overstate evidence quality. | Treat missing PIT/provider audit as hard block. |
| R-004 | Regression test target is inconsistent across docs. | Approval criteria may be unclear. | Resolve OQ-005 before approval. |
| R-005 | Stale generated reports could be reused after code or data changes. | Readiness status may reflect old evidence. | Require provenance and evidence freshness policy. |
| R-006 | Thresholds not fully specified in the source plan can create inconsistent pass/fail decisions. | Different runs may classify the same evidence differently. | Resolve OQ-001, OQ-002, and OQ-003 before approval. |

## Traceability

| Item | Links to |
|---|---|
| US-001 | FR-001, FR-002, FR-003, SC-001 |
| US-002 | FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, SC-003, SC-004, SC-005, SC-006 |
| US-003 | FR-012, FR-013, FR-014, FR-015, FR-016, SC-007, SC-008 |
| US-004 | FR-017, FR-018, SC-009 |
| US-005 | FR-019, FR-020, FR-021, FR-022, FR-023, SC-002, SC-010, SC-011, SC-012, SC-013 |
| Safety boundary | NG-001, NG-002, NG-003, NG-004, NG-005, NG-007, NFR-001, NFR-004 |
| Approval blockers | OQ-001, OQ-002, OQ-003, OQ-004, OQ-005, OQ-006, OQ-007 |

## Approval Readiness

This Spec is not approval-ready yet.

Blocking reasons:

- `[NEEDS CLARIFICATION: max_mdd_limit for CPCV path pass is not specified.]`
- `[NEEDS CLARIFICATION: min_trades_per_path is not specified.]`
- `[NEEDS CLARIFICATION: forward_mdd_limit is not specified.]`
- `[NEEDS CLARIFICATION: final regression target conflicts with current docs.]`
- `[NEEDS CLARIFICATION: evidence freshness policy is not specified.]`

Approval-ready means all open questions above are resolved, targeted tests pass, full regression passes, and generated evidence proves every success criterion.

## Changelog

| Version | Date | Change |
|---|---|---|
| v0.1.0 | 2026-05-29 | Initial Spec draft derived from `LIVE_REVIEW_CANDIDATE_PLAN_005930_20260529.md`. |
