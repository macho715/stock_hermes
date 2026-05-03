# PATCH_NOTES

## Patched scope

- Patched all original ZIP scripts into a package-first structure: `stock_rtx4060/`.
- Preserved top-level compatibility wrappers for the original script names.
- Removed `.pyc` artifacts from the deliverable ZIP.
- Added `stock_investment_os.py` wrapper for the earlier single-script CLI name.

## Validation performed in sandbox

```bash
python3 main.py self-test
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 -m compileall -q stock_rtx4060 main.py stock_investment_os.py
python3 main.py benchmark --rows 800 --repeats 2 --output-dir reports
python3 main.py demo --workspace demo_workspace
```

## Sandbox benchmark

| Step | Backend | Rows | Best seconds |
|---|---:|---:|---:|
| feature_engine.build_all | pandas/numpy | 591 | 1.190640 |
| walk_forward_train | numpy-logistic | 591 | 0.204867 |
| backtester.run | python/pandas | 591 | 0.020520 |

GPU benchmark is intentionally deferred to the user RTX 4060 machine. Run:

```powershell
python main.py env --tensorflow --xgboost --output reports/runtime_status.json
python main.py benchmark --rows 5000 --repeats 3 --include-gpu --include-lstm --output-dir reports
```
