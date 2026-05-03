/goal

Goal:
Implement a file-based dashboard report bridge so `stock_pred_v5.jsx` can import report-only recommendation snapshots generated from `stock_rtx4060_unified`.

Scope:
`C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` plus the external dashboard file `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`.

Hard Constraints:
1. Do not delete files.
2. Do not add broker, account, order execution, margin, options, short-selling, or auto-trading behavior.
3. Do not add a mandatory local API server, MCP server, listening port, or background service.
4. Do not expose secrets, tokens, account identifiers, private URLs, or provider config secrets.
5. Preserve `screening_output_only` and manual review wording in backend dashboard data.
6. Do not require OpenBB for synthetic validation.

Required Workflow:
1. Read repository instructions and the dashboard bridge plan/spec first.
2. Add a snapshot exporter that converts existing recommendation JSON into `dashboard_snapshot.v1`.
3. Add a CLI path for snapshot export without changing existing `recommend` behavior.
4. Patch `stock_pred_v5.jsx` so backend report snapshots are imported through a file-based UI and shown separately from browser demo scores.
5. Keep a repo-owned synchronized dashboard copy under `dashboard/stock_pred_v5.jsx`.
6. Add tests for snapshot conversion and report-only safety checks.
7. Add a browser smoke harness for `dashboard_snapshot.v1` import evidence.
8. Update README, setup, architecture, layout, changelog, plan, spec, and reports-policy docs.
9. Run compile, CLI help, pytest, synthetic smoke, dashboard export, and browser smoke checks.

Verification:
- `python -m compileall main.py src tests`
- `python main.py --help`
- `pytest -q`
- `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/dashboard_bridge_smoke`
- `.\run.ps1 dashboard-export --recommendation-json <generated recommendations JSON> --output reports/dashboard_bridge_smoke/dashboard_snapshot.json`
- `node dashboard\verify_bridge_smoke.mjs`

Stop Conditions:
Stop and ask before continuing if:
1. A secret-bearing file must be printed or embedded.
2. A broker/account/trading action appears necessary.
3. A dependency install or external network call becomes required.
4. Python imports or CLI entrypoints break and cannot be repaired within the current scope.

Deliverables:
- `src/stock_rtx4060/dashboard_bridge.py`
- `tests/test_dashboard_bridge.py`
- patched `src/stock_rtx4060/main.py`
- patched root `main.py`
- patched `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`
- repo-owned `dashboard/stock_pred_v5.jsx`
- `dashboard/bridge_smoke.html`
- `dashboard/verify_bridge_smoke.mjs`
- `docs/REPORTS_POLICY.md`
- updated documentation files
- generated `reports/dashboard_bridge_smoke/dashboard_snapshot.json`
- generated `reports/dashboard_browser_verification/dashboard_browser_verification.md`
