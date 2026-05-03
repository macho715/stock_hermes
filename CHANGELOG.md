# Changelog

All notable changes for `stock_rtx4060_unified` are documented here.

## 2026-05-03 — Real Data Ops Phase 1-5 Implementation

### Added

- **`src/stock_rtx4060/validation_gates.py`** (NEW): G-01~G-10 validation gate functions — DATA_FRESHNESS, PRICE_CROSSCHECK, SCHEMA_COMPLETENESS, CORP_ACTION_SANITY, MODEL_HEALTH (AUC≥0.55), OOF_COVERAGE (≥70%), RISK_PLAN (R/R Track-S≥2.0/Track-L≥1.5), BACKTEST_SANITY (MDD<20%), APPROVAL, AUDIT_EVIDENCE
- **`src/stock_rtx4060/journal.py`** (NEW): Journal entry writer, SHA-256 hash utilities, `generate_journal_id()` (format: `JRN-{YYYY}-{MMDD}-{TICKER}-{TRACK}-{SEQ}`)
- **`src/stock_rtx4060/data_providers.py`**: Added `pykrx` + `fdr` to `ALLOWED_PROVIDERS`; added `metadata` field to `ProviderResult`; implemented `_load_pykrx()` + `_load_fdr()` with fallback chain PyKRX → FDR → FAIL

### Changed

- **`data_providers.py`**: `ProviderResult` dataclass extended with `metadata: dict[str, Any] | None` for ticker_type, data_freshness_minutes, market_close_adj, source_timestamp
- **`data_providers.py`**: `DataProviderName` type extended to include `"pykrx"`, `"fdr"`

### Documentation

- `docs/REAL_DATA_OPS_PHASE1_SOURCE_CONTRACT_2026-05-03.md` — ✅ APPROVED (PyKRX primary, FDR fallback, yfinance research-only)
- `docs/REAL_DATA_OPS_PHASE2_VALIDATION_GATE_DESIGN_2026-05-03.md` — ✅ APPROVED (all 10 gates)
- `docs/REAL_DATA_OPS_PHASE3_APPROVAL_AUDIT_DESIGN_2026-05-03.md` — ✅ APPROVED (state machine, role matrix, append-only audit, secret masking, journal)
- `docs/REAL_DATA_OPS_PHASE4_REPORT_DASHBOARD_CONTRACT_2026-05-03.md` — ✅ APPROVED (report additions, gate_status dict, journal output)
- `docs/REAL_DATA_OPS_PHASE5_IMPLEMENTATION_READINESS_2026-05-03.md` — Phase 5 confirmed (FDR installed, all-KRX universe accepted); Task Group A+B implemented

### Evidence

- FDR import verified: `import FinanceDataReader` → OK
- PyKRX import verified: `from pykrx import stock` → OK
- `main.py --test`: PASS
- `pytest -q`: 19/19 PASS
- G-01 G-05 G-07 G-02 gate smoke tests: PASS

## 2026-05-03 — Documentation System Update

### Added
- README.md: Cross-project role section, system flow Mermaid, features list, tech stack table
- docs/SYSTEM_ARCHITECTURE.md: Component topology + sequence diagram + module dependency Mermaids + tech stack
- docs/LAYOUT.md: Full source tree + folder hierarchy Mermaid + config files map
- run.ps1: WSL TensorFlow GPU wrapper commands `tensorflow-gpu-wsl-check`, `tf-gpu-wsl`, and `tf-gpu-smoke`
- README.md and docs/SETUP.md: documented the split between Windows TensorFlow CPU smoke and WSL TensorFlow GPU smoke

### Features Documented (from code analysis)
- Walk-forward ensemble with leak-safe TimeSeriesSplit(gap=horizon) in ensemble_model.py
- 9 sequential risk gates: DATA_ROWS → LIQUIDITY → MARKET_REGIME → MODEL_EDGE → OOF_COVERAGE → BACKTEST_SANITY → RISK_PLAN → TRACK_SCORE → AUTOMATION_BOUNDARY
- dashboard_bridge.py → dashboard_snapshot.v1 JSON schema for stock-pred-v5 REC tab
- api_server.py Flask API with /api/recommend, /api/snapshot, /api/health endpoints
- preview_server.py unified launcher (Flask thread + Vite subprocess + browser open)

### System Notes
- Cross-project: stock-pred-v5 REC tab consumes dashboard_snapshot.json or Flask /api/recommend
- dashboard_snapshot.v1 schema: {version, generated_at_utc, source, results[]}
- screening_output_only=True on all recommendation outputs — no broker execution
- WSL TensorFlow GPU smoke verified TensorFlow 2.21.0 on `/physical_device:GPU:0`, GPU matmul PASS, and LSTM smoke PASS.

## [Unreleased] - 2026-05-02

### Added

