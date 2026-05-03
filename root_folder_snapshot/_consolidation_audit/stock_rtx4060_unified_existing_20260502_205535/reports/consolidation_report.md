# Stock RTX4060 Unified Consolidation Report

## 1. Summary

| Item | Result |
|---|---|
| Generated | 2026-05-02 20:53:47 |
| Final folder | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Original source folders deleted | No |
| Source files inventoried | 238 |
| Source files kept in runtime path | 11 |
| Source files isolated in review_needed | 20 |
| Source files excluded from unified runtime | 207 |
| Exact duplicate groups | 31 |

## 2. Source Folders Reviewed

| No | Path | Files | Role | Notes |
|---:|---|---:|---|---|
| 1 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2` | 38 | Algorithm v2 source bundle | Inventoried with sha256. |
| 2 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2` | 26 | Bundle duplicate candidate | Inventoried with sha256. |
| 3 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_recommendation_patch` | 31 | Recommendation patch candidate | Inventoried with sha256. |
| 4 | `C:\Users\jichu\Downloads\주식\workspaces` | 143 | Active workspace and runtime evidence | Inventoried with sha256. |

## 3. Final Unified Folder

| Item | Value |
|---|---|
| Path | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Package | `src/stock_rtx4060` |
| Entry point | `main.py` |
| Runner | `run.ps1` |

## 4. Files Kept

| No | Path | Reason |
|---:|---|---|
| 1 | `src\stock_rtx4060\backtester.py` | Selected active validated source for unified executable package. |
| 2 | `src\stock_rtx4060\benchmark.py` | Selected active validated source for unified executable package. |
| 3 | `src\stock_rtx4060\ensemble_model.py` | Selected active validated source for unified executable package. |
| 4 | `src\stock_rtx4060\feature_engine.py` | Selected active validated source for unified executable package. |
| 5 | `src\stock_rtx4060\hw_profile.py` | Selected active validated source for unified executable package. |
| 6 | `src\stock_rtx4060\main.py` | Selected active validated source for unified executable package. |
| 7 | `src\stock_rtx4060\recommendation_engine.py` | Selected active validated source for unified executable package. |
| 8 | `src\stock_rtx4060\reports.py` | Selected active validated source for unified executable package. |
| 9 | `src\stock_rtx4060\risk_rules.py` | Selected active validated source for unified executable package. |
| 10 | `src\stock_rtx4060\__init__.py` | Selected active validated source for unified executable package. |
| 11 | `examples\sample_ohlcv.csv` | Selected active validated source for unified executable package. |
| 12 | `main.py` | Normalized support file for unified executable layout. |
| 13 | `stock_investment_os.py` | Normalized support file for unified executable layout. |
| 14 | `run.ps1` | Normalized support file for unified executable layout. |
| 15 | `pyproject.toml` | Normalized support file for unified executable layout. |
| 16 | `requirements.txt` | Normalized support file for unified executable layout. |
| 17 | `requirements-dev.txt` | Normalized support file for unified executable layout. |
| 18 | `requirements-gpu-wsl.txt` | Normalized support file for unified executable layout. |
| 19 | `tests/test_core.py` | Normalized support file for unified executable layout. |
| 20 | `README.md` | Normalized support file for unified executable layout. |
| 21 | `CHANGELOG.md` | Normalized support file for unified executable layout. |
| 22 | `docs/SETUP.md` | Normalized support file for unified executable layout. |
| 23 | `docs/SYSTEM_ARCHITECTURE.md` | Normalized support file for unified executable layout. |
| 24 | `docs/LAYOUT.md` | Normalized support file for unified executable layout. |
| 25 | `docs/AGENTS.md` | Normalized support file for unified executable layout. |
| 26 | `docs/SPEC.md` | Normalized support file for unified executable layout. |
| 27 | `docs/UIUX.md` | Normalized support file for unified executable layout. |
| 28 | `docs/PATCH_NOTES.md` | Normalized support file for unified executable layout. |

## 5. Files Excluded From Unified

Full list: `reports/deleted_or_excluded_candidates.csv`.

| No | Source Path | Reason | Duplicate Of | Risk |
|---:|---|---|---|---|
| 1 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ALGORITHM_PATCH_REPORT_2026.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 2 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\backtester.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 3 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\CHANGELOG_RECOMMENDATION_PATCH.md` | Superseded by normalized unified docs/config/tests or not referenced by selected runtime path. | `` | LOW |
| 4 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\DOC_REVIEW_AND_INSERTION.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 5 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ensemble_model.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 6 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\feature_engine.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 7 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\hw_profile.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 8 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\main.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 9 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\pyproject.toml` | Superseded by normalized unified docs/config/tests or not referenced by selected runtime path. | `` | LOW |
| 10 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\README.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 11 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_engine.py` | Python variant superseded by validated active package under workspaces/stock_rtx4060. | `` | AMBER |
| 12 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\requirements-gpu-wsl2.txt` | Superseded by normalized unified docs/config/tests or not referenced by selected runtime path. | `` | LOW |
| 13 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\requirements.txt` | Superseded by normalized unified docs/config/tests or not referenced by selected runtime path. | `` | LOW |
| 14 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\VALIDATION_LOG_ALGO_V2.txt` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 15 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\.pytest_cache\.gitignore` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 16 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\.pytest_cache\CACHEDIR.TAG` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 17 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\.pytest_cache\README.md` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 18 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\docs\CROSS_CHECK_2026.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 19 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 20 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 21 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 22 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 23 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 24 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 25 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161729.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 26 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161729.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 27 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161807.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 28 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161807.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 29 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\tests\test_algorithm_v2.py` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | `` | AMBER |
| 30 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\backtester.cpython-312.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 31 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\ensemble_model.cpython-312.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 32 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\feature_engine.cpython-312.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 33 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\hw_profile.cpython-312.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 34 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\main.cpython-312-pytest-8.3.5.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 35 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\__pycache__\recommendation_engine.cpython-312.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 36 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\tests\__pycache__\test_algorithm_v2.cpython-312-pytest-8.3.5.pyc` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 37 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\.pytest_cache\v\cache\nodeids` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 38 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\.pytest_cache\v\cache\stepwise` | Cache/build/runtime artifact directory excluded. | `` | LOW |
| 39 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\ALGORITHM_PATCH_REPORT_2026.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ALGORITHM_PATCH_REPORT_2026.md` | LOW |
| 40 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\backtester.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\backtester.py` | LOW |
| 41 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\CHANGELOG_RECOMMENDATION_PATCH.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\CHANGELOG_RECOMMENDATION_PATCH.md` | LOW |
| 42 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\DOC_REVIEW_AND_INSERTION.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\DOC_REVIEW_AND_INSERTION.md` | LOW |
| 43 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\ensemble_model.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ensemble_model.py` | LOW |
| 44 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\feature_engine.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\feature_engine.py` | LOW |
| 45 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\hw_profile.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\hw_profile.py` | LOW |
| 46 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\main.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\main.py` | LOW |
| 47 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\pyproject.toml` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\pyproject.toml` | LOW |
| 48 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\README.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\README.md` | LOW |
| 49 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_engine.py` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_engine.py` | LOW |
| 50 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\requirements-gpu-wsl2.txt` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\requirements-gpu-wsl2.txt` | LOW |
| 51 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\requirements.txt` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\requirements.txt` | LOW |
| 52 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\VALIDATION_LOG_ALGO_V2.txt` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\VALIDATION_LOG_ALGO_V2.txt` | LOW |
| 53 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\docs\CROSS_CHECK_2026.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\docs\CROSS_CHECK_2026.md` | LOW |
| 54 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.json` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.json` | LOW |
| 55 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161939.md` | LOW |
| 56 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.json` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.json` | LOW |
| 57 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_161955.md` | LOW |
| 58 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.json` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.json` | LOW |
| 59 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.md` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_reports\recommendations_algo_v2_20260502_162042.md` | LOW |
| 60 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161729.json` | Exact duplicate by sha256; one selected copy or review copy is sufficient. | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\reports\benchmark_algo_v2_20260502_161729.json` | LOW |
| ... | ... | 167 more rows in CSV | ... | ... |

