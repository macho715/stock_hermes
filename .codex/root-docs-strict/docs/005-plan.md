# Plan — OpenBB Macro Ingestor + Chaos Engineering

**Session:** auto-20260529-010925
**Date:** 2026-05-29
**Type:** FEATURE
**Branch:** `claude/openbb-chaos-20260529`

---

## 1. Overview & Goals

두 가지 산출물을 구현:
1. **OpenBB 매크로 데이터 ingestor** — `src/stock_rtx4060/data_lake/ingest/openbb_ingestor.py`
2. **Chaos Engineering 테스트 스위트** — `tests/test_chaos_paper_trading.py`

---

## 2. Deliverables

### 2.1 OpenBB Macro Ingestor (PR-O)

**File:** `src/stock_rtx4060/data_lake/ingest/openbb_ingestor.py`

| Task | Description |
|------|-------------|
| PR-O1 | OpenBB MMA ( macroeconomic analytics) 데이터 fetch |
| PR-O2 | `panel_fetcher` → `advisors/macro_regime.py` 연동 |
| PR-O3 | `advisors/orchestrator.py`에 OpenBB MCP tool 등록 |

**Dep:** `openbb>=4.4` (requirements-openbb.txt)

**Design principles:**
- Graceful degradation: OpenBB unavailable 시Warning 로그 + continue
- No hard dependency on OpenBB in main trading path
- Configurable via `config/data_providers.example.json`

### 2.2 Chaos Engineering Test Suite (PR-C)

**File:** `tests/test_chaos_paper_trading.py`

| Task | Description |
|------|-------------|
| PR-C1 | `test_chaos_open_positions_exceeded` — max_open_positions 초과 시 rejection |
| PR-C2 | `test_chaos_daily_new_exceeded` — daily_new_count >= 3 rejection |
| PR-C3 | `test_chaos_buy_score_below_threshold` — score < 56 rejection |
| PR-C4 | `test_chaos_force_rerun_no_reason` — force_rerun=True + no rerun_reason → ValueError |
| PR-C5 | `test_chaos_stale_bars` — _validate_bars가 과거 데이터陈旧判断하는지 검증 |

**Dep:** `pytest`, `unittest.mock`

---

## 3. Files to Change

| File | Action |
|------|--------|
| `src/stock_rtx4060/data_lake/ingest/openbb_ingestor.py` | Create |
| `src/stock_rtx4060/advisors/macro_regime.py` | Modify (add panel_fetcher) |
| `src/stock_rtx4060/advisors/orchestrator.py` | Modify (register OpenBB tool) |
| `tests/test_chaos_paper_trading.py` | Create |
| `requirements-openbb.txt` | Verify (`openbb>=4.4`) |

---

## 4. TDD Approach

```
RED    → write failing test for each scenario
GREEN  → minimal code to pass
REFACTOR → clean up
```

---

## 5. Out of Scope (previous pipeline)

- GAP-01~05 (already implemented)
- MLflow log_input (already implemented)
- requirements.in mlflow>=3.0 (already done)

---

## 6. Acceptance Criteria

- [ ] `openbb_ingestor.py` passes `python3 -m py_compile`
- [ ] `test_chaos_paper_trading.py` passes `pytest tests/test_chaos_paper_trading.py -v`
- [ ] Varlock scan: no secrets in new files
- [ ] No regression in existing tests (346 pass)