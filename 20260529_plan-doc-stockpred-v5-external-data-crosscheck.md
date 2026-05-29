# PLAN_DOC - STOCK.PRED v5.0 External Data Cross-Check and Model Improvement
**Skill:** plan-studio | **Date:** 2026-05-29
**Target:** Samsung Electronics `005930.KS`
**Basis date:** 2026-05-29
**Purpose:** Reconcile STOCK.PRED v5.0 internal Samsung Electronics data with externally observed 2026-05-29 market/news evidence, then plan model improvements that prevent stale-data SELL signals during volume-backed breakout regimes.

---

## Overview

STOCK.PRED v5.0 used a `PYKRX:CACHE` snapshot for `005930.KS` that showed close `308,500`, low `308,000`, and volume `9.04M`.

External public market pages observed after close show Samsung Electronics at `317,000` on 2026-05-29. Public pages disagree on final volume, so final volume must be rechecked against an authoritative market data source before changing model logic.

Samsung Semiconductor Newsroom published the HBM4E 12-layer sample shipment news on 2026-05-29. This confirms that a large news catalyst existed on the same date as the price move.

Reuters-syndicated coverage also confirms Samsung shipped 12-layer HBM4E samples and that shares rose as much as 6.5% intraday. This supports the event-shock diagnosis, but it does not replace final OHLCV evidence from KRX, Naver Finance, or a broker API.

Assumption: The user-provided `37,241,537` share volume is treated as a candidate external value until validated against KRX or a broker API.

Assumption: The user-provided KB/Mirae target prices of `530,000` to `550,000` are not treated as confirmed. A checked public KB report briefing showed `360,000`, average consensus `290,400`, and top public target `390,000`.

Sources checked:
- Samsung HBM4E newsroom: https://news.samsungsemiconductor.com/kr/%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90-%EC%84%B8%EA%B3%84-%EC%B5%9C%EC%B4%88-hbm4e-12%EB%8B%A8-%EC%83%98%ED%94%8C-%EC%B6%9C%ED%95%98/
- Reuters-syndicated HBM4E report: https://www.investing.com/news/stock-market-news/samsung-electronics-ships-faster-hbm4e-chip-samples-to-customers-shares-jump-4715878
- Market close public page: https://mbnmoney.mbn.co.kr/stock/item/news?code=005930&page=26&type=
- KB report briefing checked: https://www.newspim.com/news/view/20260504000304
- AI investment-source caution: https://www.finra.org/investors/insights/artificial-intelligence-and-investment-fraud

## Adoption Verdict

AMBER_SOURCE_CONFLICT - adopt this report as a P0 patch requirement, but keep `005930.KS` blocked from investment-candidate and LIVE_REVIEW status until source, signal, model, backtest, REC, and paper-forward evidence agree.

This is not investment-ready information. The current dashboard state is a conflict state because Benchmark KRX can show BUY while the backend Signal panel shows SELL, backtest alpha is deeply negative, and REC may still be a static FILE snapshot from a different evidence context.

Confirmed for the patch requirement:
- Internal JSON values: `close=308,500`, `volume=9,039,622`, `contrarian_mode=true`, `Signal=SELL`, `Alpha=-186.65%`, `completedTrades=32`.
- HBM4E event: confirmed by Samsung Newsroom and Reuters-syndicated coverage.
- Model failure mode: stale market data plus missing event context can make a technically consistent SELL unsuitable for live investment execution.
- Dashboard conflict mode: `Benchmark BUY`, `Signal SELL`, `Backtest Alpha -186.65%`, and `REC FILE static snapshot` must be treated as blocking evidence, not as mixed confirmation.

Not yet confirmed for hard-coded model input:
- Final close `317,000`.
- Final volume `37,241,537`.
- KB/Mirae target prices `530,000` to `550,000`.

Required action from this verdict:
- Use `AMBER_SOURCE_CONFLICT` blocking, not BUY conversion.
- Keep broker execution disabled.
- Allow paper recording, but do not allow investment-candidate or LIVE_REVIEW promotion.
- Require KRX, Naver Finance, or broker API evidence lock before final OHLCV and analyst target numbers enter model features.
- Treat model-score disagreement, negative alpha, static REC mode, and incomplete 30-day forward evidence as independent blockers.

## Goals

