# STOCK·PRED v5.1 실전 검토 가능 수준 업그레이드 최종 설계서

작성일: 2026-05-29  
대상 프로젝트: `C:\Users\jichu\Downloads\주식\stock_1901`  
대상 시스템: `STOCK·PRED v5.0`  
문서 상태: **CODE-VERIFIED / PATCH REQUIRED**  
운영 경계: **Report-only / Manual Review / No Broker Execution**

---

## 0. Executive Summary

판정: **AMBER PATCH REQUIRED**

현재 시스템은 `BUY score`를 생성하고 OOF 기반 backtest를 일부 적용하고 있으나, **실전 투자 후보로 올릴 수 있는 검증 체계는 아직 미완성**이다. 특히 `PurgedKFold`의 pre-test purge 하한이 잘못 설정되어, 일부 train label window가 test span과 겹칠 수 있다. 이 문제는 live-review 승격 전에 반드시 수정해야 한다.

핵심 결론:

1. `PurgedKFold` API는 유지한다:  
   `PurgedKFold(n_splits, embargo_pct).split(X, y=None, groups=...)`

2. 현재 `recommendation_engine.py`는 `groups=np.arange(len(X)) + horizon`과 `oof.fillna(0.5)` 기반 backtest를 사용하므로 방향은 맞다.

3. 그러나 `cv.py`의 purge logic은 test span overlap 전체를 보장하지 못한다.

4. `backtest_honesty`는 계산되지만 `_verdict()`의 live 후보 판정에는 직접 반영되지 않는다.

5. `cv_gap`은 실제로는 `embargo_samples`에 가깝다. `horizon`, `purge`, `embargo` 의미를 분리해야 한다.

6. 실전 검토 가능 수준으로 올리려면 다음 7개 레이어가 필요하다.

```text
1. PurgedKFold no-leakage patch
2. OOF-only backtest hard gate
3. CPCV / PBO / Deflated Sharpe 진단
4. Cost / slippage / liquidity stress
5. Regime filter
6. Event / sentiment PIT feature
7. Portfolio risk gate + Model Card governance
```

---

## 1. 확인한 코드 및 문서

| No | 파일 | 확인 내용 | 판정 |
|---:|---|---|---|
| 1 | `docs/AGENTS.md` | Report-only, broker execution 금지, `cv.split(X, groups=_groups)` 필수 규칙 존재 | PASS |
| 2 | `src/stock_rtx4060/ml/cv.py` | `PurgedKFold` 운영 API 존재. 단, pre-test purge 하한 버그 있음 | FAIL/P0 |
| 3 | `src/stock_rtx4060/recommendation_engine.py` | PurgedKFold 사용, `groups=np.arange+horizon`, OOF probability 생성 | PASS/AMBER |
| 4 | `src/stock_rtx4060/backtest_honesty.py` | OOF coverage, Sharpe, MDD, cost buffer, cv_gap/horizon check 존재 | AMBER |
| 5 | `src/stock_rtx4060/backtester.py` | transaction cost, slippage, Kelly/risk sizing, DSR optional 기능 존재 | PASS/AMBER |
| 6 | `tests/test_purged_kfold.py` | 기본 split/embargo/groups length 테스트 존재. 전체 no-leakage property는 부족 | AMBER |
| 7 | `tests/test_walk_forward_purged.py` | OOF 생성 및 pre-test overlap 일부 검증 | AMBER |
| 8 | `tests/test_ml_hpo.py` | HPO가 `cv.split(..., groups=...)`를 호출하는지 검증 | PASS |

---

## 2. 현재 코드에서 확인된 핵심 문제

## CV-01. `PurgedKFold` pre-test purge 하한 오류

### 현재 의도

금융 label horizon이 있는 경우, train sample의 label window `[train_start, train_end]`가 test span `[test_start, test_end]`와 겹치면 train에서 제거해야 한다.

정확한 overlap 판정은 아래다.

```python
overlap = (train_start <= test_end) and (train_end >= test_start)
```

### 현재 운영 코드의 문제

현재 `cv.py`는 test fold의 하한을 `test_start`가 아니라 `end_times[test_start]`로 잡는다.

