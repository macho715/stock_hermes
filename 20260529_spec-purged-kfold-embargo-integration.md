# Feature Specification: PurgedKFold Embargo Integration

Feature ID/Branch: purged-kfold-embargo-integration
Created: 2026-05-29
Status: Draft
Owner: stock_1901 local workflow
Input: `20260529_plan-purged-kfold-embargo-integration.md`
Last Updated: 2026-05-29
Version: v0.1.0

## Summary

### Problem

The project has a validated reference implementation for leakage-free time-series CV in `docs/purged_kfold_embargo.py`, but the operating code already exposes a different API through `PurgedKFold(...).split(X, groups=...)`. The integration must harden leakage controls without breaking existing recommendation, HPO, dashboard, and readiness contracts.

### Goals

- G1: Preserve the existing operating API `PurgedKFold(n_splits, embargo_pct).split(X, y=None, groups=...)`.
- G2: Enforce label-window overlap purge and post-test embargo behavior in the operating splitter.
- G3: Ensure backtest performance uses OOF probability only.
- G4: Keep live-capital readiness blocked unless existing readiness and backtest honesty gates pass.
- G5: Align CLI and documentation language with the actual CV method.

### Non-Goals

- NG1: Do not add broker order execution.
- NG2: Do not add account access or secret handling.
- NG3: Do not enable automated trading.
- NG4: Do not replace the model architecture.
- NG5: Do not replace PurgedKFold with Combinatorial Purged CV.
- NG6: Do not relax investment readiness gates.

## User Scenarios & Testing

### User Story 1 - Use Existing PurgedKFold API (Priority: P1)

A developer wants to harden the splitter while keeping current recommendation and HPO call sites working.

Why this priority: The repository rule requires financial CV calls to provide `groups`; breaking the public API would make integration unsafe.

Independent Test: Instantiate `PurgedKFold(n_splits=..., embargo_pct=...)` and call `split(X, groups=groups)` from a unit test.

Acceptance Scenarios:

1. Given valid `X` and valid `groups`, When `split(X, groups=groups)` runs, Then it yields train/test index pairs without changing the call signature.
2. Given a call site that passes `groups`, When the splitter is used in recommendation or HPO flow, Then no API migration is required at that call site.
3. Given `groups` length does not match `X`, When `split` runs, Then it raises a clear validation error.

### User Story 2 - Prevent Label-Window Leakage (Priority: P1)

A reviewer wants proof that train label windows never overlap the active test span.

Why this priority: The core algorithm exists to prevent horizon leakage in time-series model validation.

Independent Test: Generate multiple horizons and seeds, then assert every retained train sample has a label window disjoint from the test span.

Acceptance Scenarios:

1. Given a test block with start and label-end span, When train candidates are evaluated, Then any train row whose label window overlaps the test span is removed.
2. Given variable horizons, When folds are generated, Then the no-overlap property still holds.
3. Given adjacent train rows after the test block, When the test horizon reaches them, Then post-test purge removes them.

### User Story 3 - Apply Embargo After Test Blocks (Priority: P1)

A reviewer wants serial-correlation leakage reduced by removing samples immediately after each test block.

Why this priority: Purge handles label-window overlap, while embargo handles nearby observations after the test block.

Independent Test: Use a known index layout and assert the expected post-test embargo rows are absent from train indices.

Acceptance Scenarios:

1. Given `embargo_pct=0`, When split runs, Then no extra embargo rows are removed beyond purge.
2. Given `embargo_pct>0`, When split runs, Then the calculated post-test embargo rows are removed from train.
3. Given `embargo_pct >= 1`, When the splitter is constructed or used, Then it raises a validation error.

### User Story 4 - Use Only OOF Probability For Backtest (Priority: P1)

A reviewer wants backtest results to be based only on out-of-fold model predictions.

Why this priority: In-sample or latest probability can overstate historical performance.

Independent Test: Patch or inspect the backtest input path and assert it receives `oof_probs.fillna(0.5)` rather than latest or in-sample probabilities.

Acceptance Scenarios:

1. Given OOF probabilities with missing rows, When backtest input is built, Then missing values are filled with neutral `0.5`.
2. Given latest probability is available, When backtest runs, Then latest probability is not used as historical backtest input.
3. Given OOF probability is unavailable, When readiness is evaluated, Then live-capital readiness remains blocked.

### User Story 5 - Keep Investment Readiness Safety Gates (Priority: P1)

A local operator wants research results to remain visible while live investment candidates stay blocked when readiness gates fail.

Why this priority: The dashboard must separate raw model score from investable readiness.

Independent Test: Use candidate fixtures with failing accuracy, AUC, alpha, or completed-trade gates and verify readiness fields.

Acceptance Scenarios:

1. Given `accuracy < 0.50`, When readiness is exported, Then `new_capital_allowed=false`.
2. Given `auc < 0.50`, When readiness is exported, Then the candidate remains `AMBER_WATCHLIST`.
3. Given `alpha < 0`, When readiness is exported, Then live queue action remains blocked.
4. Given `completed_trades < 50`, When readiness is exported, Then `paper_trading_only=true`.