1. Verify whether the internal `PYKRX:CACHE` snapshot lagged the 2026-05-29 final market state.
2. Prevent stale OHLCV data from driving a high-confidence SELL or short-side signal after a late-session breakout.
3. Add a model rule plan for volume-backed breakout detection before contrarian or mean-reversion logic is applied.
4. Add a plan for news and analyst-consensus evidence to affect advisory confidence without bypassing safety gates.
5. Keep outputs as screening and research support only, not broker execution or personalized investment advice.
6. Add a dashboard conflict classifier that blocks LIVE_REVIEW when benchmark, backend signal, REC source, model scores, backtest, or paper evidence disagree.

## Scope

### In Scope

- Compare internal STOCK.PRED v5.0 data for `005930.KS` against final 2026-05-29 external OHLCV.
- Validate the exact 2026-05-29 close, low, high, and volume from KRX or a broker API.
- Mark `PYKRX:CACHE` snapshots as stale when post-close data differs from an authoritative final bar.
- Define a Dynamic Contrarian Mode switch based on volume expansion and Bollinger upper-band breakout.
- Extend the existing news sentiment path to capture HBM, target-price revision, AI memory, and analyst-consensus signals.
- Rebalance trend-following versus mean-reversion ensemble weight only after backtest and forward-paper evidence.
- Add review criteria for backtest honesty, OOF coverage, PBO, and post-close data freshness.
- Add `AMBER_SOURCE_CONFLICT` rules for Benchmark-vs-Signal disagreement, static REC source, model-score spread, negative alpha, insufficient trades, and missing forward-paper evidence.

### Out of Scope

- Automatic broker order placement.
- Claiming a new BUY/HOLD/SELL investment recommendation before implementation and validation.
- Replacing the entire STOCK.PRED architecture.
- Using unverified web snippets as final market data.
- Treating unverified `530,000` to `550,000` analyst targets as confirmed model input.
- Building a full NLP training system before proving the simpler headline and event-feature path.
- Treating Benchmark BUY as sufficient when backend Signal, Backtest, REC, or Paper evidence conflicts.

## Constraints

- The current system is report-only and screening-output-only.
- The model must not upgrade a verdict solely because news sentiment is positive.
- Final OHLCV must come from an authoritative source, not a cached UI snapshot.
- Public webpages can disagree on volume, so volume must pass a source-priority rule.
- The existing `NewsSentimentAgent` has a degraded mode that returns neutral when live news fetch fails.
- Existing model-health gates such as AUC, OOF coverage, and backtest honesty must remain active.
- Assumption: `005930.KS` market data may require KRX, broker, or licensed provider access for fully authoritative final bars.
- A screen with `Benchmark BUY` and backend `Signal SELL` must not be summarized as a valid blended investment signal.
- Static REC FILE snapshots must not be used as live KRX evidence.
- `paper_recording_allowed=true` does not imply `live_review_candidate=true`.

## Phases

### Phase 1 - Evidence Freeze

Freeze the exact internal and external facts for 2026-05-29 before changing model behavior.

Required evidence:
- Internal dashboard snapshot value: close `308,500`, low `308,000`, volume `9.04M`, source `PYKRX:CACHE`.
- Internal model output: backend model comparison produced `ENSEMBLE 7.34` and `SELL`.
- External close candidate: `317,000` at 2026-05-29 15:30.
- External volume candidate: user-provided `37,241,537`, but source conflict must be resolved.
- News catalyst: Samsung HBM4E 12-layer sample shipment published 2026-05-29.
- Reuters-syndicated catalyst context: shares rose as much as 6.5% intraday after the HBM4E sample shipment report.
- Regulatory/source-control context: FINRA/SEC/NASAA caution that AI-generated investment information can be inaccurate or outdated and should be checked against underlying sources and multiple sources.

Evidence lock requirement:
```json
{
  "bar_type": "EOD_FINAL",
  "source": "KRX_FINAL_OR_NAVER_OR_BROKER_API",
  "eod_confirmed": true,
  "close_final": null,
  "volume_final": null,
  "cache_close": 308500,
  "cache_volume": 9039622,
  "data_lag_pct_close": null,
  "data_lag_ratio_volume": null,
  "source_urls": [],
  "locked_at_utc": null
}
```

Rule:
- `close_final` and `volume_final` must stay `null` until the authoritative source is captured.
- If an implementation uses `317000` or `37241537`, the evidence file must include the source URL, retrieval time, and provider name.

