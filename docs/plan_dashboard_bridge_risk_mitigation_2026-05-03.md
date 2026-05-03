# Dashboard Bridge Risk Mitigation Plan

Status: Implemented after Phase 1 approval for Option B.

Planning skill: `mstack-plan`

Date: 2026-05-03

Target repository: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

External dashboard file: `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`

Source context:

- `docs/plan_dashboard_bridge_2026-05-03.md`
- `docs/SPEC_DASHBOARD_BRIDGE_2026-05-03.md`
- Current `git status --short --untracked-files=all`

## Phase 1: Business Review

### 1.1 Problem Definition

Current state: the backend bridge is implemented and Python checks pass, but dashboard UI behavior, JSX ownership, and generated report tracking remain unresolved.

Target state: the dashboard bridge has browser evidence, version-controlled dashboard source ownership, and a documented reports policy without deleting existing evidence.

Quantified impact:

| Risk | Current Evidence | Impact | Target State |
|---|---|---|---|
| Browser verification missing | `stock_pred_v5.jsx` was patched, but no React/browser harness was run | Import button and layout may fail at runtime | Browser smoke evidence with screenshot or Playwright report |
| JSX outside repo | `stock_pred_v5.jsx` lives outside `stock_rtx4060_unified`; repo `git status` cannot track it | Dashboard changes can be lost or omitted from commits | Versioned copy under repo, external file kept as working mirror |
| Untracked reports | Many `reports/` runtime outputs appear as untracked files | Git status is noisy and important new outputs are hard to identify | Clear keep/ignore policy plus generated report inventory |

### 1.2 Proposed Options

| Option | Description | Effort Days | Risk | Cost AED |
|---|---|---:|---|---:|
| A | Evidence-only mitigation. Keep JSX outside repo, run a one-off browser/manual check, and document reports noise. | 0.5 | Medium | 0 |
| B | Recommended. Copy dashboard JSX into a repo-owned `dashboard/` area, add a minimal browser verification harness, and add reports hygiene rules without deleting old outputs. | 1-2 | Low-Medium | 0 |
| C | Full dashboard packaging. Convert the JSX into a complete React/Vite app, add build scripts, Playwright, screenshots, report fixture management, and stricter generated-output cleanup. | 3-5 | Medium | 0 |

### 1.3 Recommendation And Rationale

Recommended option: Option B.

Reason 1: it solves the real ownership problem by making dashboard source visible to repo `git status`.

Reason 2: it gives browser-level evidence without forcing a full dashboard product migration.

Reason 3: it cleans report noise through policy and inventory, not deletion.

Rollback strategy: remove the repo-owned dashboard copy and harness, keep the external `stock_pred_v5.jsx`, and leave generated reports untouched.

### 1.4 Approval Request

- [x] Phase 1 approval: proceed with Option B risk mitigation.

Approval means the next implementation pass may:

| Area | Allowed Action |
|---|---|
| Browser verification | Create a minimal local dashboard verification harness and run browser smoke checks |
| JSX ownership | Copy `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx` into a repo-owned dashboard path without deleting the original |
| Reports hygiene | Add report inventory and `.gitignore` rules for generated runtime outputs |
| Evidence | Generate a browser verification report under `reports/dashboard_browser_verification/` |

Implementation evidence:

| Item | Result |
|---|---|
| Repo-owned dashboard copy | `dashboard/stock_pred_v5.jsx` |
| Browser harness | `dashboard/bridge_smoke.html` |
| Verification command | `node dashboard\verify_bridge_smoke.mjs` |
| Browser report | `reports/dashboard_browser_verification/dashboard_browser_verification.md` |
| Screenshot | `reports/dashboard_browser_verification/backend_snapshot_smoke.png` |
| Reports policy | `docs/REPORTS_POLICY.md` and `.gitignore` runtime-output patterns |

## Coordinator Input Packet

objective: mitigate the three remaining dashboard bridge risks without deleting files or changing the report-only investment boundary.

non-negotiables:

| Rule | Reason |
|---|---|
| Do not delete existing reports | Existing outputs may be audit evidence |
| Do not remove the external JSX file | It is the user-provided dashboard file |
| Do not add broker/order/account actions | Financial safety boundary |
| Do not require OpenBB or internet for validation | Synthetic validation must remain offline-capable |
| Do not hide untracked generated files | User needs clear repo state |

acceptance criteria:

| ID | Criterion |
|---|---|
| AC-001 | Browser verification produces evidence that the `BACKEND` import path renders or a clear blocker report |
| AC-002 | A repo-owned dashboard source file is visible in `git status` |
| AC-003 | Existing external `stock_pred_v5.jsx` still exists |
| AC-004 | Generated reports policy distinguishes committed docs from runtime outputs |
| AC-005 | No existing reports are deleted |
| AC-006 | `python -m compileall main.py src tests` and `pytest -q` still pass |

option set:

| Option | Use When |
|---|---|
| A | Need minimum confirmation only |
| B | Need a practical fix for all three risks |
| C | Need a production-grade web dashboard package |

required evidence:

| Evidence | Target |
|---|---|
| Browser check | `reports/dashboard_browser_verification/` |
| Repo-owned dashboard file | Proposed `dashboard/stock_pred_v5.jsx` or approved equivalent |
| Reports policy | README/docs plus `.gitignore` patch if approved |
| No deletion proof | Before/after report inventory |
| Regression | compileall and pytest output |

test expectations:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
python -m compileall main.py src tests
pytest -q
.\run.ps1 dashboard-export --help
```

Browser verification command:

```powershell
node dashboard\verify_bridge_smoke.mjs
```
