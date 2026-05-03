# MOVE_PLAN

## Safety Rules

- Delete nothing.
- Move only with `Move-Item`.
- Keep root runtime files in place:
  - `README.md`
  - `CHANGELOG.md`
  - `main.py`
  - `run.ps1`
  - `pyproject.toml`
  - `requirements.txt`
  - `requirements-gpu-wsl.txt`
  - `stock_investment_os.py`
  - root compatibility wrappers: `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `hw_profile.py`
- Move active package only after import references are patched.

## Planned Moves

| Source | Destination | Reason |
|---|---|---|
| `SETUP.md` | `docs/SETUP.md` | Setup documentation belongs under docs. |
| `AGENTS.md` | `docs/AGENTS.md` | Agent rules are documentation. |
| `Spec.md` | `docs/Spec.md` | Feature contract belongs under docs. |
| `plan.md` | `docs/plan.md` | Planning document belongs under docs. |
| `plan_rev.md` | `docs/plan_rev.md` | Revised plan belongs under docs. |
| `uiux.md` | `docs/uiux.md` | UX/output document belongs under docs. |
| `PATCH_NOTES.md` | `docs/PATCH_NOTES.md` | Patch notes belong under docs. |
| `SYSTEM_ARCHITECTURE.md` | `docs/SYSTEM_ARCHITECTURE.md` | Architecture document belongs under docs. |
| `LAYOUT.md` | `docs/LAYOUT.md` | Layout document belongs under docs. |
| `actual_execution_workspace/` | `workspaces/actual_execution_workspace/` | Generated runtime evidence workspace. |
| `actual_run_workspace/` | `workspaces/actual_run_workspace/` | Generated runtime workspace. |
| `run_wrapper_workspace/` | `workspaces/run_wrapper_workspace/` | Generated wrapper workspace. |
| `demo_workspace/` | `workspaces/demo_workspace/` | Generated demo workspace. |
| `stock_rtx4060/` | `workspaces/stock_rtx4060/` | Active package moved under workspace grouping after import patch. |
| `stock_rtx4060_patched/` | `workspaces/stock_rtx4060_patched/` | Older patched/reference copy. |
| `주식.zip` | `archive/original_inputs/주식.zip` | Original input archive. |

## Import Patch Plan

| File | Current reference | New reference |
|---|---|---|
| `main.py` | `stock_rtx4060.main` | `workspaces.stock_rtx4060.main` |
| `feature_engine.py` | `stock_rtx4060.feature_engine` | `workspaces.stock_rtx4060.feature_engine` |
| `ensemble_model.py` | `stock_rtx4060.ensemble_model` | `workspaces.stock_rtx4060.ensemble_model` |
| `backtester.py` | `stock_rtx4060.backtester` | `workspaces.stock_rtx4060.backtester` |
| `hw_profile.py` | `stock_rtx4060.hw_profile` | `workspaces.stock_rtx4060.hw_profile` |
| `tests/test_core.py` | `stock_rtx4060.*` | `workspaces.stock_rtx4060.*` |

## Validation Plan

| Check | Command |
|---|---|
| Compile all Python files | `python -m compileall .` |
| CLI help | `python main.py --help` |
| Tests on dependency-ready Python | `C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q` |
| Documentation consistency | `rg` checks across `README.md`, `docs/LAYOUT.md`, `docs/SYSTEM_ARCHITECTURE.md`, `CHANGELOG.md`, `docs/SETUP.md` |

## Known Risks

- `python -m pytest -q` can fail if the PATH Python lacks pytest.
- Moving `stock_rtx4060/` changes import path from `stock_rtx4060` to `workspaces.stock_rtx4060` for this root layout.
- Nested archive folders may still contain old import examples; those are treated as archive/reference material.
