# CLAUDE.md

<!-- ⚠️ ROOT-PINNED DOCUMENT — DO NOT MOVE
This file must remain in: C:\Users\jichu\Downloads\주식\
Moving this file to any subdirectory is PROHIBITED.
Managed by: Document Architecture Policy v1.0
Last verified: 2026-05-03
-->

@AGENTS.md

# CLAUDE.md

## Claude Code Scope
- Claude Code should use `AGENTS.md` as the shared repository guidance and apply this file only for Claude-specific behavior.
- Keep context concise. Do not restate long source documents unless the user asks for a report.
- Start with a brief plan for multi-file edits, then implement with small, reviewable diffs.

## Priority Behaviors
- Primary product goal: improve the stock-candidate recommendation scanner and its auditable reports.
- Preserve the boundary: recommendation reports are screening outputs for manual review, not broker execution or guaranteed investment advice.
- When the user asks for “recommend stocks,” implement ranking, validation, and reporting logic; do not add order routing or account-affecting actions.
- Use existing code paths in `recommendation_engine.py`, `main.py`, `feature_engine.py`, `ensemble_model.py`, and `backtester.py` before adding new abstractions.

## Claude Workflow
1. Inspect relevant files before editing.
2. Make the smallest safe change.
3. Run the smallest relevant command first.
4. For recommendation changes, run `python main.py --test` and a synthetic recommendation smoke test.
5. For broader changes, run `pytest -q` and `python -m py_compile *.py`.
6. Report commands, results, touched files, residual risks, and any unverified GPU or live-data paths.

## Approval Gates
- Ask for explicit approval before adding dependencies, editing CI, deleting files, writing outside the repo, handling secrets, or touching broker/account integrations.
- Stop if a task requests live trading, margin/options execution, credential capture, or automatic buy/sell behavior.
- Do not configure hooks that execute shell commands automatically unless the user explicitly asks and reviews the exact hook command.

## Validation Expectations
- Never mark GPU acceleration as validated without `nvidia-smi` and device-specific logs.
- Never mark a recommendation Green from model probability alone; Risk Gate and validation checks must pass.
- If yfinance or external market data is unavailable, use `--synthetic` only for smoke tests and label outputs as synthetic/demo.
- If a test fails, explain the root cause and fix it rather than suppressing assertions.
- LLM Advisor (`advisor_run=True`) requires `ANTHROPIC_API_KEY`; `api_server.py` silently disables it when the key is absent — never assume the advisor ran unless the response contains `advisor_score`. Dashboard toggle (`advisorEnabled`) is `false` by default and appends `advisor_run=1&advisor_blend_weight=0.3` to `/api/recommend` only when explicitly enabled.

## Response Contract
- Use Korean for user-facing explanations unless asked otherwise.
- Keep generated code comments and file bodies in English unless the user explicitly requests Korean.
- End with a concise status: `PASS`, `AMBER`, or `ZERO`, plus the next concrete action.
