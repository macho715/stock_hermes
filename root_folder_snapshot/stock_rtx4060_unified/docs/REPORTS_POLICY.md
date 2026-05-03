# Reports Policy

This repository keeps important audit reports under `reports/`, but ad-hoc runtime outputs should not make `git status` unreadable.

## Keep As Review Evidence

| Pattern | Meaning |
|---|---|
| `reports/consolidation_*` | Consolidation evidence. |
| `reports/cross_review_round_*.md` | Cross-review evidence. |
| `reports/validation_results.*` | Validation evidence. |
| `reports/delete_audit_*/` | Approved deletion audit evidence. |
| `reports/phase1_mcp_openbb_audit_implementation.md` | Phase 1 implementation evidence. |
| `reports/generated_reports_inventory_*.md` | Inventory of generated report files. |
| `reports/dashboard_browser_verification/dashboard_browser_verification.md` | Browser verification summary. |

## Treat As Runtime Output

| Pattern | Meaning |
|---|---|
| `reports/dashboard_bridge_smoke/` | Dashboard bridge smoke output. |
| `reports/ops_v1_*_smoke/` | Ops v1 smoke output. |
| `reports/recommendations_*_smoke/` | Recommendation smoke output. |
| `reports/recommendations_live_*/` | Live recommendation output. |
| `reports/recommendations_full_gpu_*/` | GPU/full run output. |
| `reports/pytest_tmp*/` | Test temporary output. |
| `reports/runtime_status.json` | Runtime probe output. |
| `reports/dashboard_browser_verification/*.png` | Browser screenshot artifact. |
| `reports/dashboard_browser_verification/snapshot_fixture.js` | Browser smoke fixture generated from a snapshot. |
| `reports/generated_reports_inventory_*.csv` | Machine-readable generated report inventory. |
| `test-results/` | Playwright runtime metadata. |

Runtime output is ignored by `.gitignore` where practical. Do not delete existing files without explicit approval.
