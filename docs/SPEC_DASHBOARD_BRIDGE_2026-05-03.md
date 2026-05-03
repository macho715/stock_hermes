# SPEC: Dashboard Report Bridge

Status: Implemented with safe defaults from the 2026-05-03 pipeline request.

Source plan: `docs/plan_dashboard_bridge_2026-05-03.md`

Target repository: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

Dashboard candidate: `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`

Repo-owned dashboard copy: `dashboard/stock_pred_v5.jsx`

## Summary

The dashboard report bridge lets `stock_pred_v5.jsx` consume audited recommendation outputs from `stock_rtx4060_unified` through generated files, not through a live API server.

Current baseline verified from source:

| Area | Verified Baseline |
|---|---|
| Python entrypoint | Root `main.py`, package CLI in `src/stock_rtx4060/main.py` |
| Recommendation command | `recommend` |
| Existing output flag | `--output-dir` |
| Existing recommendation JSON writer | `RecommendationEngine.write_reports()` |
| Existing audit artifact | `audit_log.jsonl` under the configured output directory |
| Existing safety field | `screening_output_only=True` in `RecommendationResult` |
| Dashboard file | `stock_pred_v5.jsx` |
| Repo-owned dashboard copy | `dashboard/stock_pred_v5.jsx` |
| Dashboard current source | Browser `fetchSymbol()` using Yahoo proxy and synthetic fallback |
| Dashboard current export | `exportJSON()` and `exportMD()` browser downloads |
| Dashboard backend import | `BACKEND` button imports `dashboard_snapshot.v1` JSON files |

Selected approach:

| Decision | Value |
|---|---|
| Integration style | File-based report bridge |
| Server/API requirement | No new mandatory server |
| Broker/account access | Not allowed |
| OpenBB requirement | Must remain optional |
| Dashboard output label | Must show backend data as report-only screening output |
| CLI surface | `dashboard-export` |
| Dashboard load method | Browser file import |
| Browser verification | `dashboard/bridge_smoke.html` with `node dashboard\verify_bridge_smoke.mjs` |

## User Scenarios & Testing

### US-001 Generate a dashboard snapshot from recommendation output

Given the operator runs a recommendation workflow with `--output-dir reports/dashboard_bridge_smoke`
When the bridge runs against the generated recommendation JSON
Then it must create a dashboard snapshot JSON artifact
And the snapshot must include `generated_at_utc`, `source`, `mode`, `audit_log_path`, and `results`.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Convert a minimal recommendation JSON payload into snapshot JSON |
| Integration | Synthetic `recommend` run plus bridge snapshot generation |

### US-002 Preserve report-only safety boundaries

Given a recommendation result contains `screening_output_only=True`
When the bridge converts it into dashboard snapshot format
Then the snapshot must preserve `screening_output_only`
And it must not add broker order fields, account identifiers, or execution actions.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Unit | Assert output contains `screening_output_only` for every result |
| Unit | Assert no broker/order/account action fields are introduced |

### US-003 Keep browser demo results separate from backend report results

Given `stock_pred_v5.jsx` currently computes simulated scores in the browser
When backend snapshot mode is added
Then the dashboard must label browser-generated values separately from backend recommendation values
And it must not rename browser simulated model scores as backend model scores.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Static/source check | Dashboard source includes separate labels or mode names for browser and backend data |
| Browser smoke check | `node dashboard\verify_bridge_smoke.mjs` confirms backend snapshot mode loads and displays report-only evidence |

### US-004 Offline synthetic validation remains available

Given OpenBB is not installed or internet access is unavailable
When the operator runs a synthetic recommendation workflow and bridge export
Then the workflow must still generate recommendation JSON, audit JSONL, and dashboard snapshot JSON.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Integration | `.\run.ps1 recommend --synthetic ...` succeeds |
| Integration | Snapshot generation succeeds using the synthetic output |

### US-005 Dashboard can load or import a generated snapshot

Given a generated dashboard snapshot exists
When the operator uses the dashboard in backend report mode
Then the dashboard must display ticker, track, verdict, score, probability, expected value, risk plan, validation checks, and audit path evidence.

Test coverage:

| Test Type | Expected Coverage |
|---|---|
| Browser smoke check | Snapshot data appears in `dashboard/bridge_smoke.html` and verification evidence is written under `reports/dashboard_browser_verification/` |
| Manual/full React check | Optional follow-up if the JSX is moved into a runnable React/Vite package |

## Requirements

### Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FR-001 | The existing `recommend` command must remain available and keep writing Markdown, JSON, and audit JSONL outputs. | US-001, US-004 |
| FR-002 | The bridge must accept an existing recommendation JSON file generated by `RecommendationEngine.write_reports()`. | US-001 |
| FR-003 | The bridge must create a dashboard snapshot JSON file without requiring a local API server. | US-001, US-004 |
| FR-004 | The snapshot must include top-level `generated_at_utc`, `source`, `mode`, `audit_log_path`, `disclaimer`, and `results`. | US-001, US-002 |
| FR-005 | Each snapshot result must include ticker, track, verdict, score, probability, expected value, entry, stop, TP2, risk/reward, `screening_output_only`, validations, and reasons when present in source JSON. | US-001, US-005 |
| FR-006 | The bridge must preserve `screening_output_only` from source result objects. | US-002 |
| FR-007 | The bridge must not introduce broker execution, order placement, account, margin, options, short-selling, or credential fields. | US-002 |
| FR-008 | The dashboard must label backend snapshot data as report-only screening output. | US-003, US-005 |
| FR-009 | Browser-generated simulated model scores and backend recommendation scores must be visually or structurally distinguishable. | US-003 |
| FR-010 | The bridge must work with synthetic recommendation output and must not require OpenBB. | US-004 |
| FR-011 | Snapshot generation must fail with a clear message if required recommendation JSON fields are missing. | US-001 |
| FR-012 | The bridge must preserve or reference `audit_log_path` so the operator can inspect provider audit evidence. | US-001, US-005 |
| FR-013 | The implementation must not start a local MCP server, web server, or new listening port for this phase. | US-001, US-004 |
| FR-014 | Documentation must explain how to generate the recommendation output and then produce or load the dashboard snapshot. | US-004, US-005 |

### Non-Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| NFR-001 | Backward compatibility: existing CLI commands and tests must continue to pass. | US-001, US-004 |
| NFR-002 | Auditability: every backend dashboard view must be traceable to the generated recommendation JSON and `audit_log.jsonl`. | US-001, US-005 |
| NFR-003 | Security: no secrets, tokens, account identifiers, private URLs, or provider config secrets may be exposed in dashboard snapshot output. | US-002 |
| NFR-004 | Financial safety: the dashboard must not present report-only recommendations as order instructions. | US-002, US-005 |
| NFR-005 | Offline validation: synthetic workflow must remain usable without internet, OpenBB, or credentials. | US-004 |
| NFR-006 | Minimal runtime footprint: the file-based bridge must not add a mandatory server, port, or background service. | US-001 |
| NFR-007 | Source clarity: dashboard mode labels must make data provenance understandable to a non-developer operator. | US-003, US-005 |

## Assumptions & Dependencies

| ID | Item | Status |
|---|---|---|
| AD-001 | Active Python target is `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`. | Verified |
| AD-002 | Dashboard candidate is `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx`. | Verified |
| AD-003 | Existing source recommendation JSON contains `generated_at_utc`, `disclaimer`, `audit_log_path`, `errors`, and `results`. | Verified from `RecommendationEngine.write_reports()` |
| AD-004 | Existing result dictionaries come from `RecommendationResult.to_dict()`. | Verified |
| AD-005 | Existing CLI has `recommend --output-dir`. | Verified |
| AD-006 | Existing dashboard has browser `fetchSymbol()`, `cache`, `selected`, `exportJSON()`, and `exportMD()` flows. | Verified |
| AD-007 | File-based bridge is the selected path from `docs/plan_dashboard_bridge_2026-05-03.md`. | User selected file-based report bridge |
| AD-008 | Dashboard loading method is file import. | Resolved by current implementation |
| AD-009 | CLI surface is `dashboard-export`. | Resolved by current implementation |
| AD-010 | External `stock_pred_v5.jsx` remains patched in place and a repo-owned copy is kept at `dashboard/stock_pred_v5.jsx`. | Resolved by current implementation |
| AD-011 | Browser verification uses `dashboard/bridge_smoke.html` and `node dashboard\verify_bridge_smoke.mjs`. | Resolved by current implementation |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | CLI help still works. | `python main.py --help` exits `0` |
| SC-002 | Package compiles. | `python -m compileall main.py src tests` exits `0` |
| SC-003 | Regression tests pass. | `pytest -q` passes or an environment-only failure is documented |
| SC-004 | Synthetic recommendation smoke works. | `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --output-dir reports/dashboard_bridge_smoke` creates recommendation Markdown, recommendation JSON, and `audit_log.jsonl` |
| SC-005 | Snapshot artifact exists. | Approved bridge command creates `reports/dashboard_bridge_smoke/dashboard_snapshot.json` or approved equivalent |
| SC-006 | Snapshot is traceable. | Snapshot includes `audit_log_path` and source recommendation JSON path or metadata |
| SC-007 | Snapshot preserves safety boundary. | Every result includes `screening_output_only=true`; snapshot disclaimer states no broker execution and not financial advice |
| SC-008 | Snapshot contains expected result fields. | At least ticker, track, verdict, score, probability, expected value, entry, stop, TP2, R/R, validations are present when source data contains them |
| SC-009 | No new server is required. | No new mandatory service, port, MCP server, or web API command is added |
| SC-010 | Dashboard source distinguishes backend report data from browser demo data. | `dashboard/stock_pred_v5.jsx` has separate `BACKEND` import and tab labels |
| SC-011 | Documentation is updated. | README or docs explain generation and dashboard loading steps |
| SC-012 | Browser snapshot smoke is recorded. | `node dashboard\verify_bridge_smoke.mjs` writes `reports/dashboard_browser_verification/dashboard_browser_verification.md` |
| SC-013 | Generated report handling is documented. | `docs/REPORTS_POLICY.md` lists review evidence and runtime-output patterns |

