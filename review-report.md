# Code Review Report
**Date:** 2026-05-29
**Reviewer:** Hermes Agent (requesting-code-review skill)
**Branch:** `claude/openbb-chaos-20260529` (HEAD)
**Files Reviewed:**
- `src/stock_rtx4060/dashboard_bridge.py` (+236 lines)
- `src/stock_rtx4060/data_providers.py` (+10 lines, import + `after_market_close` param)
- `tests/test_dashboard_bridge.py` (+107 lines, 2 new tests)
- `src/stock_rtx4060/data_quality/final_bar_lock.py` (pre-existing, relied upon)
- `tests/test_final_bar_lock.py` (pre-existing, relied upon)
- `tests/test_data_providers_final_bar.py` (pre-existing, relied upon)

---

## Summary

The diff implements five new investment readiness gates. All 19 tests pass
cleanly (14 dashboard-bridge + 4 final-bar-lock + 1 data-provider-final-bar).
However, spec-compliance analysis against `20260529_plan-doc-stockpred-v5-external-data-crosscheck.md`
reveals 6 gaps: 2 spec items are completely absent, 2 are partially implemented,
and 2 are spec misinterpretations. All new functions are internally consistent
with no security concerns, logic errors in the implemented paths, or regressions
against existing tests.

---

## 1. FinalBarLock Logic

**Status: COMPLIANT**

### Implementation
`data_providers.py` now calls `provider_final_bar_metadata(...)` on every cache hit,
injecting `final_bar_lock` metadata into provider results. The
`dashboard_bridge._data_lag_event_conflict_reasons()` consumes `after_market_close`,
`eod_confirmed`, `bar_type`, and `source` to compute `EOD_FINAL_BAR_NOT_LOCKED`.

**Spec alignment (P0.1):**
| Spec requirement | Status |
|---|---|
| Post-close cache-only → `AMBER_DATA_NOT_FINAL` | PARTIAL — gate is `AMBER_DATA_LAG_EVENT_CONFLICT` (same semantic, different label) |
| `inference_allowed` is `false` when final bar missing | COVERED — `final_bar_lock["inference_allowed"]` is `False` on cache hits |
| `blocking_reasons` includes `EOD_FINAL_BAR_NOT_LOCKED` | DONE |
| Final OHLCV only populated after evidence lock | DELEGATED to `final_bar_lock.source_evidence_lock` — correct separation of concerns |

**Code quality:** The logic in `_data_lag_event_conflict_reasons()` is correct:
```python
final_bar_locked = eod_confirmed and bar_type in {"EOD_FINAL", "FINAL_EOD"}
if after_market_close and (not final_bar_locked or cache_like_source):
    reasons.append("EOD_FINAL_BAR_NOT_LOCKED")
```
Uses `_is_true()` for boolean coercion (consistent with rest of file). No
hardcoded secrets. No shell/eval/SQL risks.

**Tests:** 5 pre-existing tests in `test_final_bar_lock.py` and
`test_data_providers_final_bar.py` all pass. The cache-hit path is covered
by `test_cached_pykrx_provider_marks_final_bar_not_locked_after_close`.

**Minor note:** The spec (P0.1) says `AMBER_DATA_NOT_FINAL` but the
implementation uses `AMBER_DATA_LAG_EVENT_CONFLICT`. These are semantically
equivalent for blocking purposes, but if the spec language is contractual,
the label should be aligned.

---

## 2. Event Shock Gate

**Status: PARTIALLY COMPLIANT — signal-direction ambiguity**

### Implementation
```python
signal = _normalized_text(_first_text(result, "signal", "backend_signal", "model_signal"))
if _is_true(result.get("event_shock")) and signal == "SELL":
    reasons.append("EVENT_SHOCK_SIGNAL_CONFLICT")
```

