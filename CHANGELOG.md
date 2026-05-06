# Changelog

All notable changes for `stock_rtx4060_unified` are documented here.

## 2026-05-03 — Phase B Backtest Honesty Suite + Risk-adjusted Evidence

### Added

- **`src/stock_rtx4060/backtest_honesty.py`**: Added evidence-only PASS/AMBER/FAIL checks for OOF coverage, Sharpe floor, max drawdown, transaction-cost buffer, and walk-forward gap.
- **`tests/test_backtest_honesty.py`**: Added deterministic unit tests for strong evidence, weak OOF/cost buffer evidence, excessive drawdown, and run-level summary aggregation.
- **`backtest_honesty` result field**: Recommendation JSON now carries candidate-level Phase B honesty evidence.
- **`backtest_honesty_summary` top-level field**: Recommendation JSON and `dashboard_snapshot.v1` now carry additive run-level honesty evidence.
- **Audit event**: `audit_log.jsonl` now includes a `backtest_honesty_summary` event after report writing.

### Changed

- **`src/stock_rtx4060/recommendation_engine.py`**: Adds Phase B honesty evidence after model/backtest calculation without changing score functions or ranking keys.
- **`src/stock_rtx4060/dashboard_bridge.py`**: Preserves additive Phase B honesty fields while remaining compatible with older payloads.

### Security

- Phase B remains report-only. A Backtest Honesty PASS is evidence for manual review only and does not approve a trade.
- Phase B adds no broker execution, account write, auto-buy, auto-sell, margin, options, or order-routing behavior.

### Evidence

- RED test observed first: `tests/test_backtest_honesty.py` failed with `ModuleNotFoundError: No module named 'stock_rtx4060.backtest_honesty'`.
- Targeted GREEN check: `pytest tests/test_backtest_honesty.py tests/test_dashboard_bridge.py::test_build_dashboard_snapshot_preserves_report_only_contract tests/test_dashboard_bridge.py::test_dashboard_snapshot_accepts_older_payload_without_provider_summary tests/test_core.py::test_recommendation_engine_synthetic_run -q`: PASS, 7 tests passed.
- `python -m compileall main.py src tests`: PASS.
- `python main.py --help`: PASS with the project `.venv`.
- `pytest -q`: PASS, 30 tests passed.
- `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\phase_b_backtest_honesty_smoke`: PASS, generated Markdown, JSON, and `audit_log.jsonl`.
- `dashboard-export` to `reports\phase_b_backtest_honesty_smoke\dashboard_snapshot.json`: PASS, preserved `backtest_honesty_summary.status=AMBER`, candidate `backtest_honesty.status=AMBER`, and `screening_output_only=True`.
- `audit_log.jsonl`: PASS, includes event type `backtest_honesty_summary`.

## 2026-05-03 — Phase A Commit And GitHub Upload Evidence

### Added

- Recorded the Phase A local commit and remote upload evidence for the point-in-time provider validation and Provider v2 dashboard work.

### Evidence

- Local commit created: `cb98a21 Add Phase A provider validation dashboard evidence`.
- Remote upload command: `git push origin main`.
- Remote repository: `https://github.com/macho715/stock_1901.git`.
- Branch: `main`.
- Post-push verification: `HEAD` and `origin/main` both resolved to `cb98a210e6a391342971fb5a1e1aeb2a301917e5`.
- Working tree check: `git status --short` showed no changed files, with only existing permission warnings for `pytest-cache-files-kejv6w85/` and `pytest-cache-files-kr3txwkz/`.

## 2026-05-03 — Phase A Point-in-time Provider Validation + Provider v2 Dashboard

### Added

