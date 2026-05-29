# Feature Specification: investment_readiness_benchmark.py

Feature ID/Branch: investment-readiness-benchmark
Created: 2026-05-29
Status: Draft
Owner: stock_1901 local workflow
Input: `20260529_plan-investment-readiness-benchmark.md`
Last Updated: 2026-05-29
Version: v0.1.0

## Summary

### Problem

Current recommendation reports can produce high-scoring candidates while still carrying `backtest_honesty=AMBER`, weak transaction-cost evidence, or advisor audit ambiguity. The project needs a separate benchmark that blocks those candidates from being treated as investment-ready.

### Goals

- G1: Read an existing `recommendations_algo_v2_*.json` file and produce a benchmark result.
- G2: Require `backtest_honesty.status == "PASS"` before a candidate can be marked investment-review-ready.
- G3: Check 1x, 2x, and 3x cost survival without changing the original recommendation ranking.
- G4: Check embargo stress using existing `cv_gap` and horizon metadata.
- G5: Check advisor audit consistency when `advisor_score` is present.
- G6: Preserve raw model scores while blocking live-capital readiness when model quality gates fail.

### Non-Goals

- NG1: Do not place broker orders.
- NG2: Do not log in to broker or account systems.
- NG3: Do not read or write secrets.
- NG4: Do not change recommendation model training.
- NG5: Do not change dashboard UI.
- NG6: Do not create financial advice wording.

## User Scenarios & Testing

### User Story 1 - Benchmark Existing Recommendation JSON (Priority: P1)

A local operator wants to run a stricter readiness benchmark on an existing recommendation JSON before considering any candidate manually.

Why this priority: This is the core workflow and does not require broker access or new model training.

Independent Test: Create a minimal recommendation JSON fixture with one `PASS` candidate and run the benchmark function or CLI against it.

Acceptance Scenarios:

1. Given a valid recommendation JSON with `backtest_honesty.status == "PASS"`, When the benchmark runs, Then the candidate receives a benchmark record.
2. Given a valid recommendation JSON with `backtest_honesty.status == "AMBER"`, When the benchmark runs, Then the candidate is not marked investment-review-ready.
3. Given a valid recommendation JSON with `screening_output_only=true`, When the benchmark writes output, Then the output preserves manual-review and no-broker-execution language.

### User Story 2 - Reject Weak Backtest Honesty (Priority: P1)

A local operator wants candidates with AMBER or FAIL backtest honesty evidence to be separated from candidates eligible for manual review.

Why this priority: Current reports can show high recommendation scores even when backtest honesty is AMBER.

Independent Test: Use a fixture with `backtest_honesty.status` values `PASS`, `AMBER`, and `FAIL`.

Acceptance Scenarios:

1. Given a candidate with `backtest_honesty.status == "PASS"`, When the benchmark evaluates honesty, Then `BACKTEST_HONESTY` is `PASS`.
2. Given a candidate with `backtest_honesty.status == "AMBER"`, When the benchmark evaluates honesty, Then `BACKTEST_HONESTY` is `FAIL` or candidate readiness is false.
3. Given a candidate with missing `backtest_honesty`, When the benchmark evaluates honesty, Then the candidate is marked `INVALID_INPUT` or not ready.

### User Story 3 - Apply 3x Cost Survival (Priority: P1)

A local operator wants candidates to survive conservative transaction-cost and slippage stress before manual review.

Why this priority: The prior readiness report showed weak transaction-cost buffer evidence.

Independent Test: Use candidate fixtures with `backtest_return_pct` and `backtest_honesty` cost-buffer checks.

Acceptance Scenarios:

1. Given a candidate whose return exceeds the 3x cost threshold, When cost stress runs, Then `COST_STRESS_3X` is `PASS`.
2. Given a candidate whose return does not exceed the 3x cost threshold, When cost stress runs, Then `COST_STRESS_3X` is `FAIL`.
3. Given missing return or cost-buffer metadata, When cost stress runs, Then the result is `AMBER` or `INVALID_INPUT` with an explanation.

### User Story 4 - Apply Embargo Stress (Priority: P2)

A local operator wants weak purged walk-forward gap settings to be visible before manual review.

Why this priority: `cv_gap` and horizon evidence are central to leakage control.

Independent Test: Use fixtures with `cv_gap` equal to horizon, below horizon, and above stress thresholds.

Acceptance Scenarios:

