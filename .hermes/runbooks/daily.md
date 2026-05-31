# Hermes Daily Runbook

1. Run `scripts/hermes/guard_safety.py`.
2. Run `scripts/hermes/repo_scan.py`.
3. Run `scripts/hermes/hermes_runner.py --mode read_report`.
4. Generate `reports/hermes/hermes-issue.md`.
5. Upload `reports/hermes/**` as artifacts.
6. Create an issue only on failure.

Never run broker or live order actions.
