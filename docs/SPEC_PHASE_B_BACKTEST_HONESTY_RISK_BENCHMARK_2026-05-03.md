# SPEC - Phase B Backtest Honesty Suite + Risk-adjusted Model Benchmark

Feature ID: `phase-b-backtest-honesty-risk-benchmark`

Created: 2026-05-03

Status: Approved and implemented for Phase B Option B.

Input plan: `docs/plan_phase_b_backtest_honesty_risk_benchmark_2026-05-03.md`

Owner: Codex Spec draft using `spec-studio`.

## Summary

### Problem

The current system already produces report-only recommendation and backtest evidence. Phase A also added point-in-time provider validation and Provider v2 dashboard evidence.

The remaining risk is false confidence from model metrics and backtest results. A high return, Sharpe ratio, model accuracy, or direction probability can still be misleading when leakage, overfit risk, transaction costs, weak OOF coverage, or unstable walk-forward evidence are not made explicit.

### Goals

| ID | Goal |
|---|---|
| G-001 | Add a Backtest Honesty Suite that records evidence about leakage, overfit risk, transaction-cost buffer, drawdown risk, Sharpe floor, OOF coverage, and walk-forward gap. |
| G-002 | Add risk-adjusted benchmark evidence without changing broker, account, or order behavior. |
| G-003 | Preserve existing CLI commands and report-only output. |
| G-004 | Add dashboard evidence only as additive `dashboard_snapshot.v1` fields. |

### Non-Goals

| ID | Non-goal |
|---|---|
| NG-001 | Do not implement broker execution, auto-buy, auto-sell, margin, options, short selling, or account-affecting actions. |
| NG-002 | Do not claim that a backtest honesty PASS means a ticker is safe to buy. |
| NG-003 | Do not add TimesFM, Qlib, RD-Agent, TensorFlow/LSTM, or other research sandbox models in Phase B Option B. |
| NG-004 | Do not rename or break `dashboard_snapshot.v1`. |
| NG-005 | Do not require OpenBB, paid provider credentials, or private URLs for offline validation. |

## User Scenarios & Testing

### US-001 - Operator sees honesty status in recommendation output (Priority: P1)

As an operator, I need the recommendation report to show whether the backtest evidence is strong, weak, or cautionary before I manually review a ticker.

Why this priority: the system is used for stock-candidate screening, and weak backtest evidence can create false confidence.

Independent test: run synthetic `recommend` smoke and inspect the generated JSON or Markdown for the honesty summary.

Acceptance scenarios:

1. Given a synthetic recommendation run completes, When the report JSON is written, Then the JSON includes additive backtest honesty evidence.
2. Given a candidate has weak OOF coverage or weak backtest metrics, When honesty checks run, Then the candidate or top-level summary records `AMBER` or `FAIL` evidence rather than silently treating the result as strong.
3. Given the recommendation output includes honesty evidence, When the Markdown report is generated, Then the evidence is visible to the operator without implying broker approval.

### US-002 - Dashboard keeps existing snapshot compatibility (Priority: P1)

As a dashboard user, I need the REC dashboard to continue loading existing snapshots while optionally showing Phase B honesty evidence.

Why this priority: the dashboard already consumes `dashboard_snapshot.v1`; breaking the schema would disrupt current report viewing.

Independent test: run `dashboard-export` with both older payloads and Phase B payloads.

Acceptance scenarios:

1. Given a recommendation JSON contains Phase B honesty evidence, When `dashboard-export` runs, Then `dashboard_snapshot.v1` includes additive honesty fields.
2. Given a recommendation JSON does not contain Phase B honesty evidence, When `dashboard-export` runs, Then the export still succeeds and existing dashboard fields remain present.
3. Given a dashboard snapshot contains honesty evidence, When the REC dashboard reads it, Then report-only fields such as `screening_output_only` remain preserved.

### US-003 - Developer can test honesty checks without internet (Priority: P1)

As a developer, I need deterministic unit tests for honesty checks so Phase B can be verified without external market data.

Why this priority: provider availability and internet access should not block core honesty validation.

Independent test: run unit tests against synthetic metric inputs.

Acceptance scenarios:

1. Given metric inputs meet Phase B thresholds, When the honesty checker runs, Then the result is `PASS`.
2. Given metric inputs violate critical thresholds, When the honesty checker runs, Then the result is `FAIL` or `AMBER` with reasons.
3. Given optional metric fields are missing, When the honesty checker runs, Then missing evidence is reported explicitly instead of crashing.

### US-004 - Existing CLI remains stable (Priority: P1)

As an operator, I need existing commands to keep working after Phase B.

Why this priority: Phase B is a safety evidence upgrade, not a CLI migration.

Independent test: run compile, CLI help, full pytest, synthetic recommendation smoke, and dashboard export smoke.

Acceptance scenarios:

1. Given Phase B changes are applied, When `python main.py --help` runs, Then existing commands remain visible.
2. Given Phase B changes are applied, When `pytest -q` runs in the project `.venv`, Then existing and new tests pass.
3. Given Phase B changes are applied, When synthetic recommendation smoke runs, Then Markdown, JSON, audit JSONL, and honesty evidence are generated.

### Edge Cases

| ID | Edge case | Expected behavior |
|---|---|---|
| EC-001 | OOF coverage missing or below threshold | Return explicit caution evidence, not PASS. |
| EC-002 | Sharpe missing, NaN, or below floor | Return explicit caution evidence. |
| EC-003 | MDD exceeds threshold | Return `AMBER` or `FAIL` depending on approved threshold. |
| EC-004 | Transaction-cost buffer is not computable | Mark buffer evidence missing; do not claim cost-adjusted robustness. |
| EC-005 | Older recommendation JSON lacks honesty fields | `dashboard-export` remains backward-compatible. |
| EC-006 | Honesty status is PASS but risk plan fails | Risk plan failure still blocks the candidate; honesty PASS must not override risk gates. |

## Requirements

### Functional Requirements

| ID | Requirement | Scenario |
|---|---|---|
| FR-001 | The system MUST add deterministic backtest honesty checks for Phase B Option B. | US-001, US-003 |
| FR-002 | The honesty checks MUST support PASS, AMBER, and FAIL style outcomes. | US-001, US-003 |
| FR-003 | The honesty checks MUST evaluate OOF coverage evidence. | US-001, US-003 |
| FR-004 | The honesty checks MUST evaluate drawdown evidence. | US-001, US-003 |
| FR-005 | The honesty checks MUST evaluate Sharpe or equivalent risk-adjusted return evidence. | US-001, US-003 |
| FR-006 | The honesty checks MUST evaluate transaction-cost buffer evidence when the needed inputs are available. | US-001, US-003 |
| FR-007 | The honesty checks MUST expose human-readable reasons for AMBER and FAIL outcomes. | US-001 |
| FR-008 | Recommendation JSON MUST carry honesty evidence as additive metadata. | US-001, US-002 |
| FR-009 | Markdown recommendation reports SHOULD expose honesty evidence in a human-readable section or row field. | US-001 |
| FR-010 | `dashboard-export` MUST preserve additive honesty evidence in `dashboard_snapshot.v1` when present. | US-002 |
| FR-011 | `dashboard-export` MUST remain compatible with recommendation JSON that lacks honesty evidence. | US-002 |
| FR-012 | Existing commands MUST remain available after Phase B changes. | US-004 |
| FR-013 | Phase B MUST NOT introduce broker, account, order, margin, options, or destructive filesystem operations. | US-004 |
| FR-014 | Phase B MUST NOT change recommendation ranking rules until separately approved. | US-001 |
| FR-015 | Phase B MUST keep `screening_output_only` visible in recommendation and dashboard outputs. | US-002, US-004 |

### Non-Functional Requirements