### User Story 6 - Correct Documentation And CLI Wording (Priority: P2)

A local operator wants the report and CLI wording to describe the actual CV behavior.

Why this priority: Calling PurgedKFold output "walk-forward" or `TimeSeriesSplit(gap=...)` can mislead review and readiness decisions.

Independent Test: Search relevant docs and CLI help text for outdated CV wording after the patch.

Acceptance Scenarios:

1. Given documentation refers to the operating CV, When it describes this feature, Then it uses `purged k-fold OOF CV` or equivalent accurate wording.
2. Given a legacy `TimeSeriesSplit(gap=...)` reference remains, When reviewed, Then it is clearly marked as legacy or removed.
3. Given `cv_gap` is shown in payload or docs, When read by a reviewer, Then its meaning is not confused with horizon itself.

### Edge Cases

- EC1: `n_splits < 2` -> reject with a clear error.
- EC2: `n_splits > len(X)` -> reject with a clear error.
- EC3: `embargo_pct < 0` -> reject with a clear error.
- EC4: `embargo_pct >= 1` -> reject with a clear error.
- EC5: `groups` missing in financial CV call sites -> test or review must catch the issue.
- EC6: `groups` contains unsupported datetime-like values in the current API -> reject clearly or route through a documented helper.
- EC7: OOF probabilities contain NaN for unscored rows -> fill with neutral `0.5` for backtest only.
- EC8: All candidates fail readiness gates -> keep research output but block live-capital readiness.

## Requirements

### Functional Requirements

- FR-001: The system MUST preserve the public splitter API `PurgedKFold(n_splits, embargo_pct).split(X, y=None, groups=...)`.
- FR-002: The splitter MUST require valid `groups` at financial CV call sites covered by repository rules.
- FR-003: The splitter MUST reject `groups` whose length differs from `X`.
- FR-004: The splitter MUST reject `embargo_pct < 0`.
- FR-005: The splitter MUST reject `embargo_pct >= 1`.
- FR-006: The splitter MUST reject invalid split counts.
- FR-007: The splitter MUST remove train samples whose label windows overlap the active test span.
- FR-008: The splitter MUST remove post-test embargo samples based on `embargo_pct`.
- FR-009: The splitter MUST produce deterministic folds for the same input.
- FR-010: The recommendation pipeline MUST fit scalers and models inside each train fold only.
- FR-011: The recommendation pipeline MUST use OOF probabilities as historical backtest input.
- FR-012: The recommendation pipeline MUST fill missing OOF backtest probabilities with neutral `0.5`.
- FR-013: The recommendation pipeline MUST NOT use latest probability as historical backtest input.
- FR-014: HPO flow MUST pass label-end `groups` into PurgedKFold when purged CV is selected.
- FR-015: Readiness export MUST keep `new_capital_allowed=false` when any readiness gate fails.
- FR-016: Readiness export MUST keep `paper_trading_only=true` when any readiness gate fails.
- FR-017: Readiness export MUST preserve raw score separately from investment readiness score.
- FR-018: Documentation MUST describe the operating CV method without mislabeling it as strict walk-forward when it is PurgedKFold.
- FR-019: CLI help text MUST describe `cv_gap` or embargo-related options using the actual implemented meaning.
- FR-020: The docs reference implementation MUST remain either clearly marked as reference-only or be superseded by the operating implementation.

### Non-Functional Requirements

- NFR-001 (Safety): The feature MUST NOT introduce broker, account, order, or secret operations.
- NFR-002 (Compatibility): Existing recommendation and HPO call sites SHOULD keep their current API shape.
- NFR-003 (Testability): Leakage, embargo, OOF-only backtest, and readiness behavior MUST be covered by targeted tests.
- NFR-004 (Determinism): Split outputs MUST be deterministic for identical inputs.
- NFR-005 (Traceability): Documentation updates MUST make clear which CV method is used for research OOF scoring and which checks block live readiness.
- NFR-006 (Auditability): Dashboard snapshot verification MUST show readiness fields after the change.

## Interfaces & Contracts

### Splitter Contract

- Input:
  - `X`: array-like sample matrix or indexable collection.
  - `y`: optional, ignored unless existing compatibility requires it.
  - `groups`: label end index or horizon end position for each sample.
- Output:
  - Iterator of `(train_idx, test_idx)` index arrays.
- Contract:
  - Test folds are contiguous blocks.
  - Train indices exclude test indices.
  - Train label windows do not overlap the active test span.
  - Embargo rows after each test block are excluded.

### Recommendation Pipeline Contract

- Fold training must fit preprocessing and model state only on each train fold.
- Historical backtest input must be OOF probability.
- Neutral fill value for missing OOF backtest rows is `0.5`.
- Latest or full-sample predictions may be reported as current signal but must not be counted as historical backtest performance.

### Readiness Output Contract

