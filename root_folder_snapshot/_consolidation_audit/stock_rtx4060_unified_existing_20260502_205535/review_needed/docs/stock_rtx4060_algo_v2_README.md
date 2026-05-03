# stock_rtx4060 Algorithm v2

목적: 업로드된 `stock_rtx4060_recommendation_patch.zip`를 기준으로 Track-S / Track-L / Risk Gate / RTX 4060 실행환경을 유지하면서 알고리즘을 개선한 패치 버전입니다.

## 핵심 변경

- Leak-safe Walk-Forward CV: `TimeSeriesSplit(gap=horizon)` 기본 적용
- Out-of-fold backtest: 학습 구간을 최종 모델 확률로 채우지 않고 0.5 중립 신호 처리
- Feature Engine v2: 1-bar lag feature, Wilder RSI/ATR/ADX, 변동성·드로다운·유동성·캔들 구조 피처 포함
- Backtester v2: fractional Kelly + fixed risk-per-trade sizing + max position cap + cost/slippage + monthly loss stop
- Recommendation Engine v2: ATR 기반 stop/TP, expected value, market regime, OOF coverage, GREEN/AMBER/RED/ZERO validation
- GPU path: XGBoost 2.x는 `device="cuda"` + `tree_method="hist"`, 구버전은 fallback 처리
- Safety boundary: broker order execution 없음. 결과는 `screening_output_only`입니다.

## 설치

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

WSL2/CUDA GPU 경로:

```powershell
pip install -r requirements-gpu-wsl2.txt
```

## 검증

```powershell
python main.py --test
pytest -q
python -m py_compile *.py
```

## 벤치마크

```powershell
python main.py --benchmark --synthetic --benchmark-rows 1200 --universe SYNTH-A --output-dir reports
```

## 추천 후보 스캐너

오프라인/데모:

```powershell
python main.py --recommend --synthetic --universe SYNTH-A --track BOTH --top 2 --output-dir recommendation_reports
```

실데이터, yfinance 사용:

```powershell
python main.py --recommend --universe AAPL,MSFT,NVDA,QQQ,SPY --track BOTH --period 3y --top 5
```

GPU XGBoost 시도:

```powershell
python main.py --recommend --universe AAPL,NVDA,QQQ --track BOTH --period 3y --top 5 --model-kind auto --xgb-device cuda
```

## 단일 티커 예측 파이프라인

```powershell
python main.py --ticker AAPL --period 5y --horizon 5
python main.py --ticker NVDA --period 3y --horizon 20 --model-kind auto
```

## 주의

이 코드는 리서치와 의사결정 보조용입니다. 자동매매, 브로커 주문, 개인 맞춤 투자자문을 수행하지 않습니다. 과거 백테스트 성과는 미래 수익을 보장하지 않습니다.