| ID | Requirement | Measurement |
|---|---|---|
| NFR-001 | Testability: honesty logic MUST be unit-testable without internet. | `pytest tests/test_backtest_honesty.py -q` passes. |
| NFR-002 | Compatibility: dashboard snapshot schema MUST remain `dashboard_snapshot.v1`. | Dashboard bridge tests pass. |
| NFR-003 | Safety: the feature MUST preserve report-only language. | Tests or smoke output confirm `screening_output_only`. |
| NFR-004 | Maintainability: new checks SHOULD be isolated from provider loading. | New module or clearly scoped functions are used. |
| NFR-005 | Observability: AMBER/FAIL outcomes MUST include reasons. | Unit tests assert reason text is non-empty. |
| NFR-006 | Performance: Phase B Option B SHOULD stay lightweight enough for synthetic smoke runs. | Synthetic smoke completes without requiring new heavy model dependencies. |

## Key Entities / Data

| Entity | Meaning | Key fields |
|---|---|---|
| HonestyCheck | One deterministic validation result for a backtest or model evidence field. | `name`, `status`, `value`, `threshold`, `reason` |
| HonestySummary | Aggregated Phase B evidence for a recommendation run or candidate. | `status`, `checks`, `passed`, `amber`, `failed`, `generated_at_utc` |
| Dashboard Snapshot | File-based dashboard payload. | Existing `dashboard_snapshot.v1` plus optional additive honesty summary |

## Interfaces & Contracts

### Files

| File contract | Requirement |
|---|---|
| Recommendation JSON | MUST remain valid JSON and include optional honesty evidence after implementation. |
| Recommendation Markdown | SHOULD include honesty evidence without removing existing sections. |
| `dashboard_snapshot.v1` | MUST keep existing keys and add optional honesty evidence only. |
| Audit JSONL | MAY remain unchanged unless Phase B explicitly adds honesty audit events after approval. |

### CLI

| Command | Expected Phase B behavior |
|---|---|
| `python main.py --help` | Existing command list remains available. |
| `.\run.ps1 recommend --synthetic ...` | Generates existing report files plus Phase B honesty evidence after implementation. |
| `.\run.ps1 dashboard-export ...` | Exports snapshot with optional honesty evidence. |

## Assumptions & Dependencies

### Assumptions

| ID | Assumption |
|---|---|
| A-001 | Phase B Option B is approved and implemented. |
| A-002 | Existing backtest and recommendation output fields provide enough baseline metrics for minimal honesty checks. |
| A-003 | Honesty evidence is additive and does not change ranking in Phase B. |
| A-004 | Synthetic data is sufficient for offline smoke validation, but not proof of real-market performance. |

### Dependencies

| ID | Dependency | Impact |
|---|---|---|
| DEP-001 | `src/stock_rtx4060/backtester.py` | Existing backtest metrics feed honesty checks. |
| DEP-002 | `src/stock_rtx4060/recommendation_engine.py` | Recommendation JSON and Markdown must carry new evidence. |
| DEP-003 | `src/stock_rtx4060/dashboard_bridge.py` | Snapshot must preserve additive honesty evidence. |
| DEP-004 | `tests/` | Regression tests must cover compatibility. |
| DEP-005 | `stock-pred-v5` | UI display can be verified after backend export, but Phase B must not require a schema-breaking frontend rewrite. |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | Package compiles. | `python -m compileall main.py src tests` exits 0. |
| SC-002 | CLI help remains available. | `python main.py --help` exits 0. |
| SC-003 | Full regression tests pass. | `pytest -q` passes in project `.venv`. |
| SC-004 | Honesty unit tests pass. | `pytest tests/test_backtest_honesty.py -q` passes after implementation. |
| SC-005 | Synthetic recommendation smoke includes honesty evidence. | `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/phase_b_backtest_honesty_smoke` creates Markdown, JSON, audit JSONL, and honesty evidence. |
| SC-006 | Dashboard export remains compatible. | `dashboard-export` succeeds for payloads with and without honesty evidence. |
| SC-007 | Report-only boundary remains intact. | Recommendation JSON and dashboard snapshot preserve `screening_output_only`. |
| SC-008 | No new heavy optional model dependency is required for Option B. | Fresh synthetic tests pass without TimesFM, Qlib, RD-Agent, TensorFlow, or OpenBB. |

