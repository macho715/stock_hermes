# PATCH_NOTES

The unified package keeps the active integrated Algorithm v2 implementation from `workspaces/stock_rtx4060`. Older patch copies are recorded in inventory and excluded or marked review-needed.

## Current Patch State

| Item | Decision |
|---|---|
| Active code source | Kept from the integrated workspace package. |
| Legacy recommendation patch docs | Moved to `review_needed/` when command syntax did not match the active CLI. |
| Bundle duplicates | Excluded from the unified executable path when exact duplicates were detected. |
| Runtime outputs | Excluded unless needed as generated validation evidence under `reports/`. |
| Original source folders | Deleted after approval A; audit copied to `reports/delete_audit_20260502_211154`. |

## Latest Documentation Sync

The active docs now reflect the post-consolidation validation split:

- `.\run.ps1 self-test` passed.
- Python 3.12 pytest passed with 5 tests.
- Default Python 3.14 is AMBER until pandas and pytest are installed.
