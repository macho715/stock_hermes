# 투자 알고리즘 A/B/C Python 스크립트

## 구성

| 파일 | 목적 | 주요 산출물 |
|---|---|---|
| `algos/a_regime_hrp_hmv_cvt.py` | Regime-aware HRP/HMV-CVT core allocator | `latest_weights.csv`, `regime_probabilities.csv`, `orders.csv`, `metrics.json` |
| `algos/b_meta_temporal_conformal_gate.py` | Meta-label + Temporal Conformal Gate 신호 필터 | `latest_signals.csv`, `latest_weights.csv`, `gate_diagnostics.csv`, `metrics.json` |
| `algos/c_decision_focused_multi_period_optimizer.py` | Decision-focused Multi-period Optimizer | `latest_multi_period_plan.csv`, `latest_weights.csv`, `optimizer_diagnostics.csv`, `metrics.json` |
| `algos/common.py` | 공통 데이터 로딩, HRP, 비용, 성과지표 유틸 | 공통 함수 |
| `examples/run_all_demo.py` | synthetic ETF-like 데이터 생성 후 A/B/C 일괄 실행 | `demo_output/*` |

## 설치

```bash
cd invest_algos
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 공통 입력 형식

기본 입력은 wide price CSV입니다.

```csv
Date,SPY,QQQ,TLT,GLD
2024-01-02,475.00,400.00,95.00,185.00
2024-01-03,476.20,402.10,94.80,186.30
```

- `Date` 컬럼 필수 권장.
- 나머지 컬럼은 자산 ticker 또는 내부 asset code.
- 가격은 point-in-time 기준이어야 합니다.
- corporate action, delisting, timezone, stale price는 외부 데이터 파이프라인에서 먼저 정리해야 합니다.

## A. Regime-aware HRP/HMV-CVT

```bash
python algos/a_regime_hrp_hmv_cvt.py \
  --prices data/prices.csv \
  --outdir output/a \
  --lookback 252 \
  --rebalance-days 5 \
  --n-regimes 3 \
  --target-vol 0.10 \
  --max-weight 0.25 \
  --cost-bps 5
```

### 핵심 로직

1. rolling return/vol/drawdown/dispersion feature 생성.
2. GaussianMixture로 regime probability 추정.
3. regime probability로 `mu_hat`, `Sigma_hat`를 가중 결합.
4. HRP weight와 constrained min-variance weight를 blend.
5. transaction cost, CVaR penalty, turnover cap, conditional volatility target을 반영해 최종 weight 산출.

### 주요 파라미터

| 파라미터 | 기본값 | 설명 |
|---|---:|---|
| `--lookback` | 252 | regime/covariance 추정 window |
| `--n-regimes` | 3 | regime 수 |
| `--target-vol` | 0.10 | 연율 목표 변동성 |
| `--hmv-blend` | 0.30 | HRP와 min-variance blend 비율 |
| `--turnover-cap` | 0.25 | 리밸런싱당 총 turnover 상한 |
| `--cost-bps` | 5.00 | weight turnover 1.00당 비용 bps |

## B. Meta-label + Temporal Conformal Gate

가격 CSV에서 feature/primary score를 자동 생성하는 방식:

```bash
python algos/b_meta_temporal_conformal_gate.py \
  --prices data/prices.csv \
  --outdir output/b \
  --horizon 5 \
  --alpha 0.10 \
  --meta-threshold 0.60 \
  --calibration-window 100
```

외부 alpha model의 long panel을 직접 넣는 방식:

```bash
python algos/b_meta_temporal_conformal_gate.py \
  --panel data/alpha_panel.csv \
  --outdir output/b
```

`alpha_panel.csv` 최소 컬럼:

```csv
Date,Asset,primary_score,fwd_return,feature_1,feature_2
2024-01-02,SPY,0.0040,0.0061,1.20,0.30
```

- `primary_score`: H-day expected return 또는 directional score.
- `fwd_return`: H-day realized return. 없으면 `meta_label`을 직접 제공.
- `meta_label`: post-cost로 primary signal이 맞았는지 여부.

### 핵심 로직

1. primary signal과 realized forward return으로 meta-label 생성.
2. LogisticRegression meta model로 post-cost signal validity probability 산출.
3. calibration window에서 conformal residual quantile 산출.
4. `p_meta >= threshold` 및 `lower_bound > cost + min_edge` 조건을 동시에 만족할 때만 trade.
5. 통과 신호를 volatility-adjusted weight로 변환.

## C. Decision-focused Multi-period Optimizer

```bash
python algos/c_decision_focused_multi_period_optimizer.py \
  --prices data/prices.csv \
  --outdir output/c \
  --lookback 252 \
  --rebalance-days 5 \
  --horizon 4 \
  --gamma 0.97 \
  --risk-aversion 5 \
  --turnover-penalty 25
```

외부 one-step forecast CSV를 넣는 방식:

```bash
python algos/c_decision_focused_multi_period_optimizer.py \
  --prices data/prices.csv \
  --predictions data/predicted_returns.csv \
  --outdir output/c
```

`predicted_returns.csv` 형식:

```csv
Date,SPY,QQQ,TLT,GLD
2024-01-02,0.0020,0.0030,0.0010,0.0015
```

### 핵심 로직

1. H-step expected return path 생성 또는 외부 forecast 사용.
2. 각 horizon step별 budget, max weight, turnover budget, target vol constraint 적용.
3. 목적함수는 expected return - risk penalty - transaction cost - CVaR penalty.
4. 첫 step weight만 실행하고 다음 rebalance에서 다시 최적화하는 MPC 구조.
5. `--tune` 사용 시 MSE가 아니라 realized portfolio utility 기준으로 risk/turnover penalty를 선택.

## Demo 실행

```bash
cd invest_algos
python examples/run_all_demo.py
```

생성 위치:

```text
invest_algos/examples/data/demo_prices.csv
invest_algos/demo_output/a_regime_hrp_hmv_cvt/
invest_algos/demo_output/b_meta_temporal_conformal_gate/
invest_algos/demo_output/c_decision_focused_mpo/
invest_algos/demo_output/demo_summary.json
```

## 운영 Guardrail

- 본 스크립트는 주문 실행기가 아니라 research/paper-trading용 산출기입니다.
- EMS/Broker 연결 전 pre-trade risk, approval, audit log, kill switch를 별도 구현해야 합니다.
- `cost_bps`는 임시 단순 비용입니다. 실제 운영에서는 fee, spread, slippage, market impact, borrow/locate fee를 분리해야 합니다.
- Backtest 결과는 synthetic/demo 또는 입력 데이터 품질에 종속됩니다. 실투입 전 walk-forward, purged split, CPCV, DSR/PBO, capacity 검증이 필요합니다.
- Short book은 borrow/locate 데이터 없이는 제한해야 하며, `B`는 기본값이 long-only입니다.