1. Given `cv_gap >= horizon`, When embargo stress runs, Then base embargo evidence is not `FAIL`.
2. Given `cv_gap < horizon`, When embargo stress runs, Then embargo stress is `FAIL`.
3. Given no reliable `cv_gap` or horizon metadata, When embargo stress runs, Then the result is `AMBER` and notes metadata-only limitation.

### User Story 5 - Check Advisor Audit Consistency (Priority: P2)

A local operator wants advisor-influenced recommendations to have visible audit evidence.

Why this priority: MiniMax advisor JSON parsing is now usable, but advisor scores still need audit traceability.

Independent Test: Use one fixture with `advisor_score` and audit evidence, and one fixture with `advisor_score` but no audit evidence.

Acceptance Scenarios:

1. Given `advisor_score` is present and audit evidence exists, When advisor consistency runs, Then `ADVISOR_AUDIT` is `PASS`.
2. Given `advisor_score` is present and audit evidence is missing, When advisor consistency runs, Then `ADVISOR_AUDIT_FAIL` is reported.
3. Given `advisor_score` is null, When advisor consistency runs, Then advisor audit status is `NOT_APPLICABLE`.

### User Story 6 - Separate Raw Score From Investment Score (Priority: P1)

A local operator wants high raw model scores to remain visible while preventing weak model-quality candidates from being treated as investable.

Why this priority: Uploaded evidence showed `BUY / 88.81` while `Accuracy=43.30%`, `AUC=48.14%`, `Alpha=-44.62%p`, and `Completed Trades=4`.

Independent Test: Use a fixture with a high raw score and failing model quality metrics.

Acceptance Scenarios:

1. Given a candidate with `accuracy < 0.50`, When model quality gate runs, Then `new_capital_allowed=false`.
2. Given a candidate with `auc < 0.50`, When model quality gate runs, Then the candidate status is `AMBER_WATCHLIST`.
3. Given a candidate with `alpha < 0`, When model quality gate runs, Then `investment_score` is capped at 44 or below.
4. Given a candidate with `completed_trades < 50`, When model quality gate runs, Then `paper_trading_only=true`.
5. Given a candidate with all model quality metrics passing, When model quality gate runs, Then the raw score is not capped by this gate.

### Edge Cases

- EC1: Input path does not exist -> return non-zero CLI exit and no misleading PASS.
- EC2: Input JSON is malformed -> return `INVALID_INPUT`.
- EC3: `results` is empty -> output run verdict `NO_CANDIDATES`.
- EC4: Candidate lacks `ticker` -> mark that candidate `INVALID_INPUT`.
- EC5: Candidate has `screening_output_only` false -> mark run `FAIL`.
- EC6: Advisor audit path exists but has no matching ticker -> mark `ADVISOR_AUDIT_FAIL`.
- EC7: Existing recommendation JSON has AMBER candidates only -> output should be valid but final readiness should be false.
- EC8: Raw score is high but model quality metrics fail -> preserve raw score and cap investment score.
- EC9: Model quality metrics are missing -> mark model quality `AMBER` and block new capital until verified.

## Requirements

### Functional Requirements

- FR-001: The system MUST provide `tools/investment_readiness_benchmark.py`.
- FR-002: The tool MUST accept an input path for `recommendations_algo_v2_*.json`.
- FR-003: The tool MUST parse `results`, `config`, `backtest_honesty_summary`, `audit_log_path`, and `disclaimer` when present.
- FR-004: The tool MUST reject or mark invalid malformed JSON input.
- FR-005: The tool MUST mark candidates with `backtest_honesty.status != "PASS"` as not investment-review-ready.
- FR-006: The tool MUST evaluate cost survival at 1x, 2x, and 3x levels.
- FR-007: The tool MUST mark 3x cost stress failure as `COST_STRESS_FAIL`.
- FR-008: The tool MUST evaluate embargo stress from `cv_gap` and horizon metadata when available.
- FR-009: The tool MUST mark weak embargo evidence as `EMBARGO_STRESS_AMBER` or `EMBARGO_STRESS_FAIL`.
- FR-010: The tool MUST check advisor audit consistency when `advisor_score` is not null.
- FR-011: The tool MUST mark missing advisor audit evidence as `ADVISOR_AUDIT_FAIL`.
- FR-012: The tool MUST preserve report-only language: `manual approval required` and `no broker order execution`.
- FR-013: The tool MUST produce a machine-readable JSON output or a Markdown output.
- FR-014: The tool MUST include an overall run verdict.
- FR-015: The tool MUST NOT modify the original recommendation JSON.
- FR-016: The tool MUST preserve original recommendation score as `raw_score` or equivalent output.
- FR-017: The tool MUST compute an investment-readiness score separately from raw model or ensemble score.
- FR-018: The tool MUST set `status="AMBER_WATCHLIST"` when any model quality gate fails.
- FR-019: The tool MUST set `new_capital_allowed=false` when `accuracy < 0.50`.
- FR-020: The tool MUST set `new_capital_allowed=false` when `auc < 0.50`.
- FR-021: The tool MUST set `new_capital_allowed=false` when `alpha < 0`.
- FR-022: The tool MUST set `new_capital_allowed=false` when `completed_trades < 50`.
- FR-023: The tool MUST set `paper_trading_only=true` when any model quality gate fails.
- FR-024: The tool MUST cap `investment_score` at `44` or lower when any model quality gate fails.
- FR-025: The tool MUST NOT use a capped investment score to hide the original raw score.