### Phase 2 - Final Bar Data Pipeline

Replace cache-first inference with final-bar-first inference for post-close runs.

Required behavior:
- Post-close inference must fetch the final OHLCV bar from KRX or broker API.
- If final data is unavailable, the model must label the result as stale or incomplete.
- If cached close or volume differs materially from final data, inference must block or downgrade confidence.

P0 rule:
```python
if bar.source.endswith(":CACHE") and is_after_market_close(symbol):
    readiness_status = "AMBER_DATA_NOT_FINAL"
    inference_allowed = False
    blocking_reasons.append("EOD_FINAL_BAR_NOT_LOCKED")
```

### Phase 3 - Dynamic Contrarian Mode

Add a rule that disables contrarian behavior during confirmed volume-backed breakouts.

Proposed trigger:
- `volume_today / avg_volume_20d > 3.0`
- and `close > bbUpper`
- and final bar source is authoritative.

Required action:
- Force `contrarian_mode = false` for that inference.
- Increase trend-following evidence weight.
- Add a reason string that explains the switch in plain language.

P0 rule:
```python
volume_breakout = (
    today_volume >= avg_volume_20d * 3.0
    and close >= bb_upper
)

if volume_breakout:
    contrarian_mode = False
    trend_following_weight += 0.30
    blocking_reasons.append("CONTRARIAN_DISABLED_VOLUME_BREAKOUT")
```

Assumption: A tolerance rule such as `close > bb_upper * 0.995` may be evaluated later, but the first implementation should use the stricter rule unless evidence shows excessive false negatives.

### Phase 4 - News and Consensus Features

Use text/news evidence as advisory input with safety limits.

Required feature candidates:
- HBM/HBM4/HBM4E event flag.
- AI memory catalyst flag.
- Analyst target-price revision direction.
- Analyst target-price source confidence.
- News recency relative to the market bar.

Safety boundary:
- News sentiment may raise or lower confidence.
- News sentiment must not override data freshness, model health, or broker-safety gates.
- A strong positive event must not convert SELL to BUY automatically.
- A strong positive event conflicting with SELL should produce AMBER review or block live-review eligibility.

P0 rule:
```python
event_shock = (
    news_score >= 0.75
    and any(keyword in news_text for keyword in ["HBM4E", "Nvidia", "AI", "target price upgrade"])
)

if event_shock and signal == "SELL":
    readiness_status = "AMBER_EVENT_SIGNAL_CONFLICT"
    live_review_candidate = False
```

### Phase 5 - Ensemble Weight Review

Review whether trend-following models should receive more weight during breakout regimes.

Required comparisons:
- Current backend model score path.
- Existing benchmark row where `005930` showed LSTM `68`, LR `88`, XGB `78`, RNN `77`, ENS `77`, signal `BUY`.
- Backend model comparison where main model scored `7.34` and produced `SELL`.
- Latest conflict example: main `7.27`, LogReg `95.96`, XGBoost `80.48`, RNN `99.61`, LSTM `7.09`.

Decision rule:
- Only adjust weights after out-of-sample and forward-paper evidence shows the regime switch improves results.
- If model score spread is `>= 50`, return `AMBER_MODEL_DISAGREEMENT` and block live decision.

### Phase 6 - Dashboard Source Conflict Classifier

Add a classifier that checks whether the visible dashboard is internally consistent enough for live review.

P0 rule:
```python
def classify_dashboard_conflict(e):
    if e.rec_mode == "FILE_STATIC":
        return "AMBER_SOURCE_CONFLICT"

    if e.selected_market != e.rec_market:
        return "AMBER_SOURCE_CONFLICT"

    if e.selected_symbol != e.evidence_symbol:
        return "AMBER_SOURCE_CONFLICT"

    if e.benchmark_signal != e.backend_signal:
        return "AMBER_SOURCE_CONFLICT"

    if e.backtest_alpha_pct < 0:
        return "AMBER_BACKTEST_UNDERPERFORM"

    if e.completed_trades < 50:
        return "AMBER_INSUFFICIENT_TRADES"

    if e.model_score_spread >= 50:
        return "AMBER_MODEL_DISAGREEMENT"

    return "PAPER_RECORDING_ALLOWED"
```

