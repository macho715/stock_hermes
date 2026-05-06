# SPEC — Phase A Point-in-time Data Gate + Provider v2 Dashboard

Feature ID: `phase-a-point-in-time-provider-v2-dashboard`

Created: 2026-05-03

Status: Approved for Phase A implementation on 2026-05-03.

Source Plan: `docs/plan_phase_a_point_in_time_provider_v2_dashboard_2026-05-03.md`

Target folder: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`

## Summary

Phase A adds a testable point-in-time OHLCV data validation contract and exposes provider health evidence in recommendation reports, audit JSONL, and the file-based dashboard snapshot.

Current verified baseline:

| Area | Current file |
|---|---|
| Root CLI wrapper | `main.py` |
| Package CLI | `src/stock_rtx4060/main.py` |
| Provider router | `src/stock_rtx4060/data_providers.py` |
| Audit logger | `src/stock_rtx4060/audit_log.py` |
| Recommendation engine | `src/stock_rtx4060/recommendation_engine.py` |
| Dashboard bridge | `src/stock_rtx4060/dashboard_bridge.py` |
| Existing provider tests | `tests/test_data_providers.py` |
| Existing dashboard bridge tests | `tests/test_dashboard_bridge.py` |

Current safety boundary:

- The system remains `screening_output_only`.
- The system does not place broker orders.
- The system does not add auto-buy, auto-sell, margin, options, or account-affecting behavior.
- OpenBB remains optional.
- Synthetic validation remains offline.

Approved implementation option:

- Option B: create `src/stock_rtx4060/provider_validation.py` and wire provider validation through providers, audit, recommendation JSON, and dashboard snapshot.

## User Scenarios & Testing

### US-001 — Operator sees point-in-time data quality in recommendation output

Priority: P1

Independent test: run synthetic recommendation smoke and inspect the generated JSON or Markdown for provider validation evidence.

Acceptance scenarios:

1. Given the operator runs `recommend` with synthetic data, When OHLCV data is loaded, Then the recommendation output records provider validation status without requiring internet or OpenBB.
2. Given an OHLCV frame has future-dated rows, When provider validation runs, Then the validation result is not PASS and the evidence identifies future rows.
3. Given an OHLCV frame has duplicate dates, When provider validation runs, Then the validation result is not silently treated as clean data.

Trace: FR-001, FR-002, FR-004, NFR-001, SC-004, SC-005.

### US-002 — Provider attempt audit logs include provider validation evidence

Priority: P1

Independent test: run provider unit tests and read `audit_log.jsonl` from a smoke output directory.

Acceptance scenarios:

1. Given a provider load succeeds, When the audit event is written, Then the event includes compact validation metadata such as status, row count, first date, last date, and freshness evidence.
2. Given provider config includes fake secret-like values, When audit metadata is written, Then secrets remain masked.
3. Given OpenBB is not installed, When synthetic provider tests run, Then OpenBB absence does not fail offline validation.

Trace: FR-003, FR-006, FR-007, NFR-002, NFR-004, SC-006, SC-009.

### US-003 — REC dashboard can show provider status from dashboard snapshot

Priority: P1

Independent test: export `dashboard_snapshot.json`, copy it to the dashboard public folder, and run the existing REC Playwright smoke.

Acceptance scenarios:

1. Given a recommendation JSON includes provider validation metadata, When `dashboard-export` builds `dashboard_snapshot.json`, Then the snapshot includes provider summary fields.
2. Given the dashboard imports the snapshot, When the REC tab renders, Then provider status can be shown without reading raw audit logs manually.
3. Given the snapshot is missing provider validation metadata, When `dashboard-export` runs, Then the bridge remains backward-compatible and does not break existing `dashboard_snapshot.v1` consumers.

Trace: FR-008, FR-009, FR-010, NFR-003, SC-007, SC-008.

### US-004 — Existing report-only workflows remain stable

Priority: P1

Independent test: run CLI help, compileall, pytest, synthetic recommendation smoke, and dashboard export smoke.

Acceptance scenarios:

1. Given Phase A changes are applied, When `python main.py --help` runs, Then existing CLI commands remain visible.
2. Given Phase A changes are applied, When `pytest -q` runs in the project `.venv`, Then existing provider, audit, core, MCP adapter, and dashboard bridge tests still pass.
3. Given Phase A changes are applied, When dashboard export runs, Then the snapshot preserves `screening_output_only` and introduces no broker execution surface.

Trace: FR-011, FR-012, NFR-005, NFR-006, SC-001, SC-002, SC-003, SC-010.

### Edge Cases

| ID | Case | Expected behavior |
|---|---|---|
| EC-001 | Missing required OHLCV columns | Validation status becomes FAIL with field list evidence. |
| EC-002 | Empty frame after normalization | Existing provider failure path remains RED or exception evidence; no false PASS. |
| EC-003 | Non-datetime index | Validation status becomes AMBER or FAIL with date-index evidence. |
| EC-004 | Future-dated rows | Validation status becomes AMBER or FAIL based on approved threshold. |
| EC-005 | Stale data | Validation status becomes AMBER by default until freshness threshold is approved. |
| EC-006 | Synthetic provider freshness | Synthetic path remains valid for offline smoke, but it must be labelled synthetic/offline evidence. |
| EC-007 | OpenBB package missing | Synthetic and yfinance paths continue to work. |
| EC-008 | Dashboard snapshot from older reports | Dashboard bridge accepts older payloads and omits provider summary instead of failing. |

## Requirements

### Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FR-001 | The system MUST add a point-in-time provider validation contract for normalized OHLCV frames. | US-001 |
| FR-002 | The validation contract MUST check row count, first date, last date, future rows, duplicate dates, required OHLCV columns, null critical values, and freshness evidence. | US-001 |
| FR-003 | The validation result MUST expose `status` with values `PASS`, `AMBER`, or `FAIL`. | US-001, US-002 |
| FR-004 | The validation result MUST be attached to provider metadata without removing existing `ProviderResult` fields. | US-001, US-002 |
| FR-005 | Provider routing MUST continue to support `auto`, `synthetic`, `yfinance`, `openbb`, `pykrx`, and `fdr` as currently represented in `data_providers.py`. | US-004 |
| FR-006 | Provider audit events MUST include validation metadata when available. | US-002 |
| FR-007 | Audit output MUST continue masking secrets, tokens, account IDs, authorization values, and private URLs. | US-002 |
| FR-008 | Recommendation JSON MUST expose provider validation evidence either per result or as a top-level provider summary. | US-003 |
| FR-009 | `dashboard-export` MUST include provider summary data in `dashboard_snapshot.v1` as additive fields. | US-003 |
| FR-010 | Dashboard snapshot export MUST remain backward-compatible with existing recommendation JSON that lacks provider validation fields. | US-003 |
| FR-011 | Existing CLI commands MUST remain available after Phase A changes. | US-004 |
| FR-012 | All recommendation and dashboard outputs MUST preserve `screening_output_only` and no-broker boundary labels. | US-004 |
| FR-013 | The system MUST NOT add broker API calls, order placement, auto-buy, auto-sell, margin, options, short selling, or account-affecting actions. | US-004 |
| FR-014 | The system MUST NOT require OpenBB for offline synthetic validation. | US-002, US-004 |
| FR-015 | The implementation uses `src/stock_rtx4060/provider_validation.py` for the Phase A provider validation contract. | Plan Option B |

Unresolved requirement:

- FR-016: The system MUST apply AMBER-first freshness behavior unless a provider frame has hard failures such as missing OHLCV columns, future rows, duplicate dates, or null critical values.

### Non-Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| NFR-001 | Testability: provider validation logic MUST be independently unit-testable without internet. | US-001 |
| NFR-002 | Security: audit and dashboard metadata MUST NOT expose provider credentials or private account data. | US-002 |
| NFR-003 | Compatibility: `dashboard_snapshot.v1` MUST remain additive and backward-compatible. | US-003 |
| NFR-004 | Auditability: a reviewer MUST be able to trace each recommendation run to provider used, source, row count, date range, and validation status when available. | US-002, US-003 |
| NFR-005 | Reliability: validation failures MUST become visible evidence and must not silently produce clean provider status. | US-001, US-004 |
| NFR-006 | Financial safety: provider PASS MUST NOT be treated as trade approval. | US-004 |

## Key Entities / Data

| Entity | Meaning | Key fields |
|---|---|---|
| `ProviderValidationResult` | Planned normalized validation result for one loaded OHLCV frame. | `status`, `row_count`, `first_date`, `last_date`, `future_rows`, `duplicate_dates`, `missing_ohlcv_columns`, `null_critical_values`, `freshness_days`, `evidence` |
| `ProviderResult` | Existing provider return object. | `frame`, `provider_requested`, `provider_used`, `source`, `endpoint`, `fallback_reason`, `metadata` |
| `AuditEvent` | Existing append-only JSONL event. | `event_type`, `status`, `command`, `ticker`, `period`, `provider_requested`, `provider_used`, `source`, `metadata` |
| `dashboard_snapshot.v1` | Existing dashboard import file. | `schema_version`, `mode`, `config`, `results`, additive `provider_summary` |
| `RecommendationResult` | Existing candidate screening result. | `ticker`, `track`, `verdict`, `screening_output_only`, `validations`, `reasons` |

## Interfaces & Contracts

### Provider validation function

Contract name: `validate_provider_frame`

Location: `src/stock_rtx4060/provider_validation.py`

Input:

| Name | Type | Required | Meaning |
|---|---|---|---|
| `frame` | `pandas.DataFrame` | Yes | Normalized OHLCV frame. |
| `provider_used` | `str` | Yes | Provider name used for the load. |
| `ticker` | `str` | Yes | Ticker being evaluated. |
| `period` | `str` | Yes | Requested period. |
| `as_of` | datetime-like | No | Run timestamp for freshness and future-row checks. |
| `min_rows` | `int` | No | Minimum acceptable row count. |
| `freshness_days_warn` | `int` | No | AMBER threshold; default implementation value is 5 days. |
| `freshness_days_fail` | `int` | No | FAIL threshold; default implementation value is 365 days. |

Output:

| Field | Type | Meaning |
|---|---|---|
| `status` | `PASS\|AMBER\|FAIL` | Overall point-in-time validation status. |
| `evidence` | `list[str]` | Human-readable validation evidence. |
| `metadata` | `dict` | Compact machine-readable metadata for audit/report/dashboard. |

### Dashboard snapshot additive section

Key: `provider_summary`

```json
{
  "provider_summary": {
    "status": "PASS",
    "providers_used": ["synthetic"],
    "event_count": 1,
    "row_count_min": 760,
    "last_date_max": "2026-05-03",
    "freshness_days_max": 0,
    "fallbacks": []
  }
}
```

Note: exact key names are draft contract names until implementation approval.

## Assumptions & Dependencies

### Assumptions

| ID | Assumption |
|---|---|
| AD-001 | The target implementation folder is `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`. |
| AD-002 | Option B is the approved implementation path. |
| AD-003 | Provider validation fields are additive and should not rename `dashboard_snapshot.v1`. |
| AD-004 | Synthetic data is an offline validation path, not a real market freshness claim. |
| AD-005 | Point-in-time freshness uses AMBER-first behavior in Phase A. |
| AD-006 | OpenBB remains optional through `requirements-openbb.txt`. |

### Dependencies

| ID | Dependency | Impact |
|---|---|---|
| DEP-001 | `pandas` DataFrame index and OHLCV columns | Provider validation checks depend on normalized frame shape. |
| DEP-002 | `src/stock_rtx4060/data_providers.py` | Provider validation must be called after provider normalization. |
| DEP-003 | `src/stock_rtx4060/audit_log.py` | Audit metadata must remain secret-safe. |
| DEP-004 | `src/stock_rtx4060/recommendation_engine.py` | Recommendation JSON must carry provider validation evidence. |
| DEP-005 | `src/stock_rtx4060/dashboard_bridge.py` | Dashboard snapshot must receive additive provider summary. |
| DEP-006 | `stock-pred-v5` REC tab | UI visibility is verified outside this package through dashboard public export and Playwright smoke. |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | CLI help remains available. | `python main.py --help` exits 0. |
| SC-002 | Package compiles. | `python -m compileall main.py src tests` exits 0. |
| SC-003 | Regression tests pass. | `pytest -q` passes in project `.venv`, or environment failure is documented as AMBER. |
| SC-004 | Provider validation unit tests pass. | `pytest tests/test_provider_validation.py -q` passes. |
| SC-005 | Synthetic recommendation smoke includes provider validation evidence. | `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/phase_a_provider_v2_smoke` creates Markdown, JSON, and audit JSONL. |
| SC-006 | Audit event includes provider validation metadata. | Generated or unit-test audit JSONL contains validation status and no fake secret values. |
| SC-007 | Dashboard snapshot includes provider summary. | `dashboard_snapshot.json` contains additive `provider_summary` or approved equivalent key. |
| SC-008 | Dashboard export remains backward-compatible. | Existing `tests/test_dashboard_bridge.py` and older payload test pass. |
| SC-009 | OpenBB remains optional. | Synthetic tests pass without requiring OpenBB import. |
| SC-010 | Report-only boundary remains intact. | Recommendation JSON and dashboard snapshot preserve `screening_output_only` and no broker execution fields are introduced. |

## Non-Goals

- Do not implement broker execution.
- Do not add auto-buy, auto-sell, broker order routing, margin, options, short selling, or account-affecting actions.
- Do not require OpenBB for offline validation.
- Do not add paid provider credentials or private URLs.
- Do not create a new MCP server runtime.
- Do not rename or break `dashboard_snapshot.v1`.
- Do not claim provider validation means a ticker is safe to buy.
- Do not implement TimesFM, Qlib, RD-Agent, or TensorFlow/LSTM production features in Phase A.

## Open Questions

| ID | Question | Why it matters |
|---|---|---|
| OQ-001 | Future provider-specific freshness thresholds may still be refined. | Phase A uses default AMBER-first behavior. |

## Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-03 | Phase A scope is Point-in-time data validation Gate + Provider v2 dashboard. | User request |
| 2026-05-03 | Plan recommends Option B. | `docs/plan_phase_a_point_in_time_provider_v2_dashboard_2026-05-03.md` |
| 2026-05-03 | User approved Option B and the four Spec approval items. | Current Codex session |
| 2026-05-03 | Existing system remains report-only and no-broker. | Current docs and source baseline |

## Reviewer Checklist

| Check | Status |
|---|---|
| Mandatory sections present | PASS |
| User scenarios use Given/When/Then | PASS |
| Functional requirement IDs present | PASS |
| Non-functional requirement IDs present | PASS |
| Success criteria are measurable | PASS |
| Critical ambiguity visible | PASS, remaining future threshold refinement is non-blocking |
| Approval-ready for implementation | PASS for Phase A |

## Traceability

| Scenario | Requirements | Success criteria |
|---|---|---|
| US-001 | FR-001, FR-002, FR-003, FR-004, FR-016, NFR-001, NFR-005 | SC-004, SC-005 |
| US-002 | FR-006, FR-007, FR-014, NFR-002, NFR-004 | SC-006, SC-009 |
| US-003 | FR-008, FR-009, FR-010, NFR-003 | SC-007, SC-008 |
| US-004 | FR-005, FR-011, FR-012, FR-013, NFR-006 | SC-001, SC-002, SC-003, SC-010 |

## Approval Readiness

Status: approved, implemented, committed, and uploaded to `origin/main` for Phase A.

Approved implementation decisions:

1. Option B is approved.
2. AMBER-first freshness behavior is approved for Phase A.
3. Additive dashboard key name is `provider_summary`.
4. Provider validation affects evidence only in Phase A, not ranking.

## Implementation Evidence

| Item | Evidence |
|---|---|
| Local commit | `cb98a21 Add Phase A provider validation dashboard evidence` |
| Full commit hash | `cb98a210e6a391342971fb5a1e1aeb2a301917e5` |
| Remote upload | `git push origin main` |
| Remote verification | `HEAD` and `origin/main` both resolved to `cb98a210e6a391342971fb5a1e1aeb2a301917e5`. |
| Smoke report evidence | `reports/phase_a_provider_v2_smoke/` |
| Review round 3 evidence | `reports/phase_a_provider_v2_review_round3/` |
| Remaining operational warning | `git status --short` emits permission warnings for `pytest-cache-files-kejv6w85/` and `pytest-cache-files-kr3txwkz/`; no changed files were listed after push. |