```python
t_lo = end_times[test_start]

for i in range(0, test_start):
    if end_times[i] >= t_lo:
        train_mask[i] = False
```

`groups = np.arange(len(X)) + horizon`일 때 예시는 아래와 같다.

```text
horizon = 5
test_start = 20
test fold = 20..39
정상 test span = [20, 44]
현재 t_lo = end_times[20] = 25

train row 17:
label window = [17, 22]
정상 기준: [17,22]는 test span [20,44]와 겹침 → purge 필요
현재 코드: end_times[17] = 22 < t_lo 25 → 생존 가능
```

### 영향

| 항목 | 영향 |
|---|---|
| Accuracy/AUC | 낙관적으로 보일 수 있음 |
| OOF backtest | 일부 label leakage 가능 |
| BUY score | 실제보다 강하게 표시될 수 있음 |
| Live-review 승격 | 현재 로직으로는 금지해야 함 |

### 조치

`cv.py`의 split core를 아래처럼 고정한다.

```python
positions = np.arange(n_samples)
starts = positions
ends = np.asarray(groups if groups is not None else positions)

test_start = int(test_idx[0])
test_stop_excl = int(test_idx[-1]) + 1
test_end = int(np.max(ends[test_idx]))

train_mask = np.ones(n_samples, dtype=bool)
train_mask[test_start:test_stop_excl] = False

# Correct purge: train label window overlaps test span
overlap = (starts <= test_end) & (ends >= test_start)
train_mask &= ~overlap

# Embargo after test block
embargo = int(np.floor(n_samples * self.embargo_pct))
if embargo > 0:
    emb_stop = min(test_stop_excl + embargo, n_samples)
    train_mask[test_stop_excl:emb_stop] = False
```

---

## CV-02. `embargo_pct >= 1` 미차단

현재 `cv.py`는 `embargo_pct < 0`만 거부한다. 운영 설계상 `0 <= embargo_pct < 1`만 허용해야 한다.

### 조치

```python
if not (0.0 <= embargo_pct < 1.0):
    raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
```

---

## CV-03. `cv_gap` 의미 혼선

현재 `model_stats["gap"]`은 다음 코드에서 산출된다.

```python
"gap": int(np.floor(len(X) * embargo_pct))
```

즉, 이 값은 `walk-forward gap`도 아니고 `label horizon`도 아니며, 실제 의미는 **embargo sample count**에 가깝다.

### 조치

JSON과 dashboard payload를 아래처럼 분리한다.

```json
{
  "cv_method": "purged_kfold_oof",
  "label_horizon_bars": 20,
  "purge_rule": "train_label_window_disjoint_from_test_span",
  "embargo_pct": 0.0426,
  "embargo_samples": 20,
  "oof_probability_source": "OOF_ONLY",
  "backtest_probability_source": "OOF_ONLY_FILLED_0_5"
}
```

`backtest_honesty.py`의 `WALK_FORWARD_GAP`도 아래처럼 rename해야 한다.

```text
기존: WALK_FORWARD_GAP
변경: EMBARGO_VS_HORIZON
```

단, 이 체크는 “embargo_samples >= horizon”을 검증하는 것이므로 실제 no-leakage 검증과는 별도다. No-leakage는 `PurgedKFold` property test에서 보장해야 한다.

---

## 3. 현재 시스템의 좋은 점

## 3.1 Report-only 경계가 있다

`docs/AGENTS.md`에는 broker execution, credentials, destructive account actions 금지가 명시되어 있다. 이 경계는 유지해야 한다.

필수 고정 필드:

```json
{
  "screening_output_only": true,
  "manual_approval_required": true,
  "broker_order_execution": false,
  "new_capital_allowed": false
}
```

## 3.2 OOF-only backtest 방향은 이미 일부 구현되어 있다

`recommendation_engine.py`는 fold별 model fit 이후 OOF probability를 채우고, 누락값은 0.5 neutral로 변환한다.

```python
oof.iloc[test_idx] = prob
neutral_probs = oof.fillna(0.5).to_numpy(dtype=float)

return {
    "oof_probs": oof,
    "backtest_probs": neutral_probs,
}
```

이 방향은 맞다. 다만 명시 필드가 부족하므로 아래를 추가해야 한다.