### Non-Functional Requirements

- NFR-001 (Safety): The tool MUST NOT perform broker login, account lookup, or order execution.
- NFR-002 (Scope): The tool MUST only operate inside the stock project folder when run in this workflow.
- NFR-003 (Traceability): Each failed benchmark check MUST include an evidence string.
- NFR-004 (Determinism): The same input JSON MUST produce the same benchmark classifications, except for generated timestamps.
- NFR-005 (Testability): Core benchmark logic MUST be callable from tests without shelling out to the CLI.
- NFR-006 (Compatibility): The tool SHOULD work with existing recommendation JSON files already generated by the project.
- NFR-007 (Explainability): When raw score and investment score differ, output MUST include the gate reason.

## Key Entities / Data

- RecommendationRunInput: Parsed recommendation JSON file.
- CandidateInput: One item from `results`.
- BenchmarkCheck: A named check with `status`, `evidence`, and optional `threshold`.
- CandidateBenchmark: Candidate-level benchmark output.
- RunBenchmark: Overall benchmark output with run verdict and candidate records.
- ModelQualityGate: Accuracy, AUC, alpha, and completed-trades evidence used to block live-capital readiness.

## Interfaces & Contracts

### CLI

```text
py -3.12 tools/investment_readiness_benchmark.py --input <recommendations_algo_v2_*.json> --output <path> --format json|md
```

### Input Contract

- Required:
  - `results`
- Candidate fields used when present:
  - `ticker`
  - `track`
  - `verdict`
  - `screening_output_only`
  - `recommendation_rank_score`
  - `backtest_return_pct`
  - `backtest_honesty`
  - `validations`
  - `reasons`
  - `advisor_score`
  - `advisor_rationale`
  - `model_accuracy`
  - `model_auc`
  - `alpha_pct` or benchmark-relative alpha field when present
  - `completed_trades` or trade-count field when present
- Run fields used when present:
  - `config`
  - `audit_log_path`
  - `disclaimer`
  - `backtest_honesty_summary`

### Output Contract

- JSON output MUST include:
  - `schema_version`
  - `generated_at_utc`
  - `input_path`
  - `run_verdict`
  - `candidate_count`
  - `ready_count`
  - `candidates`
- Candidate output MUST include:
  - `ticker`
  - `track`
  - `ready_for_manual_review`
  - `new_capital_allowed`
  - `paper_trading_only`
  - `raw_score`
  - `investment_score`
  - `blocking_reasons`
  - `checks`

## Assumptions & Dependencies

### Assumptions

- A1: The benchmark uses existing recommendation JSON as the primary input.
- A2: Cost stress can initially be metadata-based if full backtest rerun data is unavailable.
- A3: `transaction_cost_buffer_pct` from existing honesty checks can act as the base cost buffer when explicit cost metadata is missing.
- A4: Embargo stress can initially use `cv_gap` evidence from result reasons or model metadata.
- A5: Advisor audit evidence can be checked by matching ticker and date in the advisor audit file when available.
- A6: If existing recommendation JSON lacks explicit alpha or completed-trades fields, the benchmark records those checks as missing evidence and blocks new capital.
- A7: `AMBER_WATCHLIST` means not investable for live capital, retained for monitoring and paper trading only.

### Dependencies