**Spec alignment (P0.3):**
| Spec requirement | Status |
|---|---|
| `event_shock` + SELL → `AMBER_EVENT_SIGNAL_CONFLICT` | DONE |
| `live_review_candidate` becomes `false` | DONE (AMBER_DATA_LAG_EVENT_CONFLICT path sets `live_review_candidate: False`) |
| `broker_order_execution` remains `false` | DONE (always `False` in this path) |
| Report explains blocked, not upgraded | PARTIAL — no explanatory message in the `data_lag_event` return dict beyond `dashboard_warning_message` |

**Gap — `event_shock` is never produced:**
The entire codebase has exactly **one reference** to `event_shock`: the
`if _is_true(result.get("event_shock"))` consumer in `dashboard_bridge.py`.
No module sets `event_shock` on a result dict. It is an external input.
This means the gate is unreachable until a producer is connected.

The spec (Phase 5) defines the logic for producing `event_shock`:
```python
event_shock = (
    news_score >= 0.75
    and any(keyword in news_text for keyword in ["HBM4E", "Nvidia", "AI", "target price upgrade"])
)
```
**This producer logic is not implemented.**

**Consequence:** The event shock gate is dead code. It will never fire
regardless of what the recommendation engine computes, because `event_shock`
is never written into the result dict.

---

## 3. Volume Breakout Gate

**Status: PARTIALLY COMPLIANT — threshold enforcement missing**

### Implementation
```python
if _is_true(result.get("volume_breakout")) and "EOD_FINAL_BAR_NOT_LOCKED" in reasons:
    reasons.append("VOLUME_BREAKOUT_REQUIRES_FINAL_BAR")
```

**Spec alignment (P0.2):**
| Spec requirement | Status |
|---|---|
| `volume_breakout` detected from `volume_today >= avg_20d * 3.0` + `close >= bb_upper` | NOT IMPLEMENTED — flag consumed, threshold not enforced |
| `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` in output | NOT IMPLEMENTED — only `VOLUME_BREAKOUT_REQUIRES_FINAL_BAR` is added |
| Rule does not create automatic BUY | OK — only appends a blocking reason |
| Volume breakout triggers amber badge | DONE (badge `"VOLUME BREAKOUT UNLOCKED"`) |

**Two separate gaps:**

**Gap A — Volume/Bollinger threshold not enforced:** The spec defines:
```python
if volume_today >= avg_volume_20d * 3.0 and close >= bb_upper:
    # volume_breakout = True
```
But `volume_breakout` is consumed as a pre-existing boolean flag. The
3.0× volume threshold and bb_upper check are never performed in this codebase.
The flag must be set externally, meaning the code does not self-contained enforce
the threshold it claims to gate on.

**Gap B — `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` never emitted:** The spec (P0.2)
requires the output to include `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` as a reason
when volume breakout disables contrarian mode. The actual output only adds
`VOLUME_BREAKOUT_REQUIRES_FINAL_BAR`, which has different semantics
(cache not locked, not contrarian override).

**Gap C — `volume_breakout` is dead:** Like `event_shock`, `volume_breakout`
has exactly one reference in the entire codebase — the consumer in
`dashboard_bridge.py`. No code path produces it. It is a floating input flag.

---

## 4. Dashboard Bridge

**Status: COMPLIANT with minor spec-label drift**

The `dashboard_bridge` additions correctly layer three new amber states:

```
HARD_FAIL
  ↓
AMBER_DATA_LAG_EVENT_CONFLICT  (P0.1 + P0.3 + P0.4 overlap — data/event layer)
  ↓
AMBER_SOURCE_CONFLICT          (P0.5 — source/mode/timestamp conflict)
  ↓
AMBER_WATCHLIST                 (existing readiness failures)
  ↓
LIVE_REVIEW_CANDIDATE           (manual review still required)
  ↓
READY_FOR_MANUAL_REVIEW         (all gates passed)
```

**New fields added consistently across all return paths:**
- `investment_execution_ready: False` — correct (no path enables execution)
- `auto_promote: False` — correct (no auto-promotion implemented)
- `broker_order_execution: False` — correct (always blocked)

