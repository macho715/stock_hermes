# SPEC

## Scope

Consolidated stock screening, recommendation reporting, feature engineering, model validation, and dry-run backtesting.

The active executable package is `src/stock_rtx4060`. The root `main.py` is a wrapper, and `run.ps1` is the recommended Windows entrypoint.

## Non-goals

- No broker order execution.
- No personalized investment advice.
- No web dashboard in the current unified folder.

## Required Boundary

Every recommendation report must remain `screening_output_only`.

## Acceptance Evidence

| Requirement | Evidence |
|---|---|
| CLI starts | `python main.py --help` passed. |
| Package compiles | `python -m compileall .` passed. |
| Operator self-test runs | `.\run.ps1 self-test` passed in the current Codex session. |
| Regression tests run | Python 3.12 `pytest -q` passed with 5 tests. |
| Default interpreter caveat documented | Python 3.14 lacked pandas and pytest, so that path is AMBER. |
