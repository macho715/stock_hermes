# Stock RTX4060 Unified Consolidation Report

## 1. Summary
| Item | Result |
|---|---|
| Target | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Source files inventoried | 238 |
| Files kept from source roots | 11 |
| Excluded/merged/review-needed candidates | 227 |
| Review-needed source files | 4 |
| Original source deletion | 238 files deleted after approval A |
| Validation verdict | AMBER |
| Recommended operator path | `.\run.ps1 self-test` PASS |
| Delete audit path | `reports/delete_audit_20260502_211154` |

## 2. Source Folders Reviewed
| No | Path | Files | Role | Notes |
|---:|---|---:|---|---|
| 1 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2` | 38 | algo_v2 | Algorithm v2 source plus generated evidence |
| 2 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_algo_v2_bundle\stock_rtx4060_algo_v2` | 26 | bundle | Exact duplicate bundle candidates; parent folder removed after it became empty |
| 3 | `C:\Users\jichu\Downloads\주식\stock_rtx4060_recommendation_patch` | 31 | patch | Legacy recommendation patch source and docs |
| 4 | `C:\Users\jichu\Downloads\주식\workspaces` | 143 | workspace | Active integrated package plus runtime outputs |

## 3. Final Unified Folder
| Item | Value |
|---|---|
| Path | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Active package | `src/stock_rtx4060` |
| Entry point | `python main.py ...` and `.\run.ps1 ...` |
| Runtime output | `reports/` |

## 4. Files Kept
| No | Path | Reason |
|---:|---|---|
| 1 | `src/stock_rtx4060/backtester.py` | Selected source for unified folder |
| 2 | `src/stock_rtx4060/benchmark.py` | Selected source for unified folder |
| 3 | `src/stock_rtx4060/ensemble_model.py` | Selected source for unified folder |
| 4 | `src/stock_rtx4060/feature_engine.py` | Selected source for unified folder |
| 5 | `src/stock_rtx4060/hw_profile.py` | Selected source for unified folder |
| 6 | `src/stock_rtx4060/main.py` | Selected source for unified folder |
| 7 | `src/stock_rtx4060/recommendation_engine.py` | Selected source for unified folder |
| 8 | `src/stock_rtx4060/reports.py` | Selected source for unified folder |
| 9 | `src/stock_rtx4060/risk_rules.py` | Selected source for unified folder |
| 10 | `src/stock_rtx4060/__init__.py` | Selected source for unified folder |
| 11 | `examples/sample_ohlcv.csv` | Selected source for unified folder |

## 5. Files Excluded From Unified
See `reports/deleted_or_excluded_candidates.csv`.

The approved source roots were later deleted from the parent download folder. The pre-delete file list and SHA256 hashes are preserved in `reports/delete_audit_20260502_211154/deleted_files_before.csv`.

## 6. Conflicts Resolved
See `reports/conflict_resolution.md` and `reports/conflict_resolution.csv`.

## 7. Files Merged
| No | Source Files | Target File | Merge Reason |
|---:|---|---|---|
| 1 | Active package and patch docs | `README.md`, `CHANGELOG.md`, `docs/*.md` | Single executable folder needs one command/documentation surface. |

## 8. Review Needed
| No | Path | Reason | Recommended Action |
|---:|---|---|---|
| 1 | `review_needed/source_evidence/ALGORITHM_PATCH_REPORT_2026.md` | Source evidence contains legacy command syntax; quarantined outside active docs | Review manually before promoting into active docs. |
| 2 | `review_needed/source_evidence/VALIDATION_LOG_ALGO_V2.txt` | Source evidence contains legacy command syntax; quarantined outside active docs | Review manually before promoting into active docs. |
| 3 | `review_needed/docs/RECOMMENDATION_ENGINE_legacy_cli.md` | Useful legacy reference, but CLI form differs from active unified code | Review manually before promoting into active docs. |
| 4 | `review_needed/source_evidence/VALIDATION_LOG_RECOMMENDATION_PATCH.txt` | Source evidence contains legacy command syntax; quarantined outside active docs | Review manually before promoting into active docs. |

## 9. Validation Results
| Command | Result | Notes |
|---|---|---|
| `python --version` | PASS | Python 3.14.4 |
| `python -m compileall .` | PASS | Root wrapper, src package, and tests compiled. |
| `python main.py --help` | PASS | Help text printed without importing heavy dependencies. |
| `python main.py self-test` | AMBER | Default Python 3.14 lacks pandas; wrapper points to Python 3.12. |
| `python -m pytest -q` | AMBER | Default Python 3.14 lacks pytest. |
| `powershell -ExecutionPolicy Bypass -File .\run.ps1` | PASS | Wrapper selected Python 3.12 and self-test passed. |
| `C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q` | PASS | 5 tests passed; pytest-asyncio deprecation warning only. |
| `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\recommendation_smoke` | PASS | Generated recommendations_algo_v2 Markdown/JSON. |
| `Python 3.12 direct recommendation smoke` | PASS | Generated reports/recommendation_smoke_py312 recommendations_algo_v2 Markdown/JSON. |
| `.\run.ps1 self-test` | PASS | Current Codex session rerun passed; backend `xgb-cpu`, final capital `102190.84`. |

## 10. Cross Review Results
| Round | Scope | Result | Patch Applied |
|---:|---|---|---|
| 1 | File consistency | PASS | Quarantined legacy source evidence docs. |
| 2 | Execution consistency | AMBER | No code patch; default Python dependency issue documented. |
| 3 | Documentation consistency | PASS | Active docs aligned to unified structure and current operator self-test evidence. |

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
│   └── sample_ohlcv.csv
├── reports/
│   ├── recommendation_smoke/
│   │   ├── recommendations_algo_v2_20260502_205716.json
│   │   └── recommendations_algo_v2_20260502_205716.md
│   ├── recommendation_smoke_py312/
│   │   ├── recommendations_algo_v2_20260502_205716.json
│   │   └── recommendations_algo_v2_20260502_205716.md
│   ├── recommendations_smoke/
│   │   ├── recommendations_algo_v2_20260502_205714.json
│   │   └── recommendations_algo_v2_20260502_205714.md
│   ├── conflict_resolution.csv
│   ├── conflict_resolution.md
│   ├── consolidation_report.md
│   ├── consolidation_summary.json
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
│   │   └── RECOMMENDATION_ENGINE_legacy_cli.md
│   └── source_evidence/
│       ├── ALGORITHM_PATCH_REPORT_2026.md
│       ├── VALIDATION_LOG_ALGO_V2.txt
│       └── VALIDATION_LOG_RECOMMENDATION_PATCH.txt
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
│   └── README.md
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
| Default Python 3.14 lacks pandas and pytest | `python main.py self-test` and `python -m pytest -q` fail in that interpreter | Use `.\run.ps1` or install `requirements.txt` and `requirements-dev.txt` into the desired Python. |
| Legacy patch docs have old command syntax | Operator confusion if treated as current docs | Kept in `review_needed/source_evidence`. |
| Source folder is not a Git repo | No git history evidence | Reports are based on filesystem inventory and current execution checks. |
| Source roots deleted after approval A | Original source folders are no longer available for direct re-scan | Use `reports/delete_audit_20260502_211154` and `reports/source_inventory.csv` as evidence records. |

## 13. Next Recommended Commands
```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 self-test
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports\recommendations
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```
