# CLAUDE.md — AI Assistant Guidance for stock_1901

<!-- This file is read by Claude Code and other AI agents at session start. -->
<!-- Append-only; do not delete existing sections. -->

## Project Identity

- **Repo**: `macho715/stock_1901` (Linux, `/home/user/stock_1901`)
- **Active branch**: `claude/upgrade-investment-system-2Mc7x`
- **Package**: `stock_rtx4060` under `src/stock_rtx4060/`
- **Python**: 3.12 (CI), 3.14.4 local

## Development Branch

All work goes to branch `claude/upgrade-investment-system-2Mc7x`. Never push directly to `main` without a PR and CI green.

```bash
git checkout claude/upgrade-investment-system-2Mc7x
git push -u origin claude/upgrade-investment-system-2Mc7x
```

## Project Architecture (P0–P8)

| Phase | Area | Key modules |
|---|---|---|
| P0 Foundation | observability, CI | `src/stock_rtx4060/observability/`, `.github/workflows/ci.yml` |
| P1 Data Lake | PIT-correct storage | `src/stock_rtx4060/data_lake/` (DuckDB+Parquet backend) |
| P2 Factors | Factor zoo + RD-Agent | `src/stock_rtx4060/factors/` |
| P3 ML Upgrade | LightGBM, Optuna HPO, MLflow | `src/stock_rtx4060/ml/` |
| P4 Portfolio | skfolio HRP/NCO/CVaR | `src/stock_rtx4060/portfolio/` |
| P5 Backtest | vectorbt, MC bootstrap, stat tests | `src/stock_rtx4060/backtest/` |
| P6 LLM Advisor | Anthropic claude-opus-4-7, LangGraph | `src/stock_rtx4060/advisors/` |
| P7 Orchestration | Prefect 3 flows, Slack/Discord alerts | `flows/` |
| P8 Live Brokers | Alpaca, IBKR, KIS adapters | `src/stock_rtx4060/broker/` |

## Key Invariants (Must Never Break)

1. **CLI compatibility**: `main.py {env,benchmark,report,recommend,paper,ops,backtest} --help` must exit 0.
2. **`dashboard_snapshot.v1` schema**: `build_dashboard_snapshot` always returns `schema_version="dashboard_snapshot.v1"`. Additive fields only.
3. **`audit_log.jsonl` format**: Existing event names/format preserved. New events go to new files (`advisor.jsonl`, `provenance.jsonl`).
4. **`screening_output_only=True`**: All recommendation outputs carry this flag. No broker order path can be triggered without explicit user action.
5. **PurgedKFold groups**: `cv.split(X, groups=_groups)` must always receive the `groups` array — never `cv.split(X)`.
6. **PIT as_of guard**: When `as_of is not None`, falling through to live providers is forbidden (raises `RuntimeError`).
7. **numpy bounds**: `numpy>=1.26,<3.0` — shap>=0.50 requires numpy>=2; never re-pin to `<2.0`.
8. **Test coverage**: `pytest --cov=stock_rtx4060 --cov-fail-under=75` must pass. **Current: 86.03%** (incl. `test_walk_forward_purged.py` ×3). Target ≥85% total.

## Critical Files

| File | Role |
|---|---|
| `src/stock_rtx4060/recommendation_engine.py` | Central hub: `as_of` propagation, `advisory_score` blend, MLflow model load |
| `src/stock_rtx4060/data_providers.py` | PIT lake write-through; `load_ohlcv_with_provider` signature preserved |
| `src/stock_rtx4060/ensemble_model.py` | PurgedKFold swap, LightGBM, MLflow tracking, SHAP |
| `src/stock_rtx4060/backtester.py` | Optimizer-based sizing, Deflated Sharpe / PSR / MC output |
| `src/stock_rtx4060/broker_bridge.py` | `BrokerAdapter` ABC extended to real adapters; `PaperBroker` default kept |
| `src/stock_rtx4060/ml/cv.py` | `PurgedKFold(n_splits, embargo_pct)` — post-test purge loop required |
| `src/stock_rtx4060/ml/hpo.py` | Optuna study; must pass `groups=` to `cv.split()` |
| `flows/research_weekly.py` | `_current_production_score()` reads real oos_brier from MLflow |
| `flows/daily_krx.py` | KRX daily flow; uses `timedelta(days=365)` not `.replace(year=)` |
| `flows/daily_us.py` | US daily flow; same time-delta pattern |

## CI

```bash
# Full test suite (matches CI)
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-report=term-missing --tb=short -rfE -v

# Type check (non-blocking)
mypy src/stock_rtx4060/observability || true
```

