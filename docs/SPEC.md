# SPEC

## Summary

Status: Phase 1 implemented in the current codebase; verification evidence recorded under `reports/phase1_mcp_openbb_audit_implementation.md`

Source plan: `docs/plan.md`

Scope: first upgrade slice for `stock_rtx4060_unified`: MCP-safe read/report adapter contract, optional OpenBB-backed market data provider path, provider selection via CLI and config, and structured audit logs for recommendation workflows.

Current baseline:

- Active package: `src/stock_rtx4060`
- Windows entrypoint: `run.ps1`
- Root wrapper: `main.py`
- Current recommendation commands: `recommend` and `ops-v1`
- Current data paths: deterministic `--synthetic` data and `yfinance`
- Current report outputs: Markdown, JSON, CSV artifacts under `reports/`
- Current safety boundary: `screening_output_only`, manual approval required, no broker order execution

Approved Phase 1 decisions:

| Decision | Approved value |
|---|---|
| OpenBB dependency mode | Optional |
| MCP mode | Adapter contract only; no local MCP server in Phase 1 |
| First OpenBB endpoint | `obb.equity.price.historical(symbol=..., provider="yfinance")` |
| Provider selection | Both CLI flag and config; CLI overrides config |
| Audit format | JSONL primary; CSV summary optional |

OpenBB source checked:

- `https://docs.openbb.co/platform/reference/equity/price/historical`
- `https://docs.openbb.co/platform/usage/quickstart_python`

## User Scenarios & Testing

### US-001 Offline synthetic workflow remains stable

Given the operator runs the CLI without internet access
When `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_phase1_smoke` is executed
Then the command must generate recommendation Markdown, recommendation JSON, and audit JSONL reports
And the generated output must remain `screening_output_only`.

Test coverage:

- Existing recommendation smoke behavior.
- New audit artifact presence.
- No OpenBB dependency required.

### US-002 Ops v1 workflow records audit evidence

Given the operator runs the report-only workflow
When `.\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/ops_v1_phase1_smoke` is executed
Then the command must generate recommendation reports, daily brief, approval journal template, ZERO log, summary JSON, and audit JSONL artifact
And the summary or generated paths must identify the audit artifact location.

Test coverage:

- Existing `ops-v1` workflow regression.
- Audit artifact path included in workflow result.
- `broker_order_execution=False` remains present.

### US-003 Provider fallback is explicit

Given OpenBB is unavailable or not configured
When the operator runs a supported command with `--data-provider auto`, `--data-provider yfinance`, or `--data-provider synthetic`
Then the command must not fail solely because OpenBB is missing
And the audit log must record which provider was requested, which provider succeeded, and why fallback occurred.

Test coverage:

- Provider selection unit tests.
- Fallback event serialization tests.
- Error masking tests.

### US-004 OpenBB equity historical data source is auditable

Given OpenBB is installed and the OpenBB provider path is selected
When the operator runs `recommend` or `ops-v1` with `--data-provider openbb`
Then the adapter must call the approved endpoint `obb.equity.price.historical(symbol=..., provider="yfinance")`
And the resulting provider output must normalize into the existing OHLCV frame contract
And the audit log must record provider name, endpoint, ticker, period or date range, timestamp, status, and failure reason when applicable.

Test coverage:

- Provider adapter unit tests with mocked OpenBB responses.
- OpenBB absence test.
- Optional integration smoke only if OpenBB is installed in the project `.venv`.

### US-005 MCP adapter boundary remains read/report-only

Given a future caller uses the Phase 1 MCP adapter contract
When an MCP-accessible workflow is mapped
Then the contract must expose only read/report workflow capabilities
And it must not expose broker, account, order placement, margin, options, destructive filesystem actions, or external write-back tools.

Test coverage:

- Documentation check that Phase 1 is adapter contract only.
- Boundary tests for allowed command names if an adapter module is created.
- No local MCP server process or port is introduced in Phase 1.

### US-006 Secrets are masked in logs

Given environment variables or provider configuration may contain sensitive values
When audit logs or error messages are written
Then API keys, tokens, account IDs, bearer values, and `.env` values must not appear in cleartext.

Test coverage:

- Unit tests for secret masking helper.
- Audit log sample with fake sensitive values.
- Search check over generated audit artifact for known fake secret strings.

## Requirements

### Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FR-001 | The existing `recommend`, `ops-v1`, `predict`, `report`, `env`, `benchmark`, `journal`, and `self-test` commands must remain available. | US-001, US-002 |
| FR-002 | The system must introduce a provider abstraction for OHLCV data loading without removing the current `yfinance` and `--synthetic` paths. | US-001, US-003, US-004 |
| FR-003 | The synthetic provider must remain deterministic and must not require internet, OpenBB, or external credentials. | US-001 |
| FR-004 | OpenBB must be an optional dependency; OpenBB absence must not break offline synthetic validation. | US-001, US-003, US-004 |
| FR-005 | The first OpenBB endpoint must be limited to `obb.equity.price.historical(symbol=..., provider="yfinance")`. | US-004 |
| FR-006 | Provider selection must support `--data-provider synthetic|yfinance|openbb|auto`. | US-003, US-004 |
| FR-007 | Provider config must be supported for defaults, and CLI flags must override config values. | US-003 |
| FR-008 | Every provider attempt must create an audit event with timestamp, command, ticker, period or date range, provider, endpoint when applicable, status, duration when available, and error category when applicable. | US-002, US-003, US-004 |
| FR-009 | `recommend` runs must write an audit JSONL artifact beside or under the configured `--output-dir`. | US-001, US-004 |
| FR-010 | `ops-v1` runs must return or record the audit artifact path together with recommendation, daily brief, approval journal, ZERO log, and summary paths. | US-002 |
| FR-011 | Provider failure must become explicit AMBER/RED evidence or a `RED_DATA_OR_MODEL_ERROR` result; it must not silently produce a successful recommendation without provenance. | US-003, US-004 |
| FR-012 | Audit output must mask secrets, tokens, keys, account IDs, private URLs, and private financial identifiers. | US-006 |
| FR-013 | Phase 1 MCP work must be an adapter contract only and must not start a local MCP server. | US-005 |
| FR-014 | Phase 1 MCP adapter contract must stay read/report-only and must not expose write-back, broker, account, or order execution tools. | US-005 |
| FR-015 | Existing report-only labels must remain in recommendation and Ops v1 outputs: `screening_output_only`, `manual_approval_required`, and `broker_order_execution=False`. | US-001, US-002, US-005 |
| FR-016 | Documentation must explain the data provider behavior, optional OpenBB dependency, audit artifact location, and MCP adapter safety boundary. | US-003, US-004, US-005 |

### Non-Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| NFR-001 | Backward compatibility: existing synthetic smoke tests and `tests/test_core.py` must continue to pass. | US-001, US-002 |
| NFR-002 | Security: generated logs must not expose secrets or account-affecting details. | US-006 |
| NFR-003 | Auditability: a reviewer must be able to trace each candidate to the provider path used for that run. | US-002, US-004 |
| NFR-004 | Failure transparency: provider failures must include human-readable reason codes. | US-003, US-004 |
| NFR-005 | No hidden runtime requirement: OpenBB absence must not break offline validation. | US-001, US-003 |
| NFR-006 | Financial safety: no part of this upgrade may create personalized investment advice, broker execution, auto-buy, margin/options, or account-affecting actions. | US-005 |
| NFR-007 | Extensibility: later OpenBB endpoints or MCP server runtime require a separate approval update. | US-004, US-005 |

## Assumptions & Dependencies

| ID | Item | Status |
|---|---|---|
| AD-001 | The active target folder is `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`. | Verified from plan and repo inspection |
| AD-002 | `docs/plan.md` is the source plan for this spec. | Verified |
| AD-003 | OpenBB starts as optional dependency. | Approved |
| AD-004 | Audit logs use JSONL as the primary event artifact. | Approved |
| AD-005 | CSV audit summary is optional and may be generated for human review. | Approved |
| AD-006 | Phase 1 defines an MCP-safe adapter contract only; no MCP server is added. | Approved |
| AD-007 | First OpenBB endpoint is equity historical OHLCV via `obb.equity.price.historical(..., provider="yfinance")`. | Approved |
| AD-008 | Provider selection uses both CLI and config, with CLI override precedence. | Approved |
| AD-009 | Tests should use the project `.venv` and existing Windows runner where possible. | Verified from current docs |

## Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-001 | Existing CLI help still works. | `python main.py --help` exits `0` |
| SC-002 | Package still compiles. | `python -m compileall main.py src tests` exits `0` |
| SC-003 | Regression tests pass. | `.\.venv\Scripts\python.exe -m pytest -q` passes, or environment failure is documented separately |
| SC-004 | Synthetic recommendation smoke still works. | `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_phase1_smoke` generates Markdown, JSON, and audit JSONL |
| SC-005 | Ops v1 smoke still works. | `.\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/ops_v1_phase1_smoke` generates current Ops v1 artifacts plus audit JSONL |
| SC-006 | Audit artifact exists for `recommend`. | Generated path exists and includes at least one provider event |
| SC-007 | Audit artifact exists for `ops-v1`. | Generated path exists and is referenced in summary or returned path output |
| SC-008 | OpenBB absence is safe. | Synthetic smoke passes without OpenBB installed |
| SC-009 | Secrets are masked. | Generated audit artifact contains no known fake secret value used by tests |
| SC-010 | Safety boundary remains intact. | Generated reports still show `screening_output_only`, manual approval requirement, and no broker execution |
| SC-011 | MCP server remains out of scope. | No new listening service, port, or MCP server command is added in Phase 1 |