## Open Questions

| ID | Question | Impact |
|---|---|---|
| OQ-001 | RESOLVED: Use existing `RecommendationConfig` thresholds where available and add lightweight configurable defaults for Phase B. | Approved by operator. |
| OQ-002 | RESOLVED: Store both candidate-level `backtest_honesty` and top-level `backtest_honesty_summary`. | Approved by operator. |
| OQ-003 | RESOLVED: Use fixed configurable default `transaction_cost_buffer_pct=0.50` for Phase B. | Approved by operator. |
| OQ-004 | RESOLVED: Add `backtest_honesty_summary` event to audit JSONL after report writing. | Approved by operator. |

## Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-03 | Phase A Point-in-time Provider Validation + Provider v2 Dashboard is already implemented, committed, and uploaded to `origin/main`. | Current repository docs |
| 2026-05-03 | Phase B should follow Phase A and should not duplicate Phase A scope. | Current planning pass |
| 2026-05-03 | Phase B Option B is recommended and approved. | User approval |
| 2026-05-03 | Phase B open questions were approved. | User approval |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Threshold ambiguity | Implementation may encode arbitrary PASS/AMBER/FAIL values. | Require approval for thresholds before coding or mark defaults as configurable. |
| False confidence | Users may treat honesty PASS as buy approval. | Preserve `screening_output_only` and manual review wording. |
| Runtime overhead | Additional checks could slow recommendations. | Keep Option B deterministic and avoid heavy new dependencies. |
| Schema drift | Dashboard or old reports could break. | Add fields only and test old payload compatibility. |
| Scope creep | TimesFM/Qlib/RD-Agent could enter core recommendation path too early. | Keep research models as explicit non-goals for Phase B Option B. |

## Traceability

| Scenario | Requirements | Success criteria |
|---|---|---|
| US-001 | FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-014, FR-015 | SC-004, SC-005, SC-007 |
| US-002 | FR-010, FR-011, FR-015, NFR-002, NFR-003 | SC-006, SC-007 |
| US-003 | FR-001, FR-002, FR-007, NFR-001, NFR-005 | SC-004 |
| US-004 | FR-012, FR-013, FR-015, NFR-006 | SC-001, SC-002, SC-003, SC-008 |

## Reviewer Checklist

| Check | Status |
|---|---|
| Mandatory sections present | PASS |
| User scenarios use Given/When/Then | PASS |
| Functional requirement IDs present | PASS |
| Non-functional requirement IDs present | PASS |
| Success criteria are measurable | PASS |
| Critical ambiguity visible | PASS, four open questions resolved |
| Approval-ready for implementation | PASS, implemented for Option B |

## Approval Readiness

Status: approved and implemented.

Implemented decisions:

1. Phase B Option B is approved.
2. Thresholds use existing `RecommendationConfig` values where available plus lightweight configurable Phase B defaults.
3. Honesty evidence is stored in both candidate-level `backtest_honesty` and top-level `backtest_honesty_summary`.
4. Phase B writes audit JSONL event type `backtest_honesty_summary`.

Implementation evidence:

| Check | Result |
|---|---|
| RED test | `tests/test_backtest_honesty.py` first failed with missing `stock_rtx4060.backtest_honesty`. |
| Targeted tests | PASS, 7 tests passed. |
| Compile | PASS, `python -m compileall main.py src tests`. |
| CLI help | PASS, `python main.py --help`. |
| Full pytest | PASS, 30 tests passed. |
| Phase B smoke | PASS, `reports/phase_b_backtest_honesty_smoke/dashboard_snapshot.json` contains additive honesty evidence and keeps `screening_output_only=True`. |