```python
"probability_source": "OOF_ONLY",
"neutral_fill_value": 0.5,
"latest_prob_used_for_backtest": False
```

## 3.3 Backtester는 비용과 slippage를 이미 반영한다

현재 `BacktestConfig`에는 아래 기본값이 있다.

```python
transaction_cost = 0.001
slippage = 0.0005
```

그러나 실전 검토 후보 승격에는 단일 비용값이 아니라 **1x / 3x / stress 비용 시나리오**가 필요하다.

---

## 4. 현재 시스템의 부족한 점

| No | 부족 항목 | 현재 상태 | 필요한 조치 |
|---:|---|---|---|
| 1 | No-leakage CV | bug 있음 | `overlap = starts <= test_end & ends >= test_start`로 수정 |
| 2 | OOF-only hard gate | 구현은 있으나 테스트·payload 명시 부족 | `probability_source=OOF_ONLY` 테스트 추가 |
| 3 | Live readiness | score/verdict 중심 | 별도 `investment_readiness_score` 추가 |
| 4 | backtest_honesty gate | 계산만 하고 `_verdict()`에는 미반영 | PASS 아니면 live-review 차단 |
| 5 | Alpha after cost | 없음 | 1x/3x cost stress 추가 |
| 6 | CPCV/PBO | 없음 | live-review 승격 전 정밀 진단 추가 |
| 7 | DSR/PSR | backtester 옵션으로 존재하나 기본 off | readiness gate에 연결 |
| 8 | Event/Sentiment | 제한적 | `available_at` 기반 PIT feature로 추가 |
| 9 | Portfolio risk | 단일 종목 risk plan 중심 | position cap, CVaR, sector cap 추가 |
| 10 | Model card | 없음 또는 약함 | candidate별 자동 생성 |

---

## 5. 실전 검토 가능 수준 목표

중요: 여기서 말하는 실전 검토 가능 수준은 자동매매가 아니다.  
의미는 **사람이 투자 검토 테이블에 올려도 될 정도로 검증 증거가 충분한 상태**다.

## 5.1 상태 정의

| Level | 상태 | 의미 | 신규 자금 |
|---:|---|---|---|
| 0 | HARD_BLOCK | 데이터·검증·누수·감사 실패 | 금지 |
| 1 | AMBER_WATCHLIST | 연구·관찰 후보 | 금지 |
| 2 | PAPER_CANDIDATE | paper trading 대상 | 금지 |
| 3 | PAPER_PASS | forward 검증 통과 | 금지 |
| 4 | LIVE_REVIEW_CANDIDATE | 사람이 실전 검토 가능 | 자동 투입 금지 |
| 5 | MANUAL_APPROVED | 별도 사람 승인 완료 | 수동 실행만 |

---

## 6. Live-review 승격 기준

## 6.1 Hard Block 조건

아래 중 하나라도 true면 즉시 `HARD_BLOCK`.

```python
hard_block = (
    broker_order_execution is True
    or provider_audit_exists is False
    or point_in_time_safe is False
    or data_leakage_detected is True
    or oof_only_backtest is False
    or screening_output_only is not True
)
```

## 6.2 AMBER WATCHLIST 조건

```python
amber = (
    model_accuracy < 0.50
    or model_auc < 0.50
    or completed_trades < 50
    or alpha_after_cost <= 0
    or backtest_honesty_status != "PASS"
)
```

## 6.3 PAPER PASS 조건

```python
paper_pass = (
    model_accuracy >= 0.52
    and model_auc >= 0.55
    and oof_coverage >= 0.85
    and completed_trades >= 80
    and alpha_after_1x_cost > 0
    and alpha_after_3x_cost >= 0
    and sharpe >= 1.20
    and max_drawdown_within_limit is True
)
```

## 6.4 LIVE REVIEW 조건

```python
live_review = (
    paper_pass is True
    and cpcv_path_pass_rate >= 0.60
    and pbo <= 0.20
    and deflated_sharpe > 0
    and regime_stress == "PASS"
    and liquidity_turnover == "PASS"
    and paper_trading_days >= 30
    and paper_alpha >= 0
    and model_card_exists is True
)
```

