# CLAUDE.md

@AGENTS.md

## Project Identity

- Repo: `macho715/stock_1901`
- Main package: `src/stock_rtx4060/`
- Purpose: profit-engine research — signal strengthening, asset rotation, alpha validation, paper-trading review.
- Safety posture: research and paper validation only. Higher-risk workflows require explicit user approval.

## Commands

Use the smallest relevant check first.

```bash
# Syntax check
python -m compileall src/stock_rtx4060 flows tests

# Backend test gate (75% coverage required)
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 --tb=short -q

# CLI smoke tests
PYTHONPATH=.:src python main.py recommend --help
PYTHONPATH=.:src python main.py backtest --help
PYTHONPATH=.:src python main.py paper --help

# Type check (non-blocking)
mypy src/stock_rtx4060/observability || true
```

## C_fast / invest_algos Checks

Run when touching `invest_algos/`, C_fast validation, cost-stress logic, or regime rotation.

```bash
cd invest_algos
python examples/run_cfast_validation.py
pytest -q tests/test_cfast_validation.py \
         tests/test_latest_weights_schema.py \
         tests/test_timeseries_input_validation.py
```

Validation output must show all four of these controls or the run is invalid:

- `execution_mode=PAPER_TRADING_DRY_RUN_ONLY`
- `live_trading_allowed=false`
- `broker_execution_allowed=false`
- `promotion_status=BLOCKED_BY_X5_COST_FRAGILITY`

**`--candidate` 플래그 사용** (2026-05-31 추가):

```bash
cd invest_algos
# vol_cap_relaxed — 현재 CONDITIONAL_PASS 달성 candidate
python examples/run_cfast_validation.py --candidate vol_cap_relaxed

# 사용 가능한 candidate 목록
# baseline_default | vol_cap_relaxed | accepted_v2_target10_paper | defensive_v2 | cost_conservative
```

**C_fast 현재 상태** (2026-05-31):
- `vol_cap_relaxed`: `CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE` — x2=13.06% ✅
- `promotion_status`: `READY_FOR_PAPER_TRADING_REVIEW`
- `forward_month_gate`: pass=True (+2.53%)

**대시보드 C_FAST 뱃지** (2026-05-31 추가):
- `GET /api/cfast-validation` — validation_summary.json 요약 (api_server.py)
- StockPredV5.jsx footer에 C_FAST 상태 자동 표시

## Dashboard

```bash
# Backend
python api_server.py --port 5151

# Frontend — classic
cd root_folder_snapshot/stock-pred-v5 && npx vite --port 5173

# Frontend — executive
cd root_folder_snapshot/stock-pred-v5 && VITE_DASHBOARD_LAYOUT=executive npx vite --port 5173
```

Missing data must render as empty or fallback — never as fabricated values.

## Non-Negotiable Invariants

These are project-specific constraints that cannot be derived from the code alone.

- `screening_output_only=True` must remain on every recommendation output.
- `dashboard_snapshot.v1` is append-only; never remove or rename existing fields.
- Broker/live execution is manual-gated and disabled for all paper flows.
- LLM advisor output may **downgrade** a rating; it must never **upgrade** RED/AMBER to GREEN.
- `cv.split(...)` paths that require PurgedKFold groups must pass `groups=`.
- PIT/as-of behavior must fail fast on a lake miss when `as_of is not None`; no silent live fallback.
- Cost-fragile strategy promotion is blocked until x5 cost-stress evidence passes.

## Profit-Engine Patch Rule

Every strategy, signal, allocation, or C_fast change must report evidence in this order:

1. Net total return after costs
2. Benchmark-relative alpha vs `SPY_100`, `EQUAL_8ETF`, `CASH_100`
3. Max drawdown and downside behavior
4. Turnover and cost drag
5. Cash weight / asset rotation behavior
6. Promotion blockers and execution controls

A patch that only changes labels or dashboard wording without improving measurable evidence is **not** successful.

## Git Safety

- Always run `git branch --show-current` before editing.
- Do not push to `main` directly.
- Do not run `git push`, `git reset --hard`, `git clean`, force-push, or delete branches without explicit user request.

## Where to Add Things

| Need                          | Location                                                           |
|:------------------------------|:-------------------------------------------------------------------|
| New CLI subcommand            | `src/stock_rtx4060/main.py` + focused tests                        |
| New factor                    | `src/stock_rtx4060/factors/`                                       |
| New RD-Agent factor workflow  | `src/stock_rtx4060/factors/rd_agent/`                              |
| New ML model                  | `src/stock_rtx4060/ensemble_model.py` or `src/stock_rtx4060/ml/`  |
| New portfolio method          | `src/stock_rtx4060/portfolio/`                                     |
| New advisor                   | `src/stock_rtx4060/advisors/`                                      |
| New broker adapter            | `src/stock_rtx4060/broker/` — default to safe paper behavior       |
| New dashboard field           | `recommendation_engine.py`, `dashboard_bridge.py`, component tests |

## Completion Contract

Before reporting DONE:

1. List changed files and why each change matters.
2. List commands run with pass/fail status.
3. For profit-engine changes: include benchmark-relative and cost-stress evidence.
4. State remaining risks, assumptions, and unverified areas.
5. If blocked: stop and list at most 3 required inputs.