## Non-Goals

- Do not add broker API integration.
- Do not add order placement, auto-buy, auto-sell, account access, margin, options, or short-selling.
- Do not turn dashboard signals into personalized financial advice.
- Do not require OpenBB for synthetic validation.
- Do not add a mandatory local API server in this phase.
- Do not add a local MCP server in this phase.
- Do not replace existing Markdown, JSON, or audit JSONL outputs.
- Do not rename browser simulated model outputs as Python backend model outputs.
- Do not delete the external `stock_pred_v5.jsx`; keep it synchronized with `dashboard/stock_pred_v5.jsx` when bridge UI changes.
- Do not move `stock_pred_v5.jsx` into a new React/Vite app package unless separately approved.

## Open Questions

| ID | Question | Impact | Required Resolution |
|---|---|---|---|
| OQ-001 | Should the dashboard load snapshots through a file import button, a fixed path under a served public folder, or both? | Affects dashboard UX and test path | Resolved: file import button |
| OQ-002 | Should the CLI expose a new `dashboard-export` subcommand or add a `--dashboard-snapshot` option to `recommend`? | Affects command contract and docs | Resolved: `dashboard-export` |
| OQ-003 | Should `stock_pred_v5.jsx` stay outside the unified repo or be copied into a `dashboard/` folder later? | Affects ownership and validation | Resolved for this phase: external file remains and repo-owned copy exists at `dashboard/stock_pred_v5.jsx` |
| OQ-004 | Should backend report mode display only Python results, or also keep browser charts beside backend evidence? | Affects UI design and user interpretation | Resolved for this phase: separate `BACKEND` tab beside existing browser charts |

## Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-03 | File-based report bridge is the selected integration direction. | User request |
| 2026-05-03 | Existing plan is `docs/plan_dashboard_bridge_2026-05-03.md`. | Local file inspection |
| 2026-05-03 | Existing recommendation JSON and audit JSONL are generated by `RecommendationEngine.write_reports()`. | Source inspection |
| 2026-05-03 | Existing dashboard currently fetches browser data via `fetchSymbol()` and exports browser JSON/Markdown through `exportJSON()` and `exportMD()`. | Source inspection |
| 2026-05-03 | Safe defaults selected for implementation: file import, `dashboard-export`, external JSX patched in place, separate `BACKEND` tab. | Current pipeline request |
| 2026-05-03 | Phase 1 risk mitigation added a repo-owned dashboard copy, browser smoke harness, reports policy, and browser verification evidence. | Current implementation |

## Reviewer Checklist

| Check | Status |
|---|---|
| Mandatory sections present | Yes |
| Functional requirements have stable IDs | Yes |
| Non-functional requirements have stable IDs | Yes |
| Success criteria are measurable | Yes |
| User scenarios use Given/When/Then | Yes |
| Safety boundary is explicit | Yes |
| Critical ambiguity is hidden | No; implementation choices are listed in Open Questions and Clarifications Log |
| Implementation code included | No; this file remains a requirements contract |

## Approval Readiness

Status: Implementation-ready for the current file-based bridge scope.

Smallest approval packet:

| Decision | Required Choice |
|---|---|
| Dashboard load method | File import |
| CLI surface | New `dashboard-export` command |
| Dashboard file ownership | Keep external JSX path and repo-owned `dashboard/stock_pred_v5.jsx` copy synchronized |
