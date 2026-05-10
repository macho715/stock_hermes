# AGENTS

This unified folder is report-only. Do not add broker execution, credentials, or destructive account actions.

Run the smallest relevant checks first:

```powershell
.\.venv\Scripts\python.exe -m compileall main.py src tests
python main.py --help
.\run.ps1 self-test
.\.venv\Scripts\python.exe -m pytest -q
```

## Current Runtime Note

The recommended operator command is:

```powershell
.\run.ps1 self-test
```

Current observed result: PASS. The wrapper selected the project `.venv` Python 3.12 and completed the self-test.

Default `python` was Python 3.14.4 during earlier validation. Treat that global interpreter path as AMBER. Use the project `.venv` for runtime and tests.

## Documentation Rule

When updating docs, keep these facts synchronized:

- Active package path: `src/stock_rtx4060`.
- Output path: `reports/`.
- Safety boundary: reports only, no broker orders.
- Current validation split: `.venv` and `run.ps1` PASS, global Python dependency path AMBER.
- Ops v1 workflow: `ops-v1` creates recommendation reports, a daily brief, an approval journal template, ZERO logs, and a summary JSON.
- Legacy source evidence stays in `review_needed/` until manually reviewed.
- **Current test status (2026-05-10): 1,210 tests, 85.82% coverage** (target ≥85% ✅).
- **P0-P8 phases**: `observability/`, `data_lake/`, `factors/`, `ml/`, `portfolio/`, `backtest/`, `advisors/`, `broker/` subpackages active.
- **PurgedKFold**: `cv.split(X, groups=_groups)` must always receive `groups` — never `cv.split(X)`.
- **PIT `as_of` guard**: lake miss with `as_of!=None` raises `RuntimeError`.

## Continue Quality Gate Rule

Continue checks live at `.continue/checks/*.md`.

Use Continue as an advisory PR quality gate only. Do not treat Continue as:

- a stock recommendation engine
- a broker order executor
- an account-writing automation layer
- a source of approval to bypass manual review

`ops-v1` is allowed only as a report-only manual approval workflow. It must not emit broker orders.

When code changes touch `src/stock_rtx4060/`, verify the relevant check files still match the current architecture and run the smallest relevant local commands before reporting completion.