- D1: Existing recommendation JSON schema from `src/stock_rtx4060/recommendation_engine.py`.
- D2: Existing honesty evidence from `src/stock_rtx4060/backtest_honesty.py`.
- D3: Existing advisor audit behavior from `src/stock_rtx4060/advisors/audit.py`.
- D4: Existing tests and fixtures under `tests/`.

## Success Criteria

### Measurable Outcomes

- SC-001: A fixture with `backtest_honesty.status == "AMBER"` produces `ready_for_manual_review=false`.
- SC-002: A fixture with `backtest_honesty.status == "PASS"` and all other checks passing produces `ready_for_manual_review=true`.
- SC-003: A fixture failing 3x cost survival includes `COST_STRESS_FAIL`.
- SC-004: A fixture with `cv_gap < horizon` includes `EMBARGO_STRESS_FAIL`.
- SC-005: A fixture with advisor score but missing audit evidence includes `ADVISOR_AUDIT_FAIL`.
- SC-006: The CLI returns non-zero for malformed JSON.
- SC-007: `py -3.12 -m pytest tests/test_investment_readiness_benchmark.py -q` passes.
- SC-008: `py -3.12 -m ruff check tools/investment_readiness_benchmark.py tests/test_investment_readiness_benchmark.py` passes.
- SC-009: A fixture with raw score `88.81`, accuracy `0.433`, AUC `0.4814`, alpha `-44.62`, and completed trades `4` produces `status="AMBER_WATCHLIST"`.
- SC-010: The same fixture produces `new_capital_allowed=false`, `paper_trading_only=true`, and `investment_score <= 44`.
- SC-011: The same fixture preserves the original raw score separately from the capped investment score.

## Open Questions & Clarifications

### Open Questions

- Q1: Should 3x cost survival be calculated only from metadata in v1, or should it rerun `Backtester` when OHLCV source data is available?
- Q2: What exact minimum threshold should define 3x cost survival when explicit fee and slippage metadata is absent?
- Q3: Where should final benchmark reports be written by default: `reports/investment_readiness_benchmark/` or caller-provided output only?
- Q4: Should `backtest_honesty=AMBER` always block readiness, or should there be a separate `manual_watchlist` tier?

### Clarifications Log

- 2026-05-29: User requested `backtest_honesty=PASS`, `3x cost survival`, `embargo stress`, and `advisor audit consistency` as the bundled benchmark.
- 2026-05-29: User selected `AMBER_WATCHLIST` for weak model quality gates. Live capital must be blocked with `new_capital_allowed=false`, while raw score remains available for monitoring and paper trading.

## Risks & Mitigations

- R1: Existing JSON may not include enough data for true rerun-based cost stress -> Mitigation: clearly label metadata-only checks.
- R2: Strict PASS-only honesty gate may remove most current candidates -> Mitigation: separate blocked candidates with reasons instead of hiding them.
- R3: Advisor audit paths may differ by output directory -> Mitigation: allow explicit audit path override in CLI.
- R4: Users may interpret output as financial advice -> Mitigation: preserve no-advice and no-order-execution wording in every report.

## Traceability

| Item | Links to |
|---|---|
| User Story 1 | FR-001, FR-002, FR-013, FR-014, SC-007 |
| User Story 2 | FR-005, SC-001, SC-002 |
| User Story 3 | FR-006, FR-007, SC-003 |
| User Story 4 | FR-008, FR-009, SC-004 |
| User Story 5 | FR-010, FR-011, SC-005 |
| User Story 6 | FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-024, FR-025, SC-009, SC-010, SC-011 |
| Safety boundary | NFR-001, FR-012, FR-019, FR-020, FR-021, FR-022, R4 |

## Reviewer Checklist

- [ ] Required sections are present.
- [ ] In-scope and out-of-scope items match the Plan.
- [ ] Functional requirements use stable IDs.
- [ ] Success criteria are measurable.
- [ ] No broker/account/order/secret behavior is included.
- [ ] Raw score and investment score are separated.
- [ ] Model quality gate failure blocks new capital.
- [ ] Open questions are non-critical for metadata-only v1 implementation or must be resolved before coding.

## Changelog

- v0.1.0 (2026-05-29): Initial contract draft from `20260529_plan-investment-readiness-benchmark.md`.
- v0.2.0 (2026-05-29): Added model quality gate and `AMBER_WATCHLIST` live-capital lock contract.