- Created a new unified folder from four reviewed roots.
- Moved the active package to `src/stock_rtx4060`.
- Added wrapper-compatible root `main.py` and `run.ps1`.
- Added consolidated tests and docs.
- Added inventory, conflict, exclusion, validation, and cross-review reports under `reports/`.
- Added synchronized documentation status for the validated operator path, default Python caveat, review-needed evidence, and report-only safety boundary.
- Added Continue PR-quality gate checks under `.continue/checks/`.
- Added `docs/CONTINUE_MERGED_USAGE_GUIDE.md` for the current unified structure.
- Added `ops-v1` CLI workflow for report-only candidate screening, manual approval templates, ZERO logs, and workflow summaries.
- Added full documentation sync for `ops-v1`, project `.venv`, validation evidence, and current report-only safety boundaries.
- Added Phase 1 provider abstraction in `src/stock_rtx4060/data_providers.py` for `auto`, `synthetic`, `yfinance`, and optional `openbb`.
- Added masked JSONL audit logging in `src/stock_rtx4060/audit_log.py`.
- Added Phase 1 read/report-only MCP adapter contract in `src/stock_rtx4060/mcp_adapter.py`; no local MCP server is started.
- Added `--data-provider` and `--provider-config` to `recommend` and `ops-v1`.
- Added optional `requirements-openbb.txt` and `config/data_providers.example.json`.
- Added provider/audit/MCP tests: `tests/test_audit_log.py`, `tests/test_data_providers.py`, and `tests/test_mcp_adapter.py`.
- Added `src/stock_rtx4060/dashboard_bridge.py` and `dashboard-export` to create `dashboard_snapshot.v1` files from recommendation JSON.
- Added `tests/test_dashboard_bridge.py` for dashboard snapshot conversion, report-only preservation, and missing-field validation.
- Added `BACKEND` snapshot import support to `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`.
- Added repo-owned dashboard copy and browser smoke harness under `dashboard/`.
- Added `docs/REPORTS_POLICY.md` for generated runtime report handling.

### Changed

- Kept the active integrated Algorithm v2 implementation from `workspaces/stock_rtx4060`.
- Excluded runtime outputs, cache files, bundle duplicates, and older superseded patch sources from the executable path.
- Updated active documentation to point at `stock_rtx4060_unified` and the verified `.\run.ps1 self-test` workflow.
- Deleted the four superseded source roots after approval A and copied pre-delete audit evidence into `reports/delete_audit_20260502_211154`.
- Adapted Continue guide references from the old `workspaces/stock_rtx4060` layout to the active `src/stock_rtx4060` package layout.
- Pinned NumPy and pandas below the next major version for the Python 3.12 `.venv` runtime path.
- Routed recommendation OHLCV loading through the provider router while preserving `--synthetic` and yfinance behavior.
- Updated Ops v1 summary output to include the generated `audit_log.jsonl` path.
- Updated README, setup, layout, architecture, and Continue checks for the provider/audit/MCP Phase 1 scope.
- Added per-run OHLCV caching in `RecommendationEngine` so Track-S and Track-L reuse the same ticker/provider data load during one CLI run.
- Updated README, setup, layout, architecture, and dashboard bridge Spec docs for the file-based dashboard workflow.
- Added `.gitignore` rules for generated runtime report outputs without deleting existing reports.
- Synchronized UI/UX, dashboard bridge plan/spec, goal, and dashboard README docs with the repo-owned dashboard copy and browser smoke verification evidence.

### Security

- No broker order execution path exists in the unified package.
- No secrets or `.env` values were copied.
- Audit log serialization masks obvious API keys, tokens, passwords, authorization values, account identifiers, and private URLs.

### Evidence

- Generated by consolidation run at `20260502_205535`.
- Current Codex session confirmed `.\run.ps1 self-test` passed after consolidation.
- Delete audit files: `reports/delete_audit_20260502_211154/deleted_targets_before.csv`, `deleted_files_before.csv`, `deleted_targets_after.csv`, `empty_parent_removed.csv`, and `runtime_cache_removed.csv`.
- Current regression verification: `.venv\Scripts\python.exe -m pytest -q` passed with 19 tests after dashboard bridge coverage was added.
- Phase 1 smoke outputs: `reports/recommendations_phase1_smoke/` and `reports/ops_v1_phase1_smoke/` include `audit_log.jsonl`.
- OpenBB cache smoke output: `reports/recommendations_openbb_cache_smoke/audit_log.jsonl` contains 1 provider event for AAPL after OHLCV caching.
- Dashboard bridge smoke output: `reports/dashboard_bridge_smoke/dashboard_snapshot.json` contains `dashboard_snapshot.v1`, `report_only`, 2 results, and `screening_output_only=True`.
- Dashboard browser verification output: `reports/dashboard_browser_verification/dashboard_browser_verification.md` records a PASS result from `node dashboard\verify_bridge_smoke.mjs`.
- Document/code fit review reports: `reports/doc_code_fit_review_round_1.md`, `reports/doc_code_fit_review_round_2.md`, and `reports/doc_code_fit_review_round_3.md`.