Required badge output for this case:
```json
{
  "readiness_status": "AMBER_SOURCE_CONFLICT",
  "display_badges": [
    "SIGNAL != BENCHMARK",
    "MODEL DISAGREEMENT",
    "BACKTEST ALPHA NEGATIVE",
    "STATIC REC NOT LIVE",
    "REPORT ONLY"
  ],
  "live_review_candidate": false,
  "paper_recording_allowed": true,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "manual_approval_required": true
}
```

### Phase 7 - Validation and Release Gate

Run regression and evidence checks before marking the plan implemented.

Required verification:
- Unit tests for stale final-bar detection.
- Unit tests for volume breakout rule.
- Unit tests for contrarian-mode override.
- Snapshot test showing stale cache is not reported as live data.
- Backtest or paper-forward comparison for `005930.KS`.
- Unit tests for `AMBER_SOURCE_CONFLICT` when Benchmark BUY and backend Signal SELL disagree.
- Unit tests that static REC FILE mode blocks LIVE_REVIEW.
- Unit tests that negative alpha and completed trades below 50 block investment-candidate promotion.

## Tasks

1. Capture the current internal STOCK.PRED v5.0 `005930.KS` snapshot as an evidence fixture.
2. Fetch authoritative 2026-05-29 final OHLCV for `005930.KS`.
3. Compare internal close, low, high, and volume against the authoritative final bar.
4. Add a freshness field to provider output that distinguishes `CACHE`, `LIVE_INTRADAY`, and `FINAL_BAR`.
5. Block or downgrade post-close inference when final bar freshness is missing.
6. Add a breakout detector using volume ratio and Bollinger upper-band breakout.
7. Add tests for the breakout detector with close `317,000` and stale close `308,500` fixture paths.
8. Add a reason string when contrarian mode is disabled by breakout evidence.
9. Extend news sentiment input mapping to preserve HBM4E and target-price revision signals.
10. Add source confidence for analyst target prices.
11. Reject or mark analyst target values as unverified when public sources conflict.
12. Run `pytest` for data provider, recommendation engine, risk rules, and news sentiment tests.
13. Produce a before/after report showing signal, data freshness, volume ratio, and model-health gates.
14. Add a blocked-state output contract for `005930.KS` when cache lag and event conflict coexist.
15. Verify that broker order execution remains false in every AMBER_DATA_LAG_EVENT_CONFLICT path.
16. Add dashboard conflict classifier for `Benchmark BUY` versus backend `Signal SELL`.
17. Add static REC FILE blocker so stale or cross-market snapshots cannot support live KRX review.
18. Add model-disagreement blocker for score spread `>= 50`.
19. Add backtest blockers for `alpha < 0` and `completedTrades < 50`.
20. Add paper-forward blocker so 30-day evidence gaps prevent LIVE_REVIEW promotion.

## P0 Patch Requirements

### P0.1 EOD Final Data Lock

The model must not treat `PYKRX:CACHE` as final evidence after market close.

Acceptance criteria:
- Post-close cache-only data returns `AMBER_DATA_NOT_FINAL`.
- `inference_allowed` is `false` when final bar is missing.
- `blocking_reasons` includes `EOD_FINAL_BAR_NOT_LOCKED`.
- Final OHLCV values are only populated after evidence lock.

### P0.2 Volume Breakout Gate

The model must prevent mechanical contrarian SELL behavior during confirmed breakout conditions.

Acceptance criteria:
- `volume_today >= avg_volume_20d * 3.0` and `close >= bb_upper` disables contrarian mode.
- The output includes `CONTRARIAN_DISABLED_VOLUME_BREAKOUT`.
- The rule does not create automatic BUY output.

### P0.3 Event Shock Gate

The model must detect HBM/AI/target-price event conflicts against SELL output.

Acceptance criteria:
- Positive event shock plus SELL returns `AMBER_EVENT_SIGNAL_CONFLICT`.
- `live_review_candidate` becomes `false`.
- `broker_order_execution` remains `false`.
- The report explains that the result is blocked for review, not upgraded to BUY.

### P0.4 Blocked State Contract

