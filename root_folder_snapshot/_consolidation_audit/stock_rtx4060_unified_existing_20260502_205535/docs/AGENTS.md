# AGENTS

## Scope

These instructions apply to `stock_rtx4060_unified`.

## Rules

- Keep active code under `src/stock_rtx4060`.
- Do not add broker order execution without a separate approved spec.
- Do not write secrets, account IDs, or broker credentials into reports.
- Treat `review_needed/` as non-runtime evidence.
- Run `python -m compileall .`, `python main.py --help`, and pytest after code changes.