## Non-Goals

- Do not add broker API integration.
- Do not add live order placement.
- Do not add auto-buy or auto-sell behavior.
- Do not enable margin, options, 0DTE, short-selling, or leveraged account actions.
- Do not start a local MCP server in Phase 1.
- Do not turn MCP into a trading gateway.
- Do not require OpenBB for offline synthetic validation.
- Do not add GraphRAG, vector database, or multi-agent orchestration in this phase.
- Do not add a web dashboard in this phase.
- Do not add paid OpenBB provider credentials in this phase.

## Open Questions

No critical open questions remain for Phase 1 implementation.

Resolved choices:

| ID | Question | Resolution |
|---|---|---|
| OQ-001 | Should OpenBB be a required dependency or optional dependency? | Optional |
| OQ-002 | Should audit logs be JSONL only, or JSONL plus CSV summary? | JSONL primary; CSV summary optional |
| OQ-003 | Should MCP be implemented as an actual local MCP server in Phase 1, or only as a documented safe boundary and future adapter contract? | Adapter contract only |
| OQ-004 | Which OpenBB data sources are allowed for the first pass? | `obb.equity.price.historical(symbol=..., provider="yfinance")` only |
| OQ-005 | What CLI flag should select provider behavior: `--data-provider`, config file, or both? | Both; CLI flag overrides config |

## Clarifications Log

| Date | Clarification | Source |
|---|---|---|
| 2026-05-02 | First upgrade scope is MCP + OpenBB + audit logs. | User request and `docs/plan.md` |
| 2026-05-02 | Recommended plan option is Option B. | `docs/plan.md` |
| 2026-05-02 | Existing report-only and no-broker boundary remains non-negotiable. | Current docs and source inspection |
| 2026-05-02 | Phase 1 decisions approved: OpenBB optional, MCP adapter contract only, OpenBB equity historical OHLCV endpoint, provider selection by CLI and config. | User approval |
| 2026-05-02 | OpenBB official docs confirm `obb.equity.price.historical` returns historical OHLCV data and supports `provider="yfinance"`. | OpenBB docs |
| 2026-05-07 | SQLite OHLCV cache (`data_cache.py`) extracted to standalone module; CI gate added; `paper-run` subcommand added. | Commit e20fc5e |
| 2026-05-07 | Test suite expanded to 340 tests, 80.79% coverage; `risk_rules.py`, `reports.py` at 100%; `data_providers.py` at 99%. | Commit 09c8187 + session work |
| 2026-05-08 | Test suite expanded to 509 tests, 89% total coverage; `ensemble_model.py` 83%, `kevpe_adapter.py` 91%, `main.py` 98%. New files: `test_ensemble_model_extra.py`, `test_kevpe_adapter.py`, `test_main_extra.py`. | Commit d7a3022 |

## Reviewer Checklist

| Check | Status |
|---|---|
| Mandatory sections present | PASS |
| Stable requirement IDs present | PASS |
| Given/When/Then scenarios present | PASS |
| Measurable success criteria present | PASS |
| Critical ambiguity visible or resolved | PASS |
| Approval-ready | PASS for Phase 1 implementation planning |

## Approval Readiness

This spec has been used for Phase 1 implementation.

Current implementation status:

| Item | Status |
|---|---|
| Provider abstraction | Implemented in `src/stock_rtx4060/data_providers.py`. |
| Audit JSONL | Implemented in `src/stock_rtx4060/audit_log.py`. |
| MCP adapter contract | Implemented in `src/stock_rtx4060/mcp_adapter.py`; no server is started. |
| CLI provider flags | Implemented for `recommend` and `ops-v1`. |
| Optional OpenBB dependency | Documented in `requirements-openbb.txt`; base install remains OpenBB-free. |
| Verification | `.venv` pytest passed with 340 tests (80.79% coverage); synthetic recommendation, Ops v1 smoke, OpenBB cache smoke, and dashboard bridge smoke generated audit logs or snapshot evidence. |
| OHLCV cache | Implemented in `src/stock_rtx4060/data_cache.py` (SQLite-backed); `_cache` singleton shared across providers; `USE_DATA_CACHE=0` env var disables it. |
| Dashboard report bridge | Implemented in `src/stock_rtx4060/dashboard_bridge.py` with `dashboard-export`; see `docs/SPEC_DASHBOARD_BRIDGE_2026-05-03.md`. |
| CI gate | `.github/workflows/ci.yml` runs `pytest --cov=stock_rtx4060` on push/PR; `fail_under=75` enforced in `pyproject.toml`. |
| paper-run subcommand | Implemented in `src/stock_rtx4060/main.py`; bridges `RecommendationEngine` to `PaperTradingEngine` (no broker orders). |
| Test suite | 340 tests across 15+ test files; `risk_rules.py` 100%, `reports.py` 100%, `data_providers.py` 99%, total 80.79%. |
