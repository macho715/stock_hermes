# 2× GitHub / Official Docs Cross-Check — 2026

| Source | 확인한 구현/인터페이스 | v2 반영 | 보류 |
|---|---|---|---|
| scikit-learn TimeSeriesSplit | time-ordered split, `gap` parameter | `gap=horizon` 기본 적용으로 horizon overlap leakage 축소 | purged group split 전용 라이브러리 의존은 보류 |
| XGBoost GPU docs | XGBoost 2.x: `device="cuda"`, `tree_method="hist"` | version-aware parameter builder와 CPU fallback | 컨테이너 GPU 부재로 실제 CUDA benchmark는 보류 |
| vectorbt | pandas/NumPy/Numba 기반 vectorized backtesting, walk-forward/label tools | pandas/NumPy 벡터화와 OOF signal backtest 설계 채택 | vectorbt dependency 추가는 보류 |
| Backtesting.py | event/vectorized backtesting, money management, SL/TP | event exit priority, cost/slippage, SL/TP, final liquidation 반영 | plotting/optimizer dependency 보류 |
| skfolio | scikit-learn-compatible portfolio risk management, cross-validation/stress-test | OOF coverage와 robust validation 관점 반영 | MVO/HRP portfolio optimizer는 scope 밖이라 보류 |
| FinRL-X | modular, deployment-consistent, weight-centric trading architecture; disclaimer | data/model/backtest/risk/report 분리와 broker-free boundary 유지 | broker execution layer는 out of scope |

## Adopted design choices

1. Backtest는 최종 모델이 과거 train-window를 다시 예측하지 않도록 OOF 확률만 사용한다.
2. 후보 추천은 score만 보지 않고 `RISK_PLAN`, `OOF_COVERAGE`, `BACKTEST_SANITY`, `AUTOMATION_BOUNDARY`를 별도 Gate로 출력한다.
3. Track-S는 R/R ≥ 2와 월간 손실 제한을 우선한다.
4. Track-L은 Score ≥ 80과 단일 종목 상한 12% 운영 전제를 유지한다.
5. GPU는 사용 가능한 경우 활성화하되, 실패 시 CPU 모드로 안전 fallback한다.