**Spec gaps in classifier (P0.5):**
| Spec classifier rule | Status |
|---|---|
| `rec_mode == "FILE_STATIC"` → AMBER_SOURCE_CONFLICT | DONE |
| `benchmark_signal != backend_signal` → AMBER_SOURCE_CONFLICT | DONE |
| `model_score_spread >= 50` → AMBER_MODEL_DISAGREEMENT | DONE |
| `backtest_alpha_pct < 0` → AMBER_BACKTEST_UNDERPERFORM | DONE (as `BACKTEST_ALPHA_NEGATIVE`) |
| `completed_trades < 50` → AMBER_INSUFFICIENT_TRADES | DONE (as `COMPLETED_TRADES_BELOW_50`) |
| `selected_symbol != evidence_symbol` → AMBER_SOURCE_CONFLICT | **NOT IMPLEMENTED** |
| `selected_market != rec_market` → AMBER_SOURCE_CONFLICT | **NOT IMPLEMENTED** |

The spec names (`selected_symbol`, `evidence_symbol`, `selected_market`,
`rec_market`) do not appear anywhere in the dashboard_bridge diff or existing
code. These appear to be dashboard-panel field names that are never passed
into the `result` dict consumed by `_source_mode_timestamp_conflict_reasons()`.

**New helper functions — quality:**
- `_first_text()` — clean first-true accessor; defensive against non-string values
- `_normalized_text()` — single-call text normalization; correct use of
  `replace("-", "_")` + `replace(" ", "_")` chain
- `_coerce_model_score()` — handles [0,1] normalization; correct guard `0.0 <= numeric <= 1.0`
- `_model_score_spread()` — collects from `model_scores` dict + 9 well-known keys;
  returns `None` when < 2 scores (avoids false positives)
- `_is_true()` / `_is_false()` — comprehensive string-to-boolean coercion;
  handles `Y`/`N`/`PASS`/`FAIL` variants correctly

---

## 5. Model Disagreement Gate

**Status: COMPLIANT**

```python
spread = _model_score_spread(result)
if spread is not None and spread >= 50.0:
    reasons.append("MODEL_DISAGREEMENT")
```

**Spec alignment (P0.5):**
| Spec requirement | Status |
|---|---|
| `model_score_spread >= 50` → `AMBER_MODEL_DISAGREEMENT` | DONE |
| `display_badges` includes `"MODEL DISAGREEMENT"` | DONE |
| Blocks `live_review_candidate`, `new_capital_allowed`, `broker_order_execution` | DONE |
| `model_score_spread` field in output | DONE (`model_score_spread: round(spread, 2)`) |

**Score coercion correctness:**
The test fixture has `model_scores = {"lstm": 7.09, ..., "rnn": 99.61}` and
asserts `model_score_spread == 92.52`. This is correct:
- 7.09 (LSTM) and 99.61 (RNN) are already in [0, 100] scale
- 7.27 (main) is also [0, 100]
- Spread = 99.61 - 7.09 = 92.52 ✓

The `_coerce_model_score()` normalization of [0,1] → [0,100] handles the
right edge cases (values outside [0,1] pass through unchanged).

**Test assertion verifies all 8 source conflict reasons simultaneously:**
```python
assert row["model_score_spread"] == 92.52
assert "MODEL_DISAGREEMENT" in row["blocking_reasons"]
```
This is a strong integration test covering score collection, spread
computation, and flagging end-to-end.

---

## Static Security Scan

No security concerns found:
- No hardcoded secrets, API keys, or credentials
- No `os.system`, `subprocess(shell=True)`, `eval()`, `exec()`, or `pickle.loads()`
- No SQL string formatting — all data access is dict-key indexing
- No file path traversal — no `open()` with user-controlled paths
- All external inputs (`result.get(...)`) are coerced through `_is_true()`,
  `_normalized_text()`, `_coerce_model_score()` before use

