# AGENTS

This unified folder is report-only. Do not add broker execution, credentials, or destructive account actions.

Run the smallest relevant checks first:

```powershell
python -m compileall .
python main.py --help
python main.py self-test
python -m pytest -q
```

## Current Runtime Note

The recommended operator command is:

```powershell
.\run.ps1 self-test
```

Current observed result: PASS. The wrapper selected Python 3.12 and completed the self-test.

Default `python` was Python 3.14.4 during validation. It compiled and displayed help, but lacked pandas and pytest. Treat that interpreter path as AMBER unless dependencies are installed.

## Documentation Rule

When updating docs, keep these facts synchronized:

- Active package path: `src/stock_rtx4060`.
- Output path: `reports/`.
- Safety boundary: reports only, no broker orders.
- Current validation split: `run.ps1` PASS, default Python dependency path AMBER.
- Legacy source evidence stays in `review_needed/` until manually reviewed.