---

## 7. 최종 readiness JSON 스키마

```json
{
  "schema_version": "stock_pred_readiness.v1",
  "symbol": "005930.KS",
  "as_of": "2026-05-29T00:00:00+09:00",
  "bar_type": "EOD_OR_INTRADAY",
  "price_provider": "PYKRX",
  "model_provider": "yfinance",
  "raw_signal": "BUY",
  "raw_score": 91.88,
  "investment_readiness_score": 37.0,
  "readiness_status": "AMBER_WATCHLIST",
  "live_review_candidate": false,
  "new_capital_allowed": false,
  "manual_approval_required": true,
  "broker_order_execution": false,
  "screening_output_only": true,
  "validation": {
    "cv_method": "purged_kfold_oof",
    "oof_only_backtest": true,
    "backtest_probability_source": "OOF_ONLY_FILLED_0_5",
    "label_horizon_bars": 20,
    "embargo_pct": 0.01,
    "embargo_samples": 5,
    "purge_rule": "train_label_window_disjoint_from_test_span",
    "cpcv_enabled": false,
    "pbo": null,
    "deflated_sharpe": null,
    "backtest_honesty": "AMBER"
  },
  "cost_stress": {
    "fee_model": "configured",
    "slippage_bps_1x": 5,
    "slippage_bps_3x": 15,
    "alpha_after_1x_cost": null,
    "alpha_after_3x_cost": null,
    "turnover_ok": null
  },
  "blocking_reasons": [
    "ACCURACY_BELOW_52",
    "ALPHA_AFTER_COST_NOT_POSITIVE",
    "COMPLETED_TRADES_BELOW_80",
    "CPCV_NOT_RUN",
    "PAPER_TRADING_NOT_DONE"
  ]
}
```

---

## 8. 구현 패치 상세

## Phase 1 — `cv.py` P0 patch

### 목표

- 기존 API 유지
- full overlap purge 보장
- `embargo_pct >= 1` 거부
- `groups` length mismatch 유지
- no-leakage property test 통과

### 핵심 코드

```python
class PurgedKFold:
    def __init__(self, n_splits: int = 5, embargo_pct: float = 0.01) -> None:
        if n_splits < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        if not (0.0 <= embargo_pct < 1.0):
            raise ValueError(f"embargo_pct must be in [0, 1), got {embargo_pct}")
        self.n_splits = int(n_splits)
        self.embargo_pct = float(embargo_pct)

    def split(self, X, y=None, groups=None):
        n_samples = len(X)
        if n_samples < self.n_splits + 1:
            raise ValueError(
                f"PurgedKFold requires n_samples (>{self.n_splits}) but got {n_samples}"
            )

        positions = np.arange(n_samples)
        starts = positions

        if groups is None:
            ends = positions
        else:
            ends = np.asarray(pd.Series(groups).values)
            if len(ends) != n_samples:
                raise ValueError(
                    f"groups length {len(ends)} does not match X length {n_samples}"
                )
            if np.any(ends < starts):
                raise ValueError("groups must contain label end index >= row position")

        embargo = int(np.floor(n_samples * self.embargo_pct))

        fold_sizes = np.full(self.n_splits, n_samples // self.n_splits, dtype=int)
        fold_sizes[: n_samples % self.n_splits] += 1

        current = 0
        for fold_size in fold_sizes:
            test_start = current
            test_stop = current + int(fold_size)
            current = test_stop

            test_idx = positions[test_start:test_stop]
            test_end = int(np.max(ends[test_idx]))

            train_mask = np.ones(n_samples, dtype=bool)
            train_mask[test_start:test_stop] = False

            overlap = (starts <= test_end) & (ends >= test_start)
            train_mask &= ~overlap

            if embargo > 0:
                emb_stop = min(test_stop + embargo, n_samples)
                train_mask[test_stop:emb_stop] = False

            yield positions[train_mask], test_idx
```

---

## Phase 2 — 운영 테스트 보강

### `tests/test_purged_kfold.py`

추가 테스트:

```python
@pytest.mark.parametrize("horizon", [0, 1, 5, 15])
@pytest.mark.parametrize("seed", range(5))
def test_no_label_window_overlaps_test_span(horizon, seed):
    rng = np.random.default_rng(seed)
    n = 200
    X = pd.DataFrame(rng.standard_normal((n, 4)))
    groups = np.arange(n) + rng.integers(0, horizon + 1, size=n)

    cv = PurgedKFold(n_splits=6, embargo_pct=0.02)

    for train, test in cv.split(X, groups=groups):
        test_start = int(test.min())
        test_end = int(np.max(groups[test]))

        train_start = train
        train_end = groups[train]

        overlaps = (train_start <= test_end) & (train_end >= test_start)
        assert not overlaps.any()
```

추가:

```python
def test_embargo_pct_gte_one_rejected():
    with pytest.raises(ValueError, match="embargo_pct"):
        PurgedKFold(n_splits=5, embargo_pct=1.0)
```

---

## Phase 3 — `recommendation_engine.py` OOF-only 명시

### 현재 유지할 코드

```python
oof.iloc[test_idx] = prob
neutral_probs = oof.fillna(0.5).to_numpy(dtype=float)
```

### 추가할 반환 필드

```python
return {
    "model": final_model,
    "feature_cols": cols,
    "oof_probs": oof,
    "backtest_probs": neutral_probs,
    "backtest_probability_source": "OOF_ONLY_FILLED_0_5",
    "latest_prob": latest_prob,
    "latest_prob_used_for_backtest": False,
    "accuracy": ...,
    "auc": ...,
    "oof_coverage": coverage,
    "label_horizon_bars": horizon,
    "embargo_pct": embargo_pct,
    "embargo_samples": int(np.floor(len(X) * embargo_pct)),
}
```

### 테스트

```python
def test_backtest_uses_oof_probs_only(monkeypatch):
    captured = {}

    def fake_run(self, prices, signals):
        captured["signals_name"] = getattr(signals, "name", None)
        captured["signals_values"] = np.asarray(signals)
        return {
            "total_return_pct": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "sortino_ratio": 0.0,
            "profit_factor": 0.0,
            "n_trades": 0,
        }

    monkeypatch.setattr(Backtester, "run", fake_run)

    result = engine.evaluate_ticker("SYNTH", "S")

    assert result.backtest_honesty is not None
    assert result.screening_output_only is True
```

---

## Phase 4 — `backtest_honesty`를 live verdict에 연결

현재 `_verdict()`는 score와 validation checks만 본다. `backtest_honesty`가 `AMBER/FAIL`이어도 score와 pass_count가 충분하면 추천 후보가 될 수 있다.

### 조치

`_verdict()` 호출 전후로 live-review downgrade를 강제한다.

```python
def _apply_readiness_gate(verdict, label, honesty, model_stats, backtest):
    blocking = []

    if honesty is None or honesty.get("status") != "PASS":
        blocking.append("BACKTEST_HONESTY_NOT_PASS")

    if model_stats["accuracy"] < 0.50:
        blocking.append("ACCURACY_BELOW_50")

    if model_stats["auc"] < 0.50:
        blocking.append("AUC_BELOW_0_50")

    if int(backtest.get("n_trades", 0)) < 50:
        blocking.append("COMPLETED_TRADES_BELOW_50")

    if blocking:
        return "AMBER_WATCHLIST", "검증 미충족: 신규 자금 투입 금지", blocking

    return verdict, label, []
```

---

## Phase 5 — Cost / Slippage stress

현재 backtester는 단일 cost/slippage를 반영한다.  
실전 검토 후보 승격에는 3개 시나리오가 필요하다.

| Scenario | transaction_cost | slippage | 목적 |
|---|---:|---:|---|
| 1x | 기본값 | 기본값 | 정상 시장 |
| 2x | 2배 | 2배 | 유동성 약화 |
| 3x | 3배 | 3배 | stress pass 여부 |

### 산출 필드

```json
{
  "alpha_after_1x_cost": 2.35,
  "alpha_after_2x_cost": 1.10,
  "alpha_after_3x_cost": 0.41,
  "cost_stress_status": "PASS"
}
```

승격 조건:

```text
alpha_after_1x_cost > 0
alpha_after_3x_cost >= 0
```

---

