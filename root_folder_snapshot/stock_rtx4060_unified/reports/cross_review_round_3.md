# Cross Review Round 3 - Documentation Consistency

Result: PASS

| Check | Result |
|---|---|
| README structure vs folder | Matches final `src/stock_rtx4060` layout. |
| docs/LAYOUT.md vs folder | Matches final root tree. |
| docs/SYSTEM_ARCHITECTURE.md vs code | Uses actual active package module names. |
| CHANGELOG.md | Records unified consolidation. |
| docs/SETUP.md commands | Uses verified `python main.py ...` and `.\run.ps1 ...` commands. |
| Stale active doc scan | No active docs mention `workspaces.stock_rtx4060`, `recommendations_*`, `NumpyLogistic`, `XGBOrFallback`, or `4 tests`. |
| Legacy `--recommend` | Exists only as compatibility alias in `src/stock_rtx4060/main.py`; legacy source docs are quarantined under `review_needed/source_evidence`. |

Patch applied: source evidence documents with old command syntax were moved out of active docs.