- **`src/stock_rtx4060/provider_validation.py`**: Added point-in-time OHLCV validation for provider-loaded frames. It checks row count, first/last date, future-dated rows, duplicate dates, required OHLCV columns, null critical values, and freshness evidence.
- **`tests/test_provider_validation.py`**: Added unit coverage for PASS, missing-column FAIL, future/duplicate-date FAIL, and stale real-provider AMBER behavior.
- **Provider validation metadata**: Provider audit events now include `provider_validation_status`, row count, first/last date, freshness days, duplicate/future row counts, and evidence.
- **`provider_summary`**: Recommendation JSON and `dashboard_snapshot.v1` now carry an additive top-level provider summary for dashboard REC display.
- **Planning docs**: Added `docs/plan_phase_a_point_in_time_provider_v2_dashboard_2026-05-03.md` and `docs/SPEC_PHASE_A_POINT_IN_TIME_PROVIDER_V2_DASHBOARD_2026-05-03.md`.

### Changed

- **`src/stock_rtx4060/data_providers.py`**: Provider loads validate normalized OHLCV frames before returning `ProviderResult`.
- **`src/stock_rtx4060/recommendation_engine.py`**: Recommendation runs collect provider metadata once per ticker/period/provider cache key and write top-level `provider_summary`.
- **`src/stock_rtx4060/dashboard_bridge.py`**: Dashboard snapshots preserve `provider_summary` when present and remain compatible with older payloads that do not include it.

### Security

- Audit metadata continues to pass through existing secret masking in `audit_log.py`.
- Phase A remains report-only. It adds no broker execution, account write, auto-buy, auto-sell, margin, options, or order-routing behavior.

### Evidence

- `python -m compileall main.py src tests`: PASS.
- `python main.py --help`: PASS with the project `.venv`.
- `pytest -q`: PASS, 26 tests passed.
- `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/phase_a_provider_v2_smoke`: PASS, generated Markdown, JSON, and `audit_log.jsonl`.
- `dashboard-export` to `reports/phase_a_provider_v2_smoke/dashboard_snapshot.json` and `..\stock-pred-v5\public`: PASS, exported `dashboard_snapshot.json` and `audit_log.jsonl`.
- `stock-pred-v5` `npm run build`: PASS with existing Vite chunk-size warning.
- `stock-pred-v5` `npx playwright test --reporter=line`: PASS, 2 tests passed.

## 2026-05-03 — Algorithm Upgrade (v2.1)

### Added

- **`src/stock_rtx4060/feature_engine.py`**: 10 new technical indicators (+18 feature columns, total ~93)
  - `chaikin_money_flow(period=20)` → `cmf_20`: volume-weighted money flow oscillator
  - `keltner_channel(period=20, atr_mult=2.0)` → `kc_pct`, `kc_width`: ATR-based channel position and width
  - `vortex_indicator(period=14)` → `vi_plus_14`, `vi_minus_14`, `vi_diff_14`: directional movement indicators
  - `trix(period=15)` → `trix_15`: triple-smoothed EMA momentum (strong noise filter)
  - `elder_ray(period=13)` → `elder_bull_13`, `elder_bear_13`: bull/bear power relative to EMA
  - `dpo(period=20)` → `dpo_20`: Detrended Price Oscillator for cycle detection

- **`src/stock_rtx4060/ensemble_model.py`**: Added `RandomForestClassifier` as a new model kind
  - New `model_kind = "rf"` option: balanced RF with `max_features="sqrt"`, `n_estimators=200`
  - Extended "auto" fallback chain: **XGBoost → RandomForest → Logistic Regression**
  - `ModelKind` type extended to include `"rf"`

- **`src/stock_rtx4060/risk_rules.py`**: ATR-based dynamic stop-loss for Track-S
  - `evaluate_track_s_candidate()` accepts new `atr_pct: float | None` parameter
  - When provided, effective stop = `max(fixed_stop_pct, 2 × ATR%)` — adapts to current volatility
  - `score_track_s()` now includes **Chaikin Money Flow** (+8 pts max) and **Vortex VI diff** (+4/-3 pts) in scoring

- **`src/stock_rtx4060/main.py`**: `predict` command passes `atr_pct_14` to `evaluate_track_s_candidate`; `--model-kind` choices now include `"rf"`

- **`src/stock_rtx4060/recommendation_engine.py`**: `model_kind` Literal extended with `"rf"`

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
