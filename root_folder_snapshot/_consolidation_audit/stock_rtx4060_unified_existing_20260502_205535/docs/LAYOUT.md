# LAYOUT

## Tree

```text
stock_rtx4060_unified/
├── README.md
├── CHANGELOG.md
├── main.py
├── stock_investment_os.py
├── run.ps1
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── requirements-gpu-wsl.txt
├── src/
│   └── stock_rtx4060/
├── tests/
├── docs/
├── examples/
├── reports/
├── workspaces/
├── archive/
│   └── original_inputs/
├── review_needed/
└── tools/
```

## Active Source

| Path | Purpose |
|---|---|
| `src/stock_rtx4060/main.py` | CLI router. |
| `src/stock_rtx4060/feature_engine.py` | Algorithm v2 feature generation. |
| `src/stock_rtx4060/ensemble_model.py` | Model training, CV, and prediction. |
| `src/stock_rtx4060/backtester.py` | Dry-run backtesting. |
| `src/stock_rtx4060/recommendation_engine.py` | Report-only candidate ranking. |
| `src/stock_rtx4060/reports.py` | Markdown/JSON/CSV report writer. |
| `src/stock_rtx4060/risk_rules.py` | Track-S and Track-L gates. |
| `src/stock_rtx4060/hw_profile.py` | Runtime/GPU checks. |
| `tests/test_core.py` | Regression tests for selected runtime path. |

## Generated/Review Areas

- `reports/`: consolidation reports and future runtime output.
- `review_needed/`: non-runtime source evidence requiring manual review.
- `workspaces/`: reserved for future generated runs; source workspaces were not copied wholesale.
