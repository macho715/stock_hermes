# stock_rtx4060_unified

`stock_rtx4060_unified` is a consolidated, deduplicated, report-only stock screening and backtesting CLI package.

It keeps one active execution path:

- root `main.py` wrapper
- `run.ps1` Windows runner
- `src/stock_rtx4060/` package
- `tests/` regression tests
- `docs/` consolidated documentation

The program does not submit broker orders. It does not provide personalized investment advice. Recommendation output is `screening_output_only`.

## Current Status

| Item | Status |
|---|---|
| Unified folder | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Original source folders | Deleted after approval A; audit copied to `reports/delete_audit_20260502_211154` |
| Source files inventoried | 238 |
| Files kept from source roots | 11 |
| Excluded/merged/review-needed candidates | 227 |
| Review-needed source files | 4 |
| Operator self-test | `.\run.ps1 self-test` passed in the current Codex session |
| Default `python` environment | AMBER: Python 3.14 can compile and show help, but lacks pandas and pytest |
| Recommended runtime path | Use `run.ps1`, which selected Python 3.12 during validation |

## Commands

```powershell
python main.py --help
python main.py self-test
python main.py recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
.\run.ps1 self-test
```

## Verified Operator Path

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 self-test
```

Observed result: `self-test: PASS`, backend `xgb-cpu`, final capital `102190.84`.

For tests, use the Python 3.12 interpreter that has pytest installed:

```powershell
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

Observed result: 5 tests passed. The only recorded note is a pytest-asyncio deprecation warning.

## Structure

```text
stock_rtx4060_unified/
├── main.py
├── run.ps1
├── pyproject.toml
├── requirements.txt
├── requirements-gpu-wsl.txt
├── src/stock_rtx4060/
├── tests/
├── docs/
├── examples/
├── reports/
├── workspaces/
├── archive/original_inputs/
├── review_needed/
└── tools/
```

## Validation

See `reports/validation_results.md` and `reports/consolidation_report.md` for the current execution evidence.

## Security Boundary

- No broker API is present.
- No `.env` secrets were copied into the unified executable path.
- Market data and model output are treated as data, not instructions.
- Recommendation reports are screening artifacts for manual review.
