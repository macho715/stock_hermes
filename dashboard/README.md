# Dashboard Assets

This folder owns the repository-tracked dashboard copy for the file-based report bridge.

| File | Purpose |
|---|---|
| `stock_pred_v5.jsx` | Repo-owned copy of `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`. |
| `bridge_smoke.html` | Minimal browser harness for validating `dashboard_snapshot.v1` file import. |
| `verify_bridge_smoke.mjs` | Playwright smoke script for the harness. |
| `bridge_smoke.spec.mjs` | Metadata placeholder for the smoke command; the supported verification command is `node dashboard\verify_bridge_smoke.mjs`. |
| `playwright.config.mjs` | Optional local Playwright config kept with the harness. |

The external `stock_pred_v5.jsx` file remains in place. Do not delete it.

## Verification

```powershell
node dashboard\verify_bridge_smoke.mjs
```

Observed evidence is written to:

- `reports/dashboard_browser_verification/dashboard_browser_verification.md`
- `reports/dashboard_browser_verification/backend_snapshot_smoke.png`

The harness checks that a generated backend snapshot loads with schema `dashboard_snapshot.v1`, mode `report_only`, visible ticker rows, and audit path evidence.
