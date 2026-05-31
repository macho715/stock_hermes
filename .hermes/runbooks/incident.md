# Hermes Incident Runbook

Use this when automation returns ZERO or AMBER.

1. Stop further automation.
2. Preserve `reports/hermes/run_manifest.json`.
3. Preserve `reports/hermes/ZERO.md` if present.
4. Report failed gate and exact command.
5. Request at most 3 inputs.

Do not hide partial failures.
