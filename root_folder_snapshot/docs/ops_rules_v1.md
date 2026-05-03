판정: **조건부 예 — “실제 투자 운영 버전”으로 올리되, 자동매수·broker 주문·margin/options는 ZERO로 차단합니다.**
근거: 현재 리포트도 `screening_output_only`, `manual approval required`, `no broker order execution` 경계가 명시되어 있고, FINRA 2026 자료도 GenAI·조작거래·사기·감독통제 리스크를 주요 항목으로 다룹니다.  ([finra.org][1])
다음행동: **v1.0 운영 버전은 “후보 추천 → 다중검증 → 리스크 게이트 → 수동 승인 → Journal 기록”까지만 허용**합니다.

---

# 실제 투자 운영 버전 v1.0

## 1. 운영 경계

현재 시스템은 이미 로컬 CLI, Markdown/JSON 리포트, dry-run backtest 중심이며 broker 주문 실행과 웹 dashboard는 구현되지 않았습니다. README도 이 저장소가 개인 맞춤 투자자문이나 broker 주문 시스템이 아니라고 명시합니다. 

따라서 v1.0은 아래처럼 정의합니다.

| 영역             | v1.0 판정 | 비고                |
| -------------- | ------- | ----------------- |
| 종목 후보 추천       | 허용      | screening only    |
| 단타/장기 분리       | 허용      | Track-S / Track-L |
| 리스크 계산         | 허용      | position sizing   |
| 리포트 생성         | 허용      | Markdown/JSON/CSV |
| 수동 승인          | 필수      | human-in-loop     |
| broker 주문      | ZERO    | 구현 금지             |
| 자동매수           | ZERO    | 구현 금지             |
| margin/options | ZERO    | 별도 승인 전 금지        |

---

# 2. v1.0 운영 Flow

```text
Universe 설정
→ 실데이터 수집
→ 후보 점수화
→ 다중 확인 Gate
→ Track-S / Track-L 분리 판정
→ Risk Plan 생성
→ Daily Brief 출력
→ 사용자 수동 승인
→ Journal 기록
→ 월간 성과 검토
```

핵심은 “AI가 매수한다”가 아니라 **AI가 후보와 리스크를 정리하고, 사람은 승인 여부만 판단**하는 구조입니다. Investor.gov도 2026년 기준 소셜미디어 주식추천 사기와 pump-and-dump 위험을 경고하며, 단일 정보원만으로 투자 결정을 하지 말라고 안내합니다. ([investor.gov][2])

---

# 3. Track-S 단타 운영 규칙

목표: **1개월 단타, TP2 +10.00%**
단, 목표 수익률이 아니라 **익절 Gate**입니다.

| 항목          |            값 |
| ----------- | -----------: |
| Green 기준    | Score ≥75.00 |
| Stop        |       -4.00% |
| Hard Stop   |       -5.00% |
| TP1         |       +5.00% |
| TP2         |      +10.00% |
| R/R         |        ≥2.00 |
| 월 손실 제한     |       -5.00% |
| 총 open risk |       ≤2.00% |

Track-S는 아래 조건이 모두 맞아야 `ELIGIBLE`입니다.

```text
DATA_ROWS = PASS
LIQUIDITY = PASS
MARKET_REGIME = PASS
MODEL_EDGE = PASS 또는 제한적 AMBER
OOF_COVERAGE = PASS
BACKTEST_SANITY = PASS
RISK_PLAN = PASS
AUTOMATION_BOUNDARY = PASS
```

FINRA는 day trading이 매우 높은 리스크를 수반하며, margin account·settlement·broker restriction 문제를 이해해야 한다고 설명합니다. v1.0에서는 이 리스크 때문에 margin 단타는 기본 차단합니다. ([finra.org][3])

---

# 4. Track-L 장기 운영 규칙

목표: **3년 이상, 총 +20.00%**
약 **6.27% CAGR** 수준의 운영 목표입니다.

