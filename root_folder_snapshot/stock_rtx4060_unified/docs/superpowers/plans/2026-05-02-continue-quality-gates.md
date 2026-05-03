# Continue Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Continue PR-quality checks into the current `stock_rtx4060_unified` system without copying the full `continue-main` source tree.

**Architecture:** Keep Continue as an advisory quality gate at repository root. Add flat Markdown checks under `.continue/checks/`, update current docs to point at `src/stock_rtx4060`, and verify the existing Python CLI still runs.

**Tech Stack:** Continue Markdown checks, Python CLI, PowerShell runner, pytest.

---

### Task 1: Add Continue Check Files

**Files:**
- Create: `.continue/checks/01-financial-safety-boundary.md`
- Create: `.continue/checks/02-backtest-integrity.md`
- Create: `.continue/checks/03-recommendation-contract.md`
- Create: `.continue/checks/04-secret-and-pii-safety.md`
- Create: `.continue/checks/05-gpu-claim-validation.md`
- Create: `.continue/checks/06-report-contract.md`
- Create: `.continue/checks/07-architecture-boundary.md`
- Create: `.continue/checks/08-test-and-verification.md`

- [x] Create a flat `.continue/checks/` directory.
- [x] Adapt guide content from `CONTINUE_MERGED_USAGE_GUIDE.md`.
- [x] Replace old `workspaces/stock_rtx4060` references with `src/stock_rtx4060`.

### Task 2: Update Current Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/AGENTS.md`
- Modify: `docs/SYSTEM_ARCHITECTURE.md`
- Modify: `docs/LAYOUT.md`
- Modify: `CHANGELOG.md`
- Create: `docs/CONTINUE_MERGED_USAGE_GUIDE.md`

- [x] Document Continue as a PR-quality gate, not a trading engine.
- [x] Document check location and active package path.
- [x] Keep report-only and manual-review-only boundaries explicit.

### Task 3: Verify

**Commands:**

```powershell
rg -n "workspaces/stock_rtx4060|workspaces\\stock_rtx4060" .continue docs README.md CHANGELOG.md
python -B main.py --help
.\run.ps1 self-test
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Expected:
- No active Continue/doc references to the old `workspaces/stock_rtx4060` source path.
- CLI help exits 0.
- Self-test exits 0.
- Pytest reports at least 6 passing tests after Ops v1 workflow integration.

## Current Addendum

After this plan was completed, `ops-v1` was added as a report-only manual approval workflow. Continue checks and active docs now also cover:

- `src/stock_rtx4060/ops_workflow.py`
- `.\run.ps1 ops-v1 ...`
- `approval_journal_template.csv`
- `zero_log.md` and `zero_log.csv`
- project `.venv` validation instead of a global Python 3.12 path