CI runs on push/PR. Artifacts: `pytest.log`, `coverage.xml`. Failures shown in GitHub Step Summary.

## Dependency Rules

- `numpy>=1.26,<3.0` — allows numpy 2.x (required by shap>=0.50)
- `shap>=0.50.0` — required for xgboost 3.x compatibility
- All new packages must also be added to `requirements.in`
- Heavy optional deps (skfolio, vectorbt, langgraph, etc.) must degrade gracefully when absent

## Anthropic SDK Usage (P6 LLM Advisor)

- Model: `claude-opus-4-7` (current production model)
- Enable prompt caching with 4 cache breakpoints on system prompt + factor schema
- Token budget: 50k in / 4k out per recommendation cycle
- All advisor calls logged to `audit_log/advisor.jsonl` with `{ts, ticker, agent, prompt_hash, score, tokens_in, tokens_out, cost_usd}`
- Advisory scores ∈ [-1,+1]; **never overrides GREEN/AMBER/RED gate**; LLM can only downgrade GREEN→AMBER

## Git Workflow

- Commit messages: descriptive, reference the phase (`feat(P3)`, `fix(P1)`, etc.)
- Always push with `-u origin <branch>`
- Retry push up to 4 times with exponential backoff (2s, 4s, 8s, 16s) on network failures
- Do NOT force-push main; do NOT skip hooks (`--no-verify`)

## Fitness and Compliance Checks

Run these before claiming any task complete:

```bash
# 1. Syntax check
python -m compileall src/stock_rtx4060 flows tests

# 2. Tests with coverage
PYTHONPATH=.:src pytest --cov=stock_rtx4060 --cov-fail-under=75 --tb=short -q

# 3. CLI invariants
PYTHONPATH=.:src python main.py recommend --help
PYTHONPATH=.:src python main.py backtest --help
PYTHONPATH=.:src python main.py paper --help

# 4. Dashboard snapshot schema
PYTHONPATH=.:src python -c "from stock_rtx4060.dashboard_bridge import build_dashboard_snapshot; print('OK')"

# 5. PIT guard check (data_providers)
PYTHONPATH=.:src python -c "from stock_rtx4060.data_providers import load_ohlcv_with_provider; print('OK')"

# 6. Dependency conflict check
pip check 2>&1 | grep -v "^No broken"
```

| Gate | Pass condition |
|---|---|
| `compileall` | Exit 0, no syntax errors |
| `pytest --cov-fail-under=75` | All tests pass, coverage ≥75% |
| CLI `--help` | Exit 0 for all subcommands |
| `dashboard_snapshot.v1` | `schema_version` field present |
| `numpy` version | ≥1.26 and <3.0 in requirements |
| `shap` version | ≥0.50.0 in requirements |
| `PurgedKFold` groups | `groups=` always passed in `cv.split()` |
| PIT `as_of` guard | `RuntimeError` raised on lake-miss with `as_of!=None` |
| Audit log integrity | No existing event names removed from `audit_log.jsonl` |
| `screening_output_only` | `True` on every `RecommendationResult` |

## Safety Boundaries

| Boundary | Rule |
|---|---|
| Broker execution | Only via explicit `--broker live-*` flag + user approval |
| Live orders on paper runs | Skip when `status.get("reused")` is True |
| API keys | Never committed, never guessed — user provides via env vars or `~/.config/` |
| `as_of` queries | Must fail-fast if lake miss; no silent look-ahead |
| LLM advisory | Score ∈ [-1,+1]; cannot upgrade RED/AMBER to GREEN |
| Kill switch | `~/.cache/stock_1901/KILLED` file blocks all live orders |

## Where to Add Things

| Need | Add here |
|---|---|
| New CLI subcommand | `src/stock_rtx4060/main.py` + test in `tests/test_main_extra.py` |
| New factor | `src/stock_rtx4060/factors/` + register in `factor_zoo.py` |
| New ML model | `src/stock_rtx4060/ensemble_model.py` `_make_*` pattern |
| New portfolio method | `src/stock_rtx4060/portfolio/optimizer.py` |
| New advisor | `src/stock_rtx4060/advisors/` implementing `Advisor` protocol |
| New broker | `src/stock_rtx4060/broker/` implementing `BrokerAdapter` ABC |
| New Prefect flow | `flows/` + cron schedule in deployment config |
| New RD-Agent factor | `src/stock_rtx4060/factors/rd_agent/` + `tests/test_rd_agent_*.py` |
| New dashboard field | `recommendation_engine.py` + `dashboard_bridge.py` + `tests/test_dashboard_bridge.py` |

## RD-Agent Integration (P2)