## 6. Conflicts Resolved

Full list: `reports/conflict_resolution.csv`.

| No | File | Selected Version | Rejected Version | Reason |
|---:|---|---|---|---|
| 1 | `backtester.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\backtester.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\backtester.py | C:\Users\jichu\Down...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 2 | `ensemble_model.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ensemble_model.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\ensemble_model.py | C:\Users\ji...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 3 | `feature_engine.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\feature_engine.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\feature_engine.py | C:\Users\ji...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 4 | `hw_profile.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\hw_profile.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\hw_profile.py | C:\Users\jichu\Down...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 5 | `main.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\main.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\main.py | C:\Users\jichu\Downloads\주식\sto...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 6 | `recommendation_engine.py` | `Generated normalized target or review_needed` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_engine.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_engine.py...` | Selected validated active package/config/doc path or normalized doc; rejected variants recorded in inventory. |
| 7 | `README.md` | `Generated normalized target` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\README.md | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\README.md | C:\Users\jichu\Downloads\주식...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 8 | `backtester.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\backtester.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\backtester.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\backtester.py | C:\Users\jichu\Down...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 9 | `ensemble_model.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\ensemble_model.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\ensemble_model.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\ensemble_model.py | C:\Users\ji...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 10 | `feature_engine.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\feature_engine.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\feature_engine.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\feature_engine.py | C:\Users\ji...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 11 | `hw_profile.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\hw_profile.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\hw_profile.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\hw_profile.py | C:\Users\jichu\Down...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 12 | `main.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\main.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\main.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\main.py | C:\Users\jichu\Downloads\주식\sto...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 13 | `pyproject.toml` | `Generated normalized target` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\pyproject.toml | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\pyproject.toml | C:\Users\jichu\Do...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 14 | `recommendation_engine.py` | `C:\Users\jichu\Downloads\주식\workspaces\stock_rtx4060\recommendation_engine.py` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\recommendation_engine.py | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\recommendation_engine.py...` | Validated active package was preferred over raw patch/bundle/legacy variants. |
| 15 | `requirements.txt` | `Generated normalized target` | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2\requirements.txt | C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2\requirements.txt | C:\Users\jich...` | Validated active package was preferred over raw patch/bundle/legacy variants. |

## 7. Files Merged

| No | Source Files | Target File | Merge Reason |
|---:|---|---|---|
| 1 | `workspaces/stock_rtx4060/*`, root wrappers/docs/tests | `stock_rtx4060_unified` | Active package plus normalized wrappers/docs/tests were combined into one executable folder. |

## 8. Review Needed

| No | Path | Reason | Recommended Action |
|---:|---|---|---|
| 1 | `review_needed\docs\stock_rtx4060_algo_v2_ALGORITHM_PATCH_REPORT_2026.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 2 | `review_needed\docs\stock_rtx4060_algo_v2_DOC_REVIEW_AND_INSERTION.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 3 | `review_needed\docs\stock_rtx4060_algo_v2_README.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 4 | `review_needed\docs\stock_rtx4060_algo_v2_VALIDATION_LOG_ALGO_V2.txt` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 5 | `review_needed\docs\docs_CROSS_CHECK_2026.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 6 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_161939.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 7 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_161939.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 8 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_161955.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 9 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_161955.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 10 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_162042.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 11 | `review_needed\evidence\algo_v2_recommendation_reports\recommendations_algo_v2_20260502_162042.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 12 | `review_needed\evidence\algo_v2_benchmarks\benchmark_algo_v2_20260502_161729.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 13 | `review_needed\evidence\algo_v2_benchmarks\benchmark_algo_v2_20260502_161729.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 14 | `review_needed\evidence\algo_v2_benchmarks\benchmark_algo_v2_20260502_161807.json` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 15 | `review_needed\evidence\algo_v2_benchmarks\benchmark_algo_v2_20260502_161807.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 16 | `review_needed\tests\tests_test_algorithm_v2.py` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 17 | `review_needed\docs\stock_rtx4060_recommendation_patch_RECOMMENDATION_ENGINE.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 18 | `review_needed\docs\stock_rtx4060_recommendation_patch_VALIDATION_LOG_RECOMMENDATION_PATCH.txt` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 19 | `review_needed\docs\stock_rtx4060_patched_BENCHMARK_AND_CROSSCHECK.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |
| 20 | `review_needed\docs\stock_rtx4060_patched_PATCH_REPORT_2026.md` | Useful patch/evidence file, but not required for executable path. Isolated for manual review. | Review manually before promoting to docs/runtime path. |

## 9. Validation Results

Validation pending. See `reports/validation_results.md` after Phase 8.

## 10. Cross Review Results

| Round | Scope | Result | Patch Applied |
|---:|---|---|---|
| 1 | File consistency | Recorded | Selected active package and excluded duplicates/cache/generated output. |
| 2 | Execution consistency | Pending | Pending validation. |
| 3 | Documentation consistency | Pending | Pending scan. |

## 11. Final Folder Tree

```text
stock_rtx4060_unified/
├── archive/
│   └── original_inputs/
│       └── README.md
├── docs/
│   ├── AGENTS.md
│   ├── LAYOUT.md
│   ├── PATCH_NOTES.md
│   ├── SETUP.md
│   ├── SPEC.md
│   ├── SYSTEM_ARCHITECTURE.md
│   └── UIUX.md
├── examples/
│   ├── demo_workspace/
│   │   ├── benchmarks/
│   │   │   ├── benchmark_report.md
│   │   │   └── benchmark_result.json
│   │   ├── data/
│   │   │   └── sample_ohlcv.csv
│   │   ├── journal/
│   │   │   └── journal.csv
│   │   └── reports/
│   │       ├── daily_brief_2026-05-02.md
│   │       ├── monthly_scorecard_2026-05-02.md
│   │       ├── risk_dashboard_2026-05-02.md
│   │       └── track_l_thesis_2026-05-02.md
│   └── sample_ohlcv.csv
├── reports/
│   ├── conflict_resolution.csv
│   ├── conflict_resolution.md
│   ├── cross_review_round_1.md
│   ├── cross_review_round_2.md
│   ├── cross_review_round_3.md
│   ├── deleted_or_excluded_candidates.csv
│   ├── source_inventory.csv
│   ├── source_inventory.md
│   ├── validation_results.csv
│   └── validation_results.md
├── review_needed/
│   ├── docs/
│   │   ├── docs_CROSS_CHECK_2026.md
│   │   ├── stock_rtx4060_algo_v2_ALGORITHM_PATCH_REPORT_2026.md
│   │   ├── stock_rtx4060_algo_v2_DOC_REVIEW_AND_INSERTION.md
│   │   ├── stock_rtx4060_algo_v2_README.md
│   │   ├── stock_rtx4060_algo_v2_VALIDATION_LOG_ALGO_V2.txt
│   │   ├── stock_rtx4060_patched_BENCHMARK_AND_CROSSCHECK.md
│   │   ├── stock_rtx4060_patched_PATCH_REPORT_2026.md
│   │   ├── stock_rtx4060_recommendation_patch_RECOMMENDATION_ENGINE.md
│   │   └── stock_rtx4060_recommendation_patch_VALIDATION_LOG_RECOMMENDATION_PATCH.txt
│   ├── evidence/
│   │   ├── algo_v2_benchmarks/
│   │   │   ├── benchmark_algo_v2_20260502_161729.json
│   │   │   ├── benchmark_algo_v2_20260502_161729.md
│   │   │   ├── benchmark_algo_v2_20260502_161807.json
│   │   │   └── benchmark_algo_v2_20260502_161807.md
│   │   └── algo_v2_recommendation_reports/
│   │       ├── recommendations_algo_v2_20260502_161939.json
│   │       ├── recommendations_algo_v2_20260502_161939.md
│   │       ├── recommendations_algo_v2_20260502_161955.json
│   │       ├── recommendations_algo_v2_20260502_161955.md
│   │       ├── recommendations_algo_v2_20260502_162042.json
│   │       └── recommendations_algo_v2_20260502_162042.md
│   └── tests/
│       └── tests_test_algorithm_v2.py
├── src/
│   └── stock_rtx4060/
│       ├── __init__.py
│       ├── backtester.py
│       ├── benchmark.py
│       ├── ensemble_model.py
│       ├── feature_engine.py
│       ├── hw_profile.py
│       ├── main.py
│       ├── recommendation_engine.py
│       ├── reports.py
│       └── risk_rules.py
├── tests/
│   └── test_core.py
├── tools/
│   ├── consolidate_unified.py
│   └── consolidation_manifest.json
├── workspaces/
│   └── README.md
├── CHANGELOG.md
├── main.py
├── pyproject.toml
├── README.md
├── requirements-dev.txt
├── requirements-gpu-wsl.txt
├── requirements.txt
├── run.ps1
└── stock_investment_os.py
```

## 12. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Default `python` may not include pytest | `pytest` command can be environment-dependent | Validate with Python 3.12 if default pytest is unavailable. |
| `review_needed/` contains non-runtime evidence | Manual review still needed before promotion | Kept outside runtime/test path. |
| Real broker/account settings are not defined | Not approval-ready for real-money operation | Keep report-only boundary. |

## 13. Next Recommended Commands

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
python --version
python -m compileall .
python main.py --help
pytest
powershell -ExecutionPolicy Bypass -File .\run.ps1
```
