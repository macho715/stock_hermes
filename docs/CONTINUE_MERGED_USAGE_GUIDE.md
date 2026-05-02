# Continue Merged Usage Guide

## Purpose

Continue is integrated into `stock_rtx4060_unified` as a PR-level quality gate.

It is not a stock recommendation engine, broker order system, dashboard, or trading agent. It checks whether changes preserve the existing report-only stock screening boundary.

## Active Paths

| Item | Current Path |
|---|---|
| Active code | `src/stock_rtx4060/` |
| Tests | `tests/` |
| Runtime output | `reports/` |
| Continue checks | `.continue/checks/*.md` |
| Current architecture docs | `docs/SYSTEM_ARCHITECTURE.md`, `docs/LAYOUT.md`, `docs/AGENTS.md` |

## Check Files

| File | Purpose |
|---|---|
| `.continue/checks/01-financial-safety-boundary.md` | Blocks broker execution, direct trading advice, and guaranteed-return claims. |
| `.continue/checks/02-backtest-integrity.md` | Protects leak-safe validation and dry-run backtest integrity. |
| `.continue/checks/03-recommendation-contract.md` | Preserves Track-S/Track-L verdict, score, and risk-gate behavior. |
| `.continue/checks/04-secret-and-pii-safety.md` | Blocks secrets, account identifiers, private financial data, and unsafe logging. |
| `.continue/checks/05-gpu-claim-validation.md` | Requires runtime evidence before GPU or RTX4060 performance claims. |
| `.continue/checks/06-report-contract.md` | Keeps Markdown/JSON recommendation reports auditable and boundary-safe. |
| `.continue/checks/07-architecture-boundary.md` | Blocks unscoped API server, dashboard, broker, MCP server, or daemon additions. |
| `.continue/checks/08-test-and-verification.md` | Requires relevant compile, smoke, pytest, recommendation, and GPU evidence. |

## Operating Rule

Keep check files directly under `.continue/checks/`. Do not put checks in subdirectories.

Continue suggestions are advisory. A human must still review any suggested diff before applying it.

## Required Local Evidence

General changes:

```powershell
python -m compileall .
python main.py --help
.\run.ps1 self-test
```

Tests:

```powershell
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

Recommendation changes:

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\algo_v2_validation
```

GPU-related changes:

```powershell
.\run.ps1 env --xgboost --output reports\runtime_status_xgboost.json
.\run.ps1 benchmark --rows 800 --repeats 1 --include-gpu --output-dir reports\gpu_validation
```

## Safety Boundary

- Keep `screening_output_only=True`.
- Do not add broker API order execution.
- Do not convert reports into direct buy/sell instructions.
- Do not store secrets, account identifiers, or private portfolio data in reports.
- Do not claim GPU acceleration without runtime evidence.