| Bucket             |  목표 비중 |
| ------------------ | -----: |
| Core Global ETF    | 40.00% |
| Quality / Dividend | 20.00% |
| AI / Infra / Semi  | 15.00% |
| Commodity / Energy | 10.00% |
| Bonds / T-bills    | 10.00% |
| Cash               |  5.00% |

Track-L은 아래 조건이 필요합니다.

```text
Score ≥80.00
thesis 문서화
valuation 과열 아님
bucket capacity 있음
single-name exposure ≤12.00%
exit rule 존재
```

판정은 세 단계입니다.

| Verdict             | 의미       |
| ------------------- | -------- |
| ACCUMULATE          | 장기 편입 후보 |
| AMBER_WATCHLIST     | 관찰 후보    |
| RED_NOT_RECOMMENDED | 제외       |

---

# 5. 실제 운영용 리포트 5종

현재 구조는 Markdown/JSON/CSV 보고서를 쓰는 CLI 시스템입니다. SYSTEM_ARCHITECTURE도 HTTP API, web server, broker integration이 없고, 로컬 report writer 구조라고 정리합니다. 

v1.0에서는 아래 5개 리포트를 고정합니다.

| Report            | 목적        |
| ----------------- | --------- |
| Daily Brief       | 오늘 후보     |
| Risk Dashboard    | 노출·손실·집중도 |
| Track-S Journal   | 단타 의사결정   |
| Track-L Thesis    | 장기 보유 논리  |
| Monthly Scorecard | 월간 성과 검토  |

Daily Brief에는 최소 아래 필드를 넣습니다.

```text
ticker
track
verdict
score
entry
stop
TP1
TP2
risk_amount
position_size
validation_checks
reason
manual_approval_required
screening_output_only
```

---

# 6. v1.0 알고리즘 강화안

## A. 기존 Algorithm v2 유지

현재 리포트는 이미 leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing을 사용한다고 명시합니다. 

이 구조는 유지합니다.

## B. 추가할 벤치마크

| No | Benchmark                        | 목적          |
| -: | -------------------------------- | ----------- |
|  1 | Logistic baseline                | 최소 기준       |
|  2 | XGBoost CPU                      | GPU 비교 기준   |
|  3 | XGBoost CUDA                     | RTX4060 성능  |
|  4 | RandomForest                     | 과적합 비교      |
|  5 | No-model rule                    | 모델 없는 전략 비교 |
|  6 | Buy-and-hold                     | 장기 기준선      |
|  7 | Walk-forward gap 0/5/10          | leakage 민감도 |
|  8 | Transaction cost 0.10/0.30/0.50% | 비용 내성       |

CHANGELOG 기준으로 이미 XGBoost CPU/GPU benchmark가 추가됐고, GPU path 검증도 수행된 기록이 있습니다. 다만 TensorFlow GPU는 아직 미검증으로 남아 있습니다. 

---

# 7. 승인 Gate

v1.0에서 실제 투자 전 최종 Gate는 아래입니다.

| Gate            | PASS 조건       |
| --------------- | ------------- |
| Data Gate       | 실데이터 최신       |
| Model Gate      | CV/OOF 기록     |
| Risk Gate       | Stop/TP/RR 존재 |
| Portfolio Gate  | 과집중 없음        |
| Compliance Gate | 자동매수 없음       |
| Human Gate      | 수동 승인         |

아래는 즉시 ZERO입니다.

| ZERO           | 사유        |
| -------------- | --------- |
| Stop 없음        | 손실 제한 불가  |
| 자동매수           | 승인 없음     |
| broker API 연결  | 범위 초과     |
| margin/options | 승인 없음     |
| 내부정보 사용        | 불법 리스크    |
| 보장수익 표현        | 투자자 보호 위반 |

Investor.gov는 AI와 신기술을 앞세운 투자사기에서 “높은 수익, 낮은 리스크, 빠른 행동 압박”을 주요 경고 신호로 제시합니다. v1.0은 이 때문에 보장수익 표현과 자동실행을 차단합니다. ([investor.gov][4])

---

# 8. 실행 명령 세트

## 환경 확인