- Failing readiness gates must set:
  - `investment_readiness_status="AMBER_WATCHLIST"` or equivalent existing status.
  - `new_capital_allowed=false`.
  - `paper_trading_only=true`.
  - live queue action blocked.
- Raw score remains visible and separate from readiness score.

## Assumptions & Dependencies

### Assumptions

- A1: `docs/purged_kfold_embargo.py` is a reference implementation, not the final operating API.
- A2: The operating implementation should keep positional `groups` semantics for this patch.
- A3: Datetime/t1 support is not required for this patch unless the current code already accepts it safely.
- A4: PurgedKFold OOF CV is acceptable for research scoring, but not sufficient by itself to approve live investment.
- A5: Chronological holdout or stricter live simulation can be handled as a separate follow-up.

### Dependencies

- D1: `src/stock_rtx4060/ml/cv.py` for the operating splitter.
- D2: `src/stock_rtx4060/recommendation_engine.py` for OOF probability and backtest input behavior.
- D3: `src/stock_rtx4060/ml/hpo.py` for purged CV groups wiring.
- D4: `tests/test_purged_kfold.py` for splitter behavior verification.
- D5: `tests/test_walk_forward_purged.py` for recommendation pipeline OOF behavior verification.
- D6: `tests/test_ml_hpo.py` for HPO groups verification.
- D7: Dashboard export path for readiness snapshot verification.

## Success Criteria

- SC-001: `tests/test_purged_kfold.py` includes and passes partition, deterministic, no-overlap, post-test purge, and embargo validation tests.
- SC-002: `tests/test_walk_forward_purged.py` includes and passes an OOF-only backtest contract test.
- SC-003: `tests/test_ml_hpo.py` includes and passes a purged-CV groups forwarding test.
- SC-004: Targeted command `py -3.12 -m pytest tests\test_purged_kfold.py tests\test_walk_forward_purged.py tests\test_ml_hpo.py -q` passes.
- SC-005: `py -3.12 -m pytest tests\test_dashboard_bridge.py -q` passes after readiness snapshot behavior remains intact.
- SC-006: Latest dashboard-export snapshot still contains readiness fields including `new_capital_allowed`, `paper_trading_only`, status, score, and blocking reasons.
- SC-007: Search results show no misleading current-use wording that describes PurgedKFold OOF CV as strict walk-forward.
- SC-008: No broker, account, order, or secret operation is added.

## Traceability

| Scenario | Requirements | Success Criteria |
|---|---|---|
| User Story 1 | FR-001, FR-002, FR-003, FR-006 | SC-001, SC-004 |
| User Story 2 | FR-007, FR-009 | SC-001, SC-004 |
| User Story 3 | FR-004, FR-005, FR-008 | SC-001, SC-004 |
| User Story 4 | FR-010, FR-011, FR-012, FR-013 | SC-002, SC-004 |
| User Story 5 | FR-015, FR-016, FR-017 | SC-005, SC-006 |
| User Story 6 | FR-018, FR-019, FR-020 | SC-007 |

## Open Questions & Clarifications

### Open Questions

- Q1: Should datetime/t1 support be added in this patch, or explicitly deferred to a later time-based embargo patch?
- Q2: Should `cv_gap` be renamed in payloads, or should documentation clarify the existing name without schema changes?

### Clarifications Log

- 2026-05-29:
  - Q: Should the docs reference implementation replace the operating API directly?
  - A: No. Preserve `PurgedKFold(...).split(X, groups=...)` and port only the leakage-control behavior.
  - Q: Should failing readiness gates remove research candidates entirely?
  - A: No. Keep research candidates as `AMBER_WATCHLIST`, but block live capital.

## Risks & Mitigations

- R1: Changing `groups` semantics can shift model performance metrics. Mitigation: preserve current API and add explicit groups tests.
- R2: OOF neutral fill can affect reported performance. Mitigation: keep it test-covered and document it as backtest-only neutral fill.
- R3: Documentation may overstate live readiness. Mitigation: keep readiness wording tied to HARD BLOCK and paper trading only.
- R4: Datetime support may be assumed from the docs reference file. Mitigation: mark datetime/t1 support as deferred or explicitly unsupported in this patch.

## Reviewer Checklist

- [ ] API compatibility is preserved.
- [ ] `groups` is passed at financial CV call sites.
- [ ] Purge removes overlapping label windows.
- [ ] Embargo removes rows immediately after the test block.
- [ ] OOF probability is the only historical backtest input.
- [ ] Readiness fields still block live capital on failed gates.
- [ ] CLI and docs wording match the actual CV method.
- [ ] Targeted tests pass.
- [ ] Dashboard-export readiness snapshot is verified.

## Approval Readiness

Status: Draft.

This spec is implementation-ready after Q1 and Q2 are accepted as deferred or answered. It is not an approval to invest or trade.

## Changelog

- v0.1.0 (2026-05-29): Initial spec derived from `20260529_plan-purged-kfold-embargo-integration.md`.
