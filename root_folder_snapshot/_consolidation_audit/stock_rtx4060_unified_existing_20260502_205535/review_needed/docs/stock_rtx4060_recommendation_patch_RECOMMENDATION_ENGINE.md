# Recommendation Engine Patch

## 목적

이 패치는 `stock_rtx4060`에 직접 종목/ETF 후보를 추천하는 기능을 추가한다. 단, 출력은 `screening_output_only`이며 broker 주문, 자동매수, 개인 맞춤 투자 자문으로 사용하지 않는다.

## 추가 파일

| File | Purpose |
|---|---|
| `recommendation_engine.py` | Track-S / Track-L Top-N 추천 후보 스캐너, 다중 확인, Markdown/JSON 리포트 생성 |
| `RECOMMENDATION_ENGINE.md` | 기능 설명 및 실행 명령 |

## 변경 파일

| File | Change |
|---|---|
| `main.py` | `--recommend`, `--universe`, `--track`, `--top`, `--synthetic`, `--output-dir` CLI 옵션 추가 |

## 실행 예시

### 실데이터 후보 추천

```powershell
python main.py --recommend --track BOTH --universe AAPL,MSFT,NVDA,AMD,AVGO,GOOGL,AMZN,META,TSLA,QQQ,SPY --period 3y --top 10
```

### 단타 후보만 추천

```powershell
python main.py --recommend --track S --universe AAPL,NVDA,AMD,TSLA,QQQ --period 3y --top 5
```

### 장기 후보만 추천

```powershell
python main.py --recommend --track L --universe AAPL,MSFT,NVDA,AVGO,GOOGL,AMZN,SPY,QQQ,GLD --period 5y --top 5
```

### 설치/네트워크 없이 데모 검증

```powershell
python main.py --recommend --synthetic --universe SYNTH-A,SYNTH-B,SYNTH-C --top 5
```

## 알고리즘 요약

### Track-S 단타 점수

| Factor | Weight | 설명 |
|---|---:|---|
| Model Edge | 20.00 | XGBoost 최신 상승확률 |
| Trend / Regime | 20.00 | 20/50일 이동평균 및 20일 수익률 |
| Liquidity / Volume | 15.00 | 20일 평균 거래대금 및 volume ratio |
| Breakout | 15.00 | 20일 고점권/돌파 여부 |
| Backtest Sanity | 15.00 | Sharpe, MDD 허용 여부 |
| Risk Plan | 10.00 | TP2 +10.00%, stop -4.00%, Risk/Reward ≥2.00 |

### Track-L 장기 점수

| Factor | Weight | 설명 |
|---|---:|---|
| Quality Proxy | 20.00 | 200일선 기반 장기 추세 proxy |
| Earnings Proxy | 15.00 | 252일 수익률 proxy |
| Balance/Risk Proxy | 10.00 | ATR 기반 변동성 proxy |
| Valuation Proxy | 15.00 | 52주 고점 대비 과열/조정 proxy |
| Structural Theme | 10.00 | 외부 theme/fundamental source 연결 전 neutral |
| Trend | 15.00 | 60일 momentum |
| Model Edge | 10.00 | XGBoost 방향성 확률 |
| Risk Review | 10.00 | 장기 MDD 및 R/R 확인 |

## 다중 확인 Gate

| Check | 사용처 | Fail 시 처리 |
|---|---|---|
| DATA_ROWS | S/L | `RED_DATA_INSUFFICIENT` |
| LIQUIDITY | S/L | `AMBER` 또는 점수 감점 |
| MODEL_EDGE | S/L | `AMBER` 또는 점수 감점 |
| BACKTEST_SANITY | S/L | `AMBER` 또는 점수 감점 |
| RISK_PLAN | S/L | `ZERO_RISK_PLAN_FAILED` |
| TRACK_SCORE | S/L | Green/Amber/Red 판정 |

## 출력물

실행 후 `recommendation_reports/`에 아래 파일이 생성된다.

- `recommendations_YYYYMMDD_HHMMSS.md`
- `recommendations_YYYYMMDD_HHMMSS.json`

## 운영 경계

- `ELIGIBLE_RECOMMENDATION`과 `ACCUMULATE_RECOMMENDATION`은 실제 매수 지시가 아니다.
- 모든 후보는 수동 승인, broker/account rule, 세금/규정 확인 후에만 검토 가능하다.
- margin, options, 0DTE, leveraged ETF, penny stock은 이 패치에서도 활성화하지 않는다.