## Phase 6 — CPCV / PBO / DSR 추가

기존 `PurgedKFold`는 빠른 OOF 생성용으로 유지한다.

추가:

```text
PurgedKFold = daily screening / OOF 생성
CombinatorialPurgedCV = live-review 승격 전 overfitting 진단
```

필드:

```json
{
  "cpcv_enabled": true,
  "cpcv_paths": 45,
  "cpcv_path_pass_rate": 0.64,
  "pbo": 0.18,
  "deflated_sharpe": 0.21
}
```

승격 기준:

```text
cpcv_path_pass_rate >= 60.00%
pbo <= 20.00%
deflated_sharpe > 0
```

---

## Phase 7 — Event / Sentiment PIT feature

LLM은 BUY 결정을 하면 안 된다.  
LLM은 `feature generator`와 `risk explainer`로만 사용한다.

필드:

```json
{
  "event_features": {
    "news_sentiment_1d": 0.18,
    "news_sentiment_5d": 0.11,
    "disclosure_risk_flag": false,
    "earnings_event_window": false,
    "available_at_safe": true,
    "source_count": 7,
    "llm_audit_path": "reports/audit/event_sentiment_005930.jsonl"
  }
}
```

필수 규칙:

```text
available_at <= prediction_time
feature_lag >= 1
LLM output audit required
No LLM verdict upgrade
```

---

## Phase 8 — Portfolio risk gate

단일 종목 점수는 position 결정이 아니다.

필드:

```json
{
  "portfolio_gate": {
    "max_position_pct": 10.0,
    "sector_cap_pct": 30.0,
    "single_name_risk": "PASS",
    "cvar_95": -3.2,
    "correlation_cluster": "semiconductor",
    "rebalance_allowed": false
  }
}
```

승격 조건:

```text
position_size <= max_position_pct
sector_exposure <= sector_cap_pct
CVaR within configured limit
correlation cluster concentration pass
```

---

## 9. 외부 기술 병합 요약

| Source/Topic | 병합 아이디어 | 적용 위치 |
|---|---|---|
| CPCV / PBO / DSR | 단일 backtest가 아니라 성과 분포 기반 검증 | `ml/cv.py`, `backtest_honesty.py` |
| LLM stock forecasting review | LLM은 sentiment/event feature와 risk explanation으로 제한 | `event_features.py`, `advisors/` |
| Sentiment with FinBERT/DeBERTa/RoBERTa | 뉴스·공시 감성 feature 추가 | `features/sentiment.py` |
| Treasury FS AI RMF | Model card, audit, accountability, resilience | `reports/model_cards/` |
| FINRA AI fraud warning | 수익 보장·자동매매 표현 금지 | dashboard/report wording |

---

## 10. 005930 현재 적용 판정

현재 업로드 JSON 기준:

| 항목 | 현재 | 목표 | Gap |
|---|---:|---:|---:|
| Raw Score | 91.88 | 참고값 | 점수 자체는 충분 |
| Accuracy | 49.00% | ≥ 52.00% | +3.00%p 필요 |
| AUC | 0.53 | ≥ 0.55 | +0.02 필요 |
| Alpha | -186.65%p | > 0.00%p | 구조적 개선 필요 |
| Completed Trades | 32 | ≥ 80 | +48건 필요 |
| OOF Coverage | 74.68% | ≥ 85.00% | +10.32%p 필요 |
| Cost stress | 미확인 | PASS | 추가 필요 |
| CPCV/PBO/DSR | 없음 | PASS | 추가 필요 |
| Paper trading | 없음 | 30~60일 | 추가 필요 |

판정:

```text
현재 상태: AMBER_WATCHLIST
다음 목표: PAPER_CANDIDATE
최종 목표: LIVE_REVIEW_CANDIDATE
```

---

## 11. 구현 순서

