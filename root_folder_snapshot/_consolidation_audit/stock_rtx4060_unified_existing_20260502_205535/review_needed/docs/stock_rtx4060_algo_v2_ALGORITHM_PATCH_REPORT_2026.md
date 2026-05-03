# Algorithm Patch Report 2026 — stock_rtx4060 v2

## 1. 기준 입력

- 기준 ZIP: `stock_rtx4060_recommendation_patch.zip`
- 기준 문서: `plan.md`, `plan_rev.md`, `uiux.md`
- 범위: Track-S 단타, Track-L 장기, Risk Gate, GPU 예측/백테스트, 리포트 출력
- 제외: 자동매매, broker API 주문, margin/options/0DTE, 개인 맞춤 투자자문

## 2. 알고리즘 개선 내역

| 영역 | 기존 문제 | v2 패치 |
|---|---|---|
| CV/검증 | TimeSeriesSplit를 쓰지만 horizon overlap과 train-window 확률 누수 가능 | `gap=horizon` 기본 적용, OOF가 없는 구간은 0.5 중립 신호로 처리 |
| 피처 | 일부 지표는 단순 rolling 중심, 당일 feature/label 경계가 약함 | 모든 feature를 기본 1-bar lag, Wilder ATR/RSI/ADX, 변동성/드로다운/유동성/캔들 구조 피처 추가 |
| 백테스트 | Kelly 기반 capital sizing 중심 | Kelly + fixed risk-per-trade + max position cap + monthly stop + cost/slippage + final liquidation |
| Risk plan | 고정 stop/TP 구조 | ATR-adjusted stop/TP, R/R 유지, risk budget와 suggested quantity 산출 |
| 추천 점수 | score 중심 | expected value, market regime, OOF coverage, backtest sanity, automation boundary validation 추가 |
| GPU | XGBoost API 버전 차이 리스크 | XGBoost 2.x `device=cuda`, 구버전 `gpu_hist`/CPU fallback 분기 |
| 리포트 | 단순 후보표 | Score, Prob, EV%, Entry/Stop/TP2, R/R, Risk%, MaxPos%, Qty, validation details 출력 |

## 3. 검증 결과

```text
python main.py --test
PASS test_feature_engine_basic
PASS test_feature_engine_edge
PASS test_backtester_basic
PASS test_kelly_criterion
PASS test_recommendation_engine_synthetic
PASS test_ensemble_leak_safe_cv
self-test: 6/6 passed

pytest -q
12 passed

python -m py_compile *.py
passed
```

## 4. Synthetic benchmark

```text
python main.py --benchmark --synthetic --benchmark-rows 1200 --universe SYNTH-A,SYNTH-B,SYNTH-C --output-dir reports
```

| Metric | Value |
|---|---:|
| Input rows | 1200 |
| Feature rows | 942 |
| Feature columns | 81 |
| Feature seconds | 0.1190 |
| Model seconds | 15.1569 |
| Backtest seconds | 0.1015 |
| Recommendation smoke seconds | 8.6024 |
| Total seconds | 23.9942 |
| CV accuracy mean | 0.5504 |
| CV AUC mean | 0.5574 |
| Backtest total return | 0.68% |
| Backtest Sharpe | 0.216 |
| Backtest MDD | 1.76% |
| Trades | 46 |
| Profit factor | 1.192 |

## 5. 환경 한계

현재 컨테이너에는 RTX 4060 GPU, `nvidia-smi`, TensorFlow가 노출되어 있지 않았습니다. 따라서 실제 GPU 가속 수치는 포함하지 않았고, CPU/synthetic benchmark와 WSL2/CUDA 재실행 명령을 포함했습니다.

## 6. 실행 명령

```powershell
python main.py --test
python main.py --benchmark --synthetic --benchmark-rows 1200 --universe SYNTH-A --output-dir reports
python main.py --recommend --synthetic --universe SYNTH-A --track BOTH --top 2 --output-dir recommendation_reports
```
