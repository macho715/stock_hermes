# Hermes Approval Runbook

Use this before write, PR, or deployment actions.

Approval gates:
- `hermes-read`: read/report automation.
- `hermes-write`: draft PR and tracked file updates.
- `production`: deployment, blocked by default.

Rules:
- Prevent self-review where possible.
- Prefer draft PRs.
- Never auto-merge.
- Never enable live trading.
