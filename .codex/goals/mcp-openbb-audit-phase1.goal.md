# Codex Goal Workflow: MCP + OpenBB + Audit Log Phase 1

Status: Prepared and executed once through `codex exec --enable goals`

Runtime note: current local `codex --version` was updated and verified as `codex-cli 0.128.0`. The `codex-goal-workflow` skill lists `0.128.0` as the minimum version for reliable `/goal` support. In this session the goal was executed non-interactively with `codex exec --enable goals` because this API session cannot paste into a live TUI.

## Goal Prompt

```text
/goal

Goal:
Make the MCP + OpenBB + audit log Phase 1 plan and SPEC approval-ready, then stop before implementation until approval is explicit.

Scope:
- Repository: C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
- Source plan: docs/plan.md
- Source spec: docs/SPEC.md
- Related docs allowed for consistency patches: README.md, CHANGELOG.md, docs/SETUP.md, docs/SYSTEM_ARCHITECTURE.md, docs/LAYOUT.md, docs/AGENTS.md
- Exclusions: do not modify runtime source code under src/, tests/, run.ps1, main.py, requirements files, pyproject.toml, generated reports, .venv, or git metadata during this approval-readiness goal.

Hard Constraints:
1. Do not delete files.
2. Do not modify runtime code.
3. Do not install packages or access external network without explicit approval.
4. Do not commit, push, deploy, or alter production data.
5. Preserve the report-only boundary: no broker API, no order execution, no auto-buy, no margin/options, no personalized investment advice.
6. Do not print secrets, tokens, credentials, account IDs, private URLs, or .env values.
7. Treat OpenBB as optional until the dependency decision is approved.
8. Treat MCP as read/report-only until the implementation mode is approved.
9. Stop before any implementation patch if approval remains unclear.

Required Workflow:
1. Read applicable AGENTS.md files first, including docs/AGENTS.md if present.
2. Read docs/plan.md and docs/SPEC.md.
3. Build a focused inventory of existing docs and CLI evidence relevant to MCP, OpenBB, audit logs, recommend, ops-v1, synthetic data, yfinance, and broker safety.
4. Resolve or explicitly preserve open questions from docs/SPEC.md:
   - OQ-001 OpenBB required vs optional dependency.
   - OQ-003 actual MCP server vs documented safe adapter contract.
   - OQ-004 allowed OpenBB data source endpoints.
   - OQ-005 provider selection interface.
5. Patch docs/plan.md and docs/SPEC.md only when the change is traceable to existing files or explicit user approval.
6. If approved choices are available, update related documentation for consistency.
7. Do not implement src/ code in this goal.
8. Run documentation verification and safe smoke checks that do not require new dependencies.
9. Produce an approval-readiness report.

Verification:
- docs/plan.md exists.
- docs/SPEC.md exists.
- docs/SPEC.md contains Summary, User Scenarios & Testing, Requirements, Assumptions & Dependencies, and Success Criteria.
- docs/SPEC.md contains FR, NFR, and SC identifiers.
- docs/SPEC.md has no unresolved critical NEEDS CLARIFICATION markers before marking approval-ready.
- README.md and docs/SYSTEM_ARCHITECTURE.md do not claim implemented MCP/OpenBB/audit runtime unless code actually exists.
- python main.py --help exits 0.
- python -m compileall main.py src tests exits 0.
- .\.venv\Scripts\python.exe -m pytest -q passes or failure is documented.
- .\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_goal_smoke runs or failure is documented.
- .\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/ops_v1_goal_smoke runs or failure is documented.

Stop Conditions:
Stop and ask before continuing if:
1. OpenBB dependency mode is still unclear.
2. MCP implementation mode is still unclear.
3. Allowed OpenBB data source endpoints are still unclear.
4. Provider selection interface is still unclear.
5. Any runtime source code change appears necessary.
6. Package installation or external network access appears necessary.
7. Secrets, credentials, account IDs, private URLs, or .env values may be exposed.
8. Verification cannot be run and approval-ready status cannot be proven.

Deliverables:
- Updated docs/plan.md if approval choices are provided.
- Updated docs/SPEC.md with no critical unresolved ambiguity if approval choices are provided.
- reports/goal_mcp_openbb_audit_phase1_readiness.md
- Final response with status, changed files, verification results, remaining risks, and one next action.
```

## Fallback Loop If Interactive `/goal` Is Unavailable

Use this manual loop if interactive `/goal` is unavailable:

1. Resolve the four critical questions in `docs/SPEC.md`.
2. Patch only `docs/plan.md` and `docs/SPEC.md`.
3. Cross-check README and architecture docs for false implementation claims.
4. Run the verification commands listed above.
5. Write `reports/goal_mcp_openbb_audit_phase1_readiness.md`.
6. Stop before implementation until the user explicitly approves the implementation phase.

## Current Critical Questions

| ID | Question | Current status |
|---|---|---|
| OQ-001 | Should OpenBB be required or optional? | Resolved: optional |
| OQ-003 | Should Phase 1 implement an MCP server or only an MCP-safe adapter contract? | Resolved: adapter contract only |
| OQ-004 | Which OpenBB data source endpoints are allowed first? | Resolved: `obb.equity.price.historical(symbol=..., provider="yfinance")` |
| OQ-005 | Should provider selection use `--data-provider`, config file, or both? | Resolved: both; CLI overrides config |

## Current Approval State

`docs/plan.md` and `docs/SPEC.md` now record the approved Phase 1 decisions. Implementation is still not complete and must be handled in a separate implementation run.