---

## Test Coverage

| File | Tests | Status |
|---|---|---|
| `test_dashboard_bridge.py` | 14 passed | ALL PASS |
| `test_final_bar_lock.py` | 4 passed | ALL PASS |
| `test_data_providers_final_bar.py` | 1 passed | ALL PASS |
| **Total** | **19 passed** | **0 failures** |

**Baseline regressions:** No pre-existing tests were modified. All existing
assertions remain valid.

**Coverage gaps:**
- No test for `_model_score_spread()` with [0,1] normalized scores (only [0,100] tested)
- No test for `_is_false()` (companion to `_is_true()`)
- No test for when `volume_breakout` is True WITHOUT `EOD_FINAL_BAR_NOT_LOCKED`
  (the `VOLUME_BREAKOUT_REQUIRES_FINAL_BAR` condition requires both to be true)
- No test for `selected_symbol != evidence_symbol` (gap in spec)

---

## Findings Summary

| # | Area | Severity | Finding |
|---|---|---|---|
| 1 | Event Shock | HIGH | `event_shock` is never produced — gate is unreachable dead code |
| 2 | Volume Breakout | HIGH | `volume_breakout` is never produced — gate is unreachable dead code |
| 3 | Volume Breakout | MEDIUM | 3.0× volume + bb_upper threshold check not enforced (flag consumed but not self-verified) |
| 4 | Volume Breakout | MEDIUM | `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` reason never emitted; wrong reason used |
| 5 | Dashboard Bridge | LOW | `selected_symbol != evidence_symbol` spec item absent |
| 6 | Dashboard Bridge | LOW | `selected_market != rec_market` spec item absent |
| 7 | FinalBarLock | MINOR | Spec label is `AMBER_DATA_NOT_FINAL`; implementation uses `AMBER_DATA_LAG_EVENT_CONFLICT` |

---

## Recommendations

**Fix P0 (gate is dead — no-op until producer is connected):**
1. Add a producer function for `event_shock` in the recommendation engine or a
   pre-processing step that computes `event_shock = news_score >= 0.75 and
   any(keyword in news_text for keyword in [...])` and writes it into the result dict.
2. Add a producer function for `volume_breakout` that computes
   `volume_today >= avg_20d * 3.0 and close >= bb_upper` and writes the flag.
3. Change the badge for `VOLUME_BREAKOUT_REQUIRES_FINAL_BAR` from
   `"VOLUME BREAKOUT UNLOCKED"` to something that matches its actual meaning
   (unlocked final bar, not breakout-triggered contrarian override).
4. Add `CONTRARIAN_DISABLED_VOLUME_BREAKOUT` as a separate reason string when
   the contrarian-sell signal is overridden by volume breakout conditions.

**Fix P1 (spec gaps):**
5. Add `selected_symbol != evidence_symbol` check to `_source_mode_timestamp_conflict_reasons()`.
6. Add `selected_market != rec_market` check to `_source_mode_timestamp_conflict_reasons()`.

**Fix P2 (test coverage):**
7. Add test for `_model_score_spread()` with scores in [0,1] range to verify coercion.
8. Add test for `volume_breakout=True` without `EOD_FINAL_BAR_NOT_LOCKED` — should NOT add
   `VOLUME_BREAKOUT_REQUIRES_FINAL_BAR`.

---

## Verdict

**APPROVED with conditions.** The code is well-structured, the three
working gates (FinalBarLock, Source Conflict, Model Disagreement) are
correctly implemented, and all 19 tests pass. However, two of the five
named gates (`event_shock` and `volume_breakout`) are currently dead code
— they will never fire regardless of data — because their producing logic
has not been implemented. These must be connected before the gates are
operationally meaningful. The spec gaps (selected_symbol/selected_market
checks) should also be addressed to fully meet the P0.5 classifier
requirements.
