# PATCH_NOTES

The unified package keeps the active integrated Algorithm v2 implementation under `src/stock_rtx4060`. Older patch copies are recorded in inventory and excluded or marked review-needed.

## Current Patch State

| Item | Decision |
|---|---|
| Active code source | Kept from the integrated workspace package. |
| Legacy recommendation patch docs | Moved to `review_needed/` when command syntax did not match the active CLI. |
| Bundle duplicates | Excluded from the unified executable path when exact duplicates were detected. |
| Runtime outputs | Excluded unless needed as generated validation evidence under `reports/`. |
| Original source folders | Deleted after approval A; audit copied to `reports/delete_audit_20260502_211154`. |
| Ops v1 workflow | Added as `src/stock_rtx4060/ops_workflow.py` and exposed through `.\run.ps1 ops-v1 ...`. |

## Latest Documentation Sync

The active docs now reflect the post-consolidation validation split:

- `.\run.ps1 self-test` passed with the project `.venv`.
- `.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider` passed with 15 tests after Phase 1 provider/audit and OHLCV cache integration.
- `.\run.ps1 ops-v1 --universe "AMZN,AAPL" ...` generated recommendation reports, daily brief, approval journal template, ZERO logs, and summary JSON with `error_count=0`.
- `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" ...` generated Markdown, JSON, and `audit_log.jsonl`.
- `.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.example.json --universe "AAPL" ...` generated `reports/recommendations_openbb_cache_smoke/audit_log.jsonl` with 1 provider event.
- Global Python 3.14 remains AMBER; project execution should use `.venv`.