| Priority | 작업 | 파일 |
|---:|---|---|
| P0 | `PurgedKFold` overlap bug fix | `src/stock_rtx4060/ml/cv.py` |
| P0 | `embargo_pct >= 1` 거부 | `src/stock_rtx4060/ml/cv.py` |
| P0 | full no-leakage property test 추가 | `tests/test_purged_kfold.py` |
| P0 | OOF-only backtest source 필드 추가 | `src/stock_rtx4060/recommendation_engine.py` |
| P0 | `backtest_honesty != PASS` live downgrade | `src/stock_rtx4060/recommendation_engine.py` |
| P1 | `cv_gap` rename: `embargo_samples` | `recommendation_engine.py`, `backtest_honesty.py`, CLI |
| P1 | cost stress engine | `src/stock_rtx4060/backtest/` |
| P1 | CPCV/PBO/DSR module | `src/stock_rtx4060/ml/cv.py`, `backtest_honesty.py` |
| P2 | event/sentiment PIT feature | `src/stock_rtx4060/features/` |
| P2 | portfolio gate | `src/stock_rtx4060/portfolio/` |
| P2 | model card generator | `reports/model_cards/` |

---

## 12. 실행 명령

PowerShell:

```powershell
py -3.12 -m pytest tests\test_purged_kfold.py tests\test_walk_forward_purged.py tests\test_ml_hpo.py -q
py -3.12 -m pytest tests\test_dashboard_bridge.py -q
py -3.12 -m pytest tests\test_backtest_honesty.py tests\test_cost_stress.py tests\test_model_card.py -q
```

권장 self-test:

```powershell
.\.venv\Scripts\python.exe -m compileall main.py src tests
.\run.ps1 self-test
```

---

## 13. Acceptance Criteria

| No | 기준 | 합격 조건 |
|---:|---|---|
| 1 | API 유지 | `PurgedKFold(...).split(X, groups=...)` 계속 동작 |
| 2 | No leakage | train label window와 test span overlap 0건 |
| 3 | Embargo | test 직후 embargo rows가 train에서 제거 |
| 4 | OOF-only | backtest input source가 `OOF_ONLY_FILLED_0_5` |
| 5 | Honesty gate | `backtest_honesty != PASS`면 live-review 불가 |
| 6 | Cost stress | 1x/3x cost 후 alpha 계산 |
| 7 | CPCV/PBO/DSR | live-review 전 필수 진단 결과 생성 |
| 8 | Dashboard safety | `new_capital_allowed=false`, `broker_order_execution=false` 유지 |
| 9 | Model card | candidate별 근거·한계·blocking reasons 생성 |
| 10 | Wording | `walk-forward`, `TimeSeriesSplit(gap)`, `cv_gap` 혼선 제거 |

---

## 14. 최종 결론

STOCK·PRED를 실전 검토 가능 수준으로 올리는 핵심은 **모델 점수를 올리는 것이 아니라 검증 실패를 정직하게 차단하는 것**이다.

최종 병합 순서:

```text
1. PurgedKFold no-leakage patch
2. OOF-only backtest hard gate
3. backtest_honesty live gate 연결
4. cost/slippage stress
5. CPCV/PBO/DSR
6. regime + event/sentiment PIT feature
7. portfolio risk gate
8. model card + dashboard governance
```

현재 005930은 아직 `LIVE_REVIEW_CANDIDATE`가 아니다.

```text
현재: AMBER_WATCHLIST
허용: research / paper tracking
금지: 신규 자금 투입 / 자동매매 / broker order
```

---

## 15. References

1. arXiv 2605.05211, “A Review of Large Language Models for Stock Price Forecasting from a Hedge-Fund Perspective”  
   https://arxiv.org/abs/2605.05211

2. skfolio, “CombinatorialPurgedCV”  
   https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html

3. SSRN, “Backtest Overfitting in the Machine Learning Era”  
   https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376

4. arXiv 2602.00086, “Impact of LLMs news Sentiment Analysis on Stock Price Movement Prediction”  
   https://arxiv.org/abs/2602.00086

5. U.S. Treasury, “AI Risk Management Framework for Financial Services”  
   https://home.treasury.gov/news/press-releases/sb0401

6. FINRA, “Artificial Intelligence and Investment Fraud”  
   https://www.finra.org/investors/insights/artificial-intelligence-and-investment-fraud

7. scikit-learn, “Common pitfalls and recommended practices”  
   https://scikit-learn.org/stable/common_pitfalls.html

8. scikit-learn, “TimeSeriesSplit”  
   https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