RD-Agent automates factor discovery via Docker subprocess.
Full docs: see `20260529_plan-doc-rdagent-factory.md`.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RDAGENT_ENABLED` | `false` | Set `true` to activate Docker-based factor mining |
| `RDAGENT_DOCKER_IMAGE` | `microsoft/rdagent:latest` | Docker image |
| `RDAGENT_BUDGET_USD` | `10.0` | Per-cycle LLM budget cap |
| `RDAGENT_CYCLES` | `2` | Number of discovery cycles |
| `RDAGENT_TIMEOUT_MIN` | `30` | Docker run timeout (max 60) |
| `RDAGENT_APPROVAL_REQUIRED` | `true` | `false` = auto-register after validation (dev only) |

### CLI Commands

| Command | Role |
|---|---|
| `python -m stock_rtx4060.main factor-mine [--cycles N] [--budget-usd FLOAT]` | Run RD-Agent factor mining |
| `python -m stock_rtx4060.main factor-list [--status all\|discovered\|staged\|registered]` | List discovered/pending factors |
| `python -m stock_rtx4060.main factor-approve [--factor-id ID] [--run-date YYYY-MM-DD]` | Approve and register staged factors |
| `python -m stock_rtx4060.main factor-status` | Show registered discovered factors |

### Modules

- `factors/rd_agent/runner.py` — entry point, delegates to docker_runner
- `factors/rd_agent/docker_runner.py` — Docker subprocess wrapper
- `factors/rd_agent/qlib_exporter.py` — DuckDB → Qlib CSV/bin (PIT guard)
- `factors/rd_agent/loader.py` — dynamic `.py` → Factor instance
- `factors/rd_agent/provenance.py` — `audit_log/rd_agent.jsonl` JSONL logging
- `factors/rd_agent/registry_hook.py` — validate → stage → approve → register
- `factors/rd_agent/validator.py` — IC/IR/correlation/half-life gates

## Known Issues & Workarounds

| Issue | Workaround |
|---|---|
| `logging.basicConfig(force=True)` in `_intercept_stdlib()` installs a global `InterceptHandler` | Tests calling `configure_logging()` or `_intercept_stdlib()` must `monkeypatch.setattr(logging, "basicConfig", lambda **kw: None)` |
| numpy read-only views from `.corr().values` in Python 3.14 | Always `.copy()` before `np.fill_diagonal()` — see `portfolio/optimizer.py` |
| `pd.Timestamp.utcnow()` deprecated in Pandas 4.x | Use `pd.Timestamp.now('UTC')` — patched in `data_providers.py`, `recommendation_engine.py` |

## Recent Fix Log

| Date | Commit | Fix |
|---|---|---|
| 2026-05-29 | `fd24364` | E2: PBO badge end-to-end fix — fold AUC proxy PBO, `evaluate_backtest_honesty` additive pbo field, `RecommendationCard.jsx PboBadge` |
| 2026-05-29 | `f5570dd` | Dashboard: LLM Advisor KRX 제한 제거 (3곳 — `advisorRequestEnabled`, onClick, useEffect) |
| 2026-05-29 | `9664ca5` | Dashboard: XGBoost secondary score (lightgbm 백엔드), LSTM/RNN null 행 숨김, cv_gap 기본값 5 |
| 2026-05-29 | `ba4e81b` | E1-W3: MLflow LLM span tracing — `_USE_MLFLOW_TRACING` flag + `_wrap_with_mlflow_span()` in `claude_client.py` |
| 2026-05-29 | `87047c3` | E3: `forward_tracking_task` in `daily_krx_flow` + `record_today()` on `AutoForwardRecorder` |
| 2026-05-29 | `e485e1b` | Coverage ~83%→~87%: omit dead `reports.py`, pragma on torch classes, 9 new tests |
| 2026-05-29 | `6909d0a` | P0: sync `requirements.txt` mlflow `>=2.16` → `>=3.0,<4.0` |
| 2026-05-29 | `d746254` | E2: fix PBO gap — `summarize_honesty` pbo fields + `dashboard_bridge` per-candidate `backtest_honesty_summary` |
| 2026-05-11 | `26451eb` | P0: TimeSeriesSplit→PurgedKFold, API universe cap 30, top ValueError guard |
| 2026-05-10 | `717f3a0` | Coverage 78.5%→85.82%, CORS wildcard fix, InterceptHandler isolation |
| 2026-05-10 | `c6f0928` | Deprecated utcnow×6, broker_bridge parse_args typo |
| 2026-05-10 | `d1f5a9a` | numpy read-only array (Python 3.14 compat) |