Required output shape for this case:
```json
{
  "symbol": "005930.KS",
  "readiness_status": "AMBER_SOURCE_CONFLICT",
  "signal": "SELL",
  "investment_execution_ready": false,
  "paper_recording_allowed": true,
  "live_review_candidate": false,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "blocking_reasons": [
    "PYKRX_CACHE_NOT_EOD_FINAL",
    "POSSIBLE_VOLUME_UNDERCOUNT",
    "HBM4E_EVENT_NOT_IN_FEATURES",
    "CONTRARIAN_MODE_ACTIVE_DURING_BREAKOUT",
    "BACKTEST_ALPHA_NEGATIVE",
    "COMPLETED_TRADES_BELOW_50",
    "MODEL_DISAGREEMENT_HIGH"
  ]
}
```

### P0.5 Dashboard Source Conflict Gate

The dashboard must block investment and LIVE_REVIEW decisions when visible sections disagree.

Acceptance criteria:
- `Benchmark SIG BUY` plus backend `Signal SELL` returns `AMBER_SOURCE_CONFLICT`.
- `REC FILE static snapshot` returns `AMBER_SOURCE_CONFLICT` unless explicitly labeled as historical-only.
- `selected_symbol != evidence_symbol` returns `AMBER_SOURCE_CONFLICT`.
- `selected_market != rec_market` returns `AMBER_SOURCE_CONFLICT`.
- `model_score_spread >= 50` returns `AMBER_MODEL_DISAGREEMENT`.
- `backtest_alpha_pct < 0` returns `AMBER_BACKTEST_UNDERPERFORM`.
- `completed_trades < 50` returns `AMBER_INSUFFICIENT_TRADES`.
- `paper_recording_allowed` may remain true.
- `live_review_candidate`, `new_capital_allowed`, and `broker_order_execution` must remain false.

Current `005930.KS` intended final state:
```text
technical trend: strong
external news momentum: present
minimum model quality: partially passing
model consistency: failed
backtest alpha: failed
REC source: static or source-conflicted until proven live
investment execution: blocked
paper recording: allowed
```

## Risks

- If KRX or broker final data is unavailable, the model can only mark the signal as partial, not corrected.
- If public volume sources keep conflicting, the model may correctly block inference but still not know the final volume.
- If HBM4E news is ingested without source confidence, it may overstate sentiment.
- If contrarian mode is disabled too broadly, the model may chase false breakouts.
- If ensemble weights are changed without OOS evidence, the model may improve one example and degrade broader performance.
- If source evidence is not locked, the report can overfit a patch to unverified close, volume, or analyst-target numbers.
- If Benchmark BUY is shown beside backend SELL without an explicit conflict badge, users can mistake a dashboard inconsistency for a valid consensus signal.
- If static REC FILE output is mixed with a live KRX selection, the dashboard can present stale or wrong-market evidence as current evidence.

## Review Criteria

- The 2026-05-29 `005930.KS` final bar comes from an authoritative provider or is explicitly marked unavailable.
- A stale `PYKRX:CACHE` bar cannot be shown as final live evidence.
- The model explains why a contrarian override did or did not happen.
- The model does not use unverified analyst target prices as confirmed inputs.
- Existing model-health gates still report AUC, OOF coverage, PBO, and backtest honesty.
- The dashboard/report clearly separates data freshness, model score, news catalyst, and final signal.
- Tests pass for data freshness, breakout rule, news feature mapping, and recommendation output schema.
- The final state is AMBER review/blocking when evidence is incomplete, not DONE or BUY.
- `005930.KS` remains blocked from LIVE_REVIEW while `Benchmark BUY`, backend `Signal SELL`, negative alpha, static REC, or incomplete 30-day forward evidence persists.
- Paper recorder eligibility is displayed separately from investment readiness.

## Deliverables

- External data cross-check evidence file for `005930.KS` on 2026-05-29.
- Authoritative final-bar provider path or documented unavailability result.
- Dynamic Contrarian Mode implementation plan and tests.
- News and analyst-consensus feature mapping plan.
- Before/after STOCK.PRED v5.0 model behavior report.
- Regression test result summary.
- P0 patch requirement checklist showing EOD Final Data Lock, Volume Breakout Gate, Event Shock Gate, and Blocked State Contract.
- Dashboard conflict-classifier checklist showing `AMBER_SOURCE_CONFLICT`, `AMBER_MODEL_DISAGREEMENT`, `AMBER_BACKTEST_UNDERPERFORM`, and `AMBER_INSUFFICIENT_TRADES` cases.