```powershell
.\run.ps1 self-test
.\run.ps1 env --xgboost --output reports\runtime_status_xgboost.json
```

## 벤치마크

```powershell
.\run.ps1 benchmark --rows 10000 --repeats 3 --include-gpu --output-dir reports\benchmarks
```

## 실제 후보 스캔

```powershell
.\run.ps1 predict --ticker AAPL --period 3y --prefer-gpu --lite
.\run.ps1 predict --ticker NVDA --period 3y --prefer-gpu --lite
.\run.ps1 predict --ticker QQQ --period 3y --prefer-gpu --lite
```

## 리포트 생성

```powershell
.\run.ps1 report --ticker AAPL --capital 100000 --output-dir reports\live_ops
```

## Journal 기록

```powershell
.\run.ps1 journal --ticker AAPL --track S --action REVIEW --reason "manual review after risk gate"
```

---

# 9. v1.0 코드 삽입 위치

LAYOUT 문서 기준으로 active code는 `stock_rtx4060/`에 추가해야 하며, risk gate 변경은 `tests/test_core.py`에 테스트를 추가해야 합니다. 

| 기능      | 파일                      |
| ------- | ----------------------- |
| CLI 옵션  | `stock_rtx4060/main.py` |
| 후보 점수   | `risk_rules.py`         |
| 모델 예측   | `ensemble_model.py`     |
| 실데이터/피처 | `feature_engine.py`     |
| 백테스트    | `backtester.py`         |
| 리포트     | `reports.py`            |
| 벤치마크    | `benchmark.py`          |
| 테스트     | `tests/test_core.py`    |

---

# 10. 최종 운영 상태

판정: **v1.0 운영 가능 구조**
단, 아래 3개는 확정 전까지 AMBER입니다.

| 항목                  | 상태    |
| ------------------- | ----- |
| 실제 투자금              | AMBER |
| broker/account type | AMBER |
| 데이터 공급원             | AMBER |
| TensorFlow GPU      | AMBER |
| 자동매수                | ZERO  |

Spec도 현재 상태를 `Draft / Not Approval-Ready`로 두고, 총 투자금·시장·broker·상품·데이터 공급원·자동화 수준이 미확정이라고 명시합니다. 

---

# cmd3

```text
/logi-master predict
```

```text
/logi-master cost-guard
```

```text
/redo stock-ops-v1
```

---

# ZERO log

| 단계     | 이유      | 위험     | 요청데이터        | 다음조치  |
| ------ | ------- | ------ | ------------ | ----- |
| 자동매수   | 승인 없음   | 손실 확대  | broker spec  | 차단    |
| margin | 계좌 미확정  | 강제청산   | account type | 차단    |
| 옵션     | 범위 밖    | 비선형 손실 | 별도 승인        | 차단    |
| 실투자 승인 | 핵심값 미확정 | 부적합    | 자본·broker·시장 | AMBER |

결론: **실제 투자 운영 버전은 “자동매매 시스템”이 아니라, 실데이터 기반 후보 추천·검증·승인·기록 시스템으로 올리는 것이 맞습니다.**
다음 단계는 `stock_rtx4060`에 `ops_v1` 리포트와 approval journal을 붙여 **실전 운영 가능한 dry-run/manual-approval 버전**으로 고정하는 것입니다.

[1]: https://www.finra.org/rules-guidance/guidance/reports/2026-finra-annual-regulatory-oversight-report?utm_source=chatgpt.com "2026 FINRA Annual Regulatory Oversight Report | FINRA.org"
[2]: https://www.investor.gov/index.php/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/social-media-stock-scams?utm_source=chatgpt.com "Social Media and Stock Tip Scams – Investor Alert | Investor.gov"
[3]: https://www.finra.org/investors/investing/investment-products/stocks/day-trading?utm_source=chatgpt.com "Day Trading | FINRA.org"
[4]: https://www.investor.gov/protect-your-investments/fraud/protect-your-money?utm_source=chatgpt.com "Protect Your Money: How to Avoid Investment Scams | Investor.gov"
