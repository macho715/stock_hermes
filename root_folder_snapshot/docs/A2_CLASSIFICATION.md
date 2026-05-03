# A2 — Root-Level File Classification

Scope: `C:\Users\jichu\Downloads\주식\` root only. Subdirectories
(`stock-pred-v5/docs/`, `stock_rtx4060_unified/docs/`, `_consolidation_audit/`, etc.) are excluded.

| File Path | Title | Importance | In-Place Required | Reason |
|-----------|-------|------------|-------------------|--------|
| `README.md` | stock_rtx4060 Overview & Operations | 🔴 CRITICAL | YES | Root project README. Defines architecture, CLI commands (`run.ps1`, `main.py`), feature-engine, model, GPU, risk rules, recommendation scanner, backtester, reports, and verified run commands. Actively sourced by operators. |
| `AGENTS.md` | Agent Orchestration & Safety Rules | 🔴 CRITICAL | YES | Defines `screening_output_only` boundary, risk gates, GPU rules, reporting contract, and agent output contract. Directly governs every agent session in this repo. |
| `CLAUDE.md` | Claude Code Scope & Workflow | 🔴 CRITICAL | YES | Sets priority behaviors, validation expectations, approval gates, and Korean output rules for Claude Code sessions. Tightly coupled to `AGENTS.md`. |
| `CHANGELOG.md` | Changelog (append-only audit log) | 🟡 IMPORTANT | YES | Append-only change history with 2026-05-03 supplemental update. References `stock_rtx4060_unified/`, Vite dashboard, `stock-pred-v5/`, and all verified runtime evidence. Actively maintained. |
| `main.py` | CLI Compatibility Wrapper | 🔴 CRITICAL | YES | Root entry point that imports `workspaces.stock_rtx4060.main`. `run.ps1` calls it directly. All runtime commands route through here. |
| `run.ps1` | Windows PowerShell Runner | 🔴 CRITICAL | YES | Finds `.venv`, Python 3.12, 3.11, or `python`; calls `main.py`. Primary operator execution wrapper. Every verified command in README/AGENTS uses this. |
| `pyproject.toml` | pytest / ruff / black config | 🟡 IMPORTANT | YES | Configures `pytest -q`, ruff (py311, line-length 120), and black formatting. Referenced in `AGENTS.md` setup section. |
| `requirements.txt` | Base runtime dependencies | 🟡 IMPORTANT | YES | `numpy`, `pandas`, `scikit-learn>=1.1`, `tabulate`, `yfinance>=0.2.66`, `xgboost>=3.1.0`. Required by all active code paths. |
| `requirements-gpu-wsl.txt` | WSL2/Linux GPU dependencies | 🟡 IMPORTANT | NO | Extends `requirements.txt` with `tensorflow[and-cuda]>=2.16.1`. Only needed for optional WSL2 GPU path. Referenced in docs but not imported by active code. |
| `deep-research-report.md` | Production-Upgrade Technical Spec | 🟡 IMPORTANT | NO | 620-line Korean engineering spec for adding SEC EDGAR / OpenDART / KRX data adapters, validation gates, human-in-the-loop approval, immutable audit store, and FastAPI server to the current CLI-only system. Extensive but not yet implemented. Superseded in scope by `CONTINUE_MERGED_USAGE_GUIDE.md`. |
| `CONTINUE_MERGED_USAGE_GUIDE.md` | Continue AI Checks & PR Workflow | 🟡 IMPORTANT | NO | Documents 8 Continue `.continue/checks/` files, merged AGENTS/CLAUDE workflow blocks, PR checklist, branch protection rules, and ZERO/abort conditions. Not yet created in repo but referenced as planned. |
| `uiux2.md` | v1.0 Operational Spec — Track-S/L rules | 🟡 IMPORTANT | NO | Korean operational spec defining Track-S (score>=75, -4% stop, +5/+10% TP, 0.75% risk budget, max 20% position) and Track-L (score>=80, 12% bucket cap) rules, 5 report types, ZERO gates. References `stock_rtx4060/` path but is an earlier draft; `AGENTS.md` is the current authoritative source. |

---

## Text Stubs (no doc content — just thin re-exports or empty)

| File Path | Stub? | In-Place Required | Reason |
|-----------|-------|-------------------|--------|
| `backtester.py` | YES | NO | Text stub: `from main import cli` + `raise SystemExit(cli())`. Real `backtester.py` lives in `workspaces/stock_rtx4060/backtester.py`. |
| `ensemble_model.py` | YES | NO | File does not exist (was attempted read against `C:\Users\jichu\Downloads\주식\stock-pred-v5\` due to CWD shift). Real file is `workspaces/stock_rtx4060/ensemble_model.py`. |
| `feature_engine.py` | YES | NO | Same — file does not exist at root. Real file is `workspaces/stock_rtx4060/feature_engine.py`. |
| `hw_profile.py` | YES | NO | Same — file does not exist at root. Real file is `workspaces/stock_rtx4060/hw_profile.py`. |

---

## Orphaned / Outdated Files

| File Path | Status | Reason |
|-----------|--------|--------|
| `stock_investment_os.py` | 🟢 ARCHIVABLE | Stub: re-exports `main.py` for backward compatibility. `main.py` already covers this via `workspaces.stock_rtx4060.main`. Kept for legacy alias only. |
| `stock_pred_v5.jsx` | 🟢 ARCHIVABLE (orphan) | 1,863-line client-side React/Vite dashboard with synthetic OHLCV, LSTM/LogReg/XGBoost/RNN simulation, dual-market (US/KRX), and Yahoo Finance fetch. Live data import via `dashboard_snapshot.v1` JSON. Actively developed in `stock-pred-v5/` as a separate Vite app. This root copy is not referenced by any active script. |
| `stock_prediction_dashboard_1.jsx` | 🟢 ARCHIVABLE (orphan) | Older/v1 React dashboard (confirmed at root level). Simpler than `stock_pred_v5.jsx`. Not referenced by any active script or CI. Likely a predecessor. |
| `uiux2.md` | 🟢 ARCHIVABLE (duplicate) | Draft v1.0 spec. Active authoritative doc for Track-S/L rules is `AGENTS.md`. `uiux2.md` contains some operational detail but is superseded. Also note: `docs/uiux.md` exists in subdirectory. |

---

## Summary

- **CRITICAL (7):** `README.md`, `AGENTS.md`, `CLAUDE.md`, `main.py`, `run.ps1`, `pyproject.toml`, `requirements.txt`
- **IMPORTANT (5):** `CHANGELOG.md`, `requirements-gpu-wsl.txt`, `deep-research-report.md`, `CONTINUE_MERGED_USAGE_GUIDE.md`, `uiux2.md`
- **ARCHIVABLE orphans (4):** `stock_investment_os.py`, `stock_pred_v5.jsx`, `stock_prediction_dashboard_1.jsx`, `uiux2.md` (at root — distinct from `docs/uiux.md`)
- **Text stubs (4):** `backtester.py`, `ensemble_model.py`, `feature_engine.py`, `hw_profile.py` — all real implementations live in `workspaces/stock_rtx4060/`