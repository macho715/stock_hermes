판정: **AMBER — 1개월 +10.00% 단타 목표는 공격적이고, 3년 +20.00% 장기 목표는 구조화할 수 있습니다.**
근거: 2026.04 자료 기준, BlackRock은 AI·지정학·에너지 충격으로 시장이 “active + plan B”를 요구한다고 봅니다. Vanguard는 미국 주식 밸류에이션이 여전히 장기 fair value보다 높아 기대수익률을 현실적으로 설정해야 한다고 명시합니다. FINRA도 2026.06.04부터 day trading margin 체계가 바뀌지만, margin 단타는 여전히 고위험이라고 경고합니다. ([BlackRock][1])
다음 행동: **단타 Track-S와 장기 Track-L을 완전히 분리**하고, 동일 계좌 안에서도 자금·룰·손절·리밸런싱·리포트를 별도로 운영하십시오.

---

# Exec

| 구분         |  설계 판정 |            목표 | 핵심 전략                                     | 금지                                  |
| ---------- | -----: | ------------: | ----------------------------------------- | ----------------------------------- |
| Track-S 단타 | 조건부 가능 |   1개월 +10.00% | 이벤트·모멘텀·유동성 기반, 손실 제한형                    | 무손절, 과도한 margin, 0DTE/options 초보 진입 |
| Track-L 장기 |     가능 | 3년 이상 +20.00% | Core ETF + Quality/Growth/AI/Commodity 선별 | 단일 테마 몰빵, 고평가 추격매수                  |
| 공통         |  AMBER |      원금 보전 우선 | 룰 기반 투자 OS                                | 예측값만 믿고 자동매매                        |

**중요:** 장기 +20.00%는 3년 총수익률 기준이면 약 **6.27% CAGR**입니다. 단타 +10.00%/월은 연 환산으로 매우 공격적이므로 “목표”가 아니라 **익절 Gate**로만 취급해야 합니다.

---

# EN Sources ≤3

| No | Source                                   |       Date | 핵심 시사점                                                                                                            |
| -: | ---------------------------------------- | ---------: | ----------------------------------------------------------------------------------------------------------------- |
|  1 | BlackRock Q2 2026 Global Outlook         | 2026.04.22 | AI capex, 지정학, 에너지 충격, 금리 기대 변화가 시장을 지배. broad diversification만으로는 부족하고 active view와 plan B가 필요. ([BlackRock][1])  |
|  2 | Vanguard Capital Markets Model Forecasts | 2026.04.22 | 2026 Q1 이후 기대수익률은 일부 개선됐지만, 미국 주식은 여전히 장기 fair value보다 높음. 단기 밸류에이션 타이밍은 신뢰도가 낮음. ([corporate.vanguard.com][2])     |
|  3 | FINRA Intraday Margin Requirements       | 2026.04.20 | 2026.06.04부터 PDT/$25,000 요건을 intraday margin 방식으로 대체. 단, frequent margin trading은 여전히 high-risk. ([finra.org][3]) |

---

# 전체 투자 OS 구조

## 1) 계좌/자금 분리

**가정:** 총 투자금 100,000.00 AED 기준. 실제 금액이 다르면 비율만 적용.

| No | Track             | Allocation |         Value |         목표 | Max Loss Rule           | Evidence           |
| -: | ----------------- | ---------: | ------------: | ---------: | ----------------------- | ------------------ |
|  1 | Track-S 단타        |     20.00% | 20,000.00 AED |  월 +10.00% | 월 -5.00% 도달 시 거래 중단     | FINRA margin risk  |
|  2 | Track-L 장기        |     75.00% | 75,000.00 AED | 3년 +20.00% | 분기 -12.00% 이상이면 리밸런싱 검토 | Vanguard/BlackRock |
|  3 | Cash / Dry Powder |      5.00% |  5,000.00 AED |      기회 대응 | 단타 손실 보전용 사용 금지         | Risk buffer        |

**원칙:**
단타 손실이 장기 포트폴리오를 침식하면 시스템 실패입니다. 단타 계좌는 별도 broker sub-account 또는 별도 portfolio tag로 운영하십시오.

---

# Track-S: 단타 투자 구조 — 1개월 +10.00%

## A. 단타의 역할

단타는 “예측”보다 **확률이 좋은 상황만 기다리는 execution game**입니다.
목표는 매달 반드시 +10.00%가 아니라, 조건이 충족될 때만 **+10.00%까지 열어두고 손실을 작게 자르는 구조**입니다.

## B. 투자 Universe

| No | 조건     | 기준                                                     |
| -: | ------ | ------------------------------------------------------ |
|  1 | 유동성    | 일평균 거래대금 충분, 스프레드 좁은 종목/ETF                            |
|  2 | 가격 변동성 | 20일 ATR이 너무 낮지 않은 종목                                   |
|  3 | 테마     | AI, 반도체, 전력/인프라, commodity exporter, 에너지, 방산, 금리 민감 섹터 |
|  4 | 제외     | 거래정지 위험, penny stock, 유동성 부족, 공시 불투명, 급등 후 거래량 붕괴      |

BlackRock은 2026년 시장을 AI mega force, 지정학, 에너지 공급 충격, commodity exporter 선호 관점으로 보고 있습니다. 단타 Universe도 이 테마에서 유동성이 높은 종목만 고르는 방식이 적합합니다. ([BlackRock][1])

## C. 단타 진입 Score

**총점 100.00점, 75.00점 이상만 진입.**

| No | Factor              | Weight | Rule                                    |
| -: | ------------------- | -----: | --------------------------------------- |
|  1 | Market Regime       |  20.00 | 지수 상승 추세 또는 섹터 강세일 때만 Long              |
|  2 | Relative Strength   |  20.00 | 대상 종목이 지수/섹터 대비 20일 수익률 우위              |
|  3 | Volume Expansion    |  15.00 | 거래량 20일 평균 대비 1.50배 이상                  |
|  4 | Breakout / Pullback |  15.00 | 20일 신고가 돌파 또는 상승 추세 눌림목                 |
|  5 | Catalyst            |  15.00 | 실적, 수주, 정책, AI capex, commodity shock 등 |
|  6 | Risk/Reward         |  15.00 | 목표 +10.00%, 손절 -4.00% 이상 구조 가능          |

## D. 단타 Entry / Exit Rule

| 구분            | Rule                             |
| ------------- | -------------------------------- |
| Entry 1       | 종가 기준 20일 고점 돌파 + 거래량 1.50배 이상   |
| Entry 2       | 강세 섹터 내 5일선 회복 + 전일 고점 돌파        |
| Initial Stop  | -4.00%                           |
| Hard Stop     | -5.00% 초과 손실 금지                  |
| Take Profit 1 | +5.00%에서 50.00% 익절               |
| Take Profit 2 | +10.00%에서 잔여 익절                  |
| Time Stop     | 20거래일 내 +3.00% 미만이면 청산           |
| Trailing Stop | +6.00% 도달 후 고점 대비 -3.00% 이탈 시 청산 |

### 단타 기대값 Gate

예시: 목표 +10.00%, 손절 -4.00%, 왕복 비용 0.40% 가정.

| 항목                  |      값 |
| ------------------- | -----: |
| Win Net             | +9.60% |
| Loss Net            | -4.40% |
| Break-even Win Rate | 31.43% |

즉, 이 구조는 승률이 31.43%만 넘어도 수학적으로는 버틸 수 있습니다. 하지만 실제 시장에서는 슬리피지, gap down, 심리 오류가 있으므로 운영 기준은 **실전 승률 45.00% 이상**을 요구하십시오.

## E. 단타 Position Sizing

|            자금 |            1회 Risk |    손절폭 |       1회 포지션 |
| ------------: | -----------------: | -----: | -----------: |
| 20,000.00 AED | 1.00% = 200.00 AED | -4.00% | 5,000.00 AED |
| 20,000.00 AED | 0.50% = 100.00 AED | -4.00% | 2,500.00 AED |

**권장:** 초기 3개월은 1회 risk 0.50%만 사용하십시오. 월간 손실이 -5.00%에 도달하면 해당 월 거래를 중단하십시오.

## F. 단타 Daily Checklist

| No | Check          | Pass 기준                      |
| -: | -------------- | ---------------------------- |
|  1 | 시장 Gate        | 주요 지수/섹터가 하락 추세면 신규 Long 금지  |
|  2 | 뉴스 Gate        | 실적/금리/FOMC/전쟁/원자재 이벤트 확인     |
|  3 | Liquidity Gate | 스프레드 과도하면 진입 금지              |
|  4 | Entry Plan     | Entry, Stop, TP가 주문 전 기록됨    |
|  5 | Risk Gate      | 총 단타 open risk가 계좌의 2.00% 이하 |
|  6 | Journal        | 진입 이유, 차트, 뉴스, 수량, 손절가 기록    |

---

# Track-L: 장기 투자 구조 — 3년 이상 +20.00%

## A. 장기 목표 해석

3년 총 +20.00%는 약 **연 +6.27% CAGR**입니다.
이는 단타보다 훨씬 현실적입니다. 다만 Vanguard는 미국 주식 밸류에이션이 일부 낮아졌음에도 장기 fair value보다 높다고 보므로, 고평가 대형 성장주만 추격하는 구조는 피해야 합니다. ([corporate.vanguard.com][2])

## B. 장기 Portfolio Structure

**기준:** 총 75,000.00 AED 장기 계좌.

| No | Bucket                                     | Allocation |         Value | 목적             |
| -: | ------------------------------------------ | ---------: | ------------: | -------------- |
|  1 | Core Global Equity ETF                     |     40.00% | 30,000.00 AED | 시장 전체 성장 수익    |
|  2 | Quality / Dividend / Cashflow              |     20.00% | 15,000.00 AED | 방어력·현금 흐름       |
|  3 | AI Infrastructure / Semiconductors / Power |     15.00% | 11,250.00 AED | 2026 구조적 성장 테마 |
|  4 | Commodity / Energy / Materials             |     10.00% |  7,500.00 AED | 지정학·인플레 hedge  |
|  5 | Bonds / T-bills / Money Market             |     10.00% |  7,500.00 AED | 변동성 완충         |
|  6 | Opportunistic Cash                         |      5.00% |  3,750.00 AED | 급락 시 분할매수      |

BlackRock은 AI beneficiaries와 commodity exporters를 2026년 주요 선호 영역으로 제시하면서도, 시장이 소수 mega force에 집중되어 있어 “분산처럼 보이는 큰 active bet”을 경계해야 한다고 설명합니다. 따라서 AI·commodity는 넣되, Core와 Quality를 함께 둬야 합니다. ([BlackRock][1])

## C. 장기 종목/ETF Score

**총점 100.00점, 80.00점 이상만 신규 편입.**

| No | Factor            | Weight | Rule                                             |
| -: | ----------------- | -----: | ------------------------------------------------ |
|  1 | Business Quality  |  25.00 | ROIC, margin, pricing power, 시장점유율               |
|  2 | Earnings/Cashflow |  20.00 | 매출·EPS·FCF 성장 지속성                                |
|  3 | Balance Sheet     |  15.00 | 부채비율, 이자보상배율, 현금 흐름 안정성                           |
|  4 | Valuation         |  15.00 | PER/PBR/EV-EBITDA가 성장 대비 과도하지 않음                 |
|  5 | Structural Theme  |  15.00 | AI, energy, infrastructure, defense, commodity 등 |
|  6 | Governance/Risk   |  10.00 | 회계, 소송, 규제, 지정학 리스크                              |

## D. 장기 매수 방식

| 방식             | Rule                         |
| -------------- | ---------------------------- |
| Initial Buy    | 목표 비중의 30.00%만 1차 진입         |
| DCA            | 매월 또는 분기별 분할매수               |
| Drawdown Add   | -10.00%, -20.00% 구간에서만 추가 매수 |
| Valuation Stop | 실적 둔화 + 고평가 동시 발생 시 추가 매수 중단  |
| Rebalance      | 반기 1회 또는 비중 ±5.00% 이탈 시      |
| Review         | 실적 발표 후 thesis 유지 여부 점검      |

## E. 장기 Exit Rule

| 상황                    | Action                     |
| --------------------- | -------------------------- |
| 목표 +20.00% 도달         | 30.00% 부분 익절 또는 trailing 전환 |
| Thesis 훼손             | 전량 또는 50.00% 축소            |
| 회계/규제 리스크             | 즉시 Risk Committee 리뷰       |
| 섹터 과열                 | 신규 매수 중단, 기존 보유만 관리         |
| 포트폴리오 단일 종목 12.00% 초과 | 리밸런싱                       |

---

# 통합 데이터·AI 구조

## 1) Data Layer

| No | Data              | Track-S  | Track-L  |
| -: | ----------------- | -------- | -------- |
|  1 | OHLCV             | 필수, 일/분봉 | 필수, 일/주봉 |
|  2 | Volume/Liquidity  | 필수       | 보조       |
|  3 | Fundamentals      | 보조       | 필수       |
|  4 | Earnings Calendar | 필수       | 필수       |
|  5 | Macro/Rates/Oil   | 필수       | 필수       |
|  6 | News/Sentiment    | 필수       | 보조       |
|  7 | Portfolio/Risk    | 필수       | 필수       |
|  8 | Trading Journal   | 필수       | 필수       |

## 2) Signal Engine

```text
Market Regime
  → Sector Strength
    → Candidate Scan
      → Track-S Momentum Score
      → Track-L Fundamental Score
        → Risk Gate
          → Order Plan
            → Journal
              → Review
```

## 3) Decision Gate

| Gate  | 단타 Track-S                      | 장기 Track-L                 |
| ----- | ------------------------------- | -------------------------- |
| Green | Score ≥75.00, Risk/Reward ≥2.00 | Score ≥80.00, valuation 허용 |
| Amber | Score 65.00~74.99               | Score 70.00~79.99          |
| Red   | 손절가 없음, 유동성 부족                  | thesis 불명확, 재무 악화          |
| ZERO  | 자동 매수, margin 과다, 손실 제한 없음        | 단일 종목 몰빵, P2/내부 정보 사용       |

---

# Options A/B/C

| Option | 구조                                  |  기대수익 | Risk | Time     | 추천     |
| ------ | ----------------------------------- | ----: | ---- | -------- | ------ |
| A      | 보수형: 단타 10.00%, 장기 85.00%, 현금 5.00% | 낮음~중간 | 낮음   | 즉시       | 안정 우선  |
| B      | 균형형: 단타 20.00%, 장기 75.00%, 현금 5.00% |    중간 | 중간   | 즉시       | **권장** |
| C      | 공격형: 단타 35.00%, 장기 60.00%, 현금 5.00% |    높음 | 높음   | 3개월 검증 후 | 초보 비권장 |

**추천:** Option B.
단타 목표가 +10.00%로 높기 때문에 전체 자금 중 단타 비중은 20.00% 이내가 합리적입니다.

---

# 실제 운영 Rulebook

## 매일

| 시간     | Action                   |
| ------ | ------------------------ |
| 장 시작 전 | Macro/news/sector 확인     |
| 장중     | 신규 진입은 사전에 등록된 watchlist만 |
| 장 마감 후 | 손익, 진입 이유, rule 위반 여부 기록 |

## 매주

| 항목        | Action                     |
| --------- | -------------------------- |
| 단타 성과     | 승률, 평균손익비, max drawdown 확인 |
| Watchlist | 10~20개 유지                  |
| 장기 종목     | 실적/뉴스/valuation 변화만 점검     |

## 매월

| 항목    | Action                     |
| ----- | -------------------------- |
| 단타    | +10.00% 달성 시 월 거래 축소       |
| 단타 손실 | -5.00% 도달 시 월 거래 중단        |
| 장기    | DCA 실행, thesis 변화 점검       |
| 리포트   | Track-S / Track-L 별도 손익 계산 |

---

# Python/자동화 설계

## 모듈 구조

```text
stock_investment_os/
├── config/
│   ├── universe.yaml
│   ├── risk_rules.yaml
│   └── portfolio_targets.yaml
├── data/
│   ├── price_loader.py
│   ├── fundamentals_loader.py
│   ├── macro_loader.py
│   └── news_loader.py
├── signals/
│   ├── market_regime.py
│   ├── short_term_score.py
│   └── long_term_score.py
├── risk/
│   ├── position_sizing.py
│   ├── stop_loss.py
│   └── exposure_check.py
├── portfolio/
│   ├── track_s_trading.py
│   ├── track_l_investing.py
│   └── rebalance.py
├── reports/
│   ├── daily_brief.py
│   ├── monthly_review.py
│   └── decision_journal.py
└── app.py
```

## 핵심 Output

| Report                | 내용                                |
| --------------------- | --------------------------------- |
| Daily Brief           | 오늘 매매 가능 후보, 진입가, 손절가, 목표가        |
| Risk Dashboard        | open risk, max drawdown, exposure |
| Track-S Journal       | 모든 단타 의사 결정 기록                     |
| Track-L Thesis Report | 장기 보유 이유와 훼손 조건                   |
| Monthly Scorecard     | 목표 대비 성과, rule 위반, 개선점            |

---

# 단타 후보 출력 예시 포맷

| Ticker   | Sector   | Score |  Entry |  Stop |    TP1 |    TP2 |   Risk | Verdict   |
| -------- | -------- | ----: | -----: | ----: | -----: | -----: | -----: | --------- |
| SAMPLE-A | AI Infra | 82.00 | 100.00 | 96.00 | 105.00 | 110.00 | -4.00% | Watch/Buy |
| SAMPLE-B | Energy   | 73.00 |  50.00 | 48.00 |  52.50 |  55.00 | -4.00% | AMBER     |
| SAMPLE-C | Weak     | 61.00 |      - |     - |      - |      - |      - | No Trade  |

---

# 장기 후보 출력 예시 포맷

| Ticker/ETF | Bucket      | Score | Target Weight | Buy Rule | Exit Rule | Verdict    |
| ---------- | ----------- | ----: | ------------: | -------- | --------- | ---------- |
| CORE-ETF   | Core Global | 85.00 |        40.00% | 월 DCA    | 리밸런싱      | Accumulate |
| AI-INFRA   | AI Infra    | 82.00 |        15.00% | 조정 시 분할  | thesis 훼손 | Accumulate |
| COMMODITY  | Hedge       | 78.00 |        10.00% | 원자재 강세 시 | 과열 시 축소   | AMBER      |

---

# Fail-safe Rules

| Rule            | 단타    | 장기   |
| --------------- | ----- | ---- |
| 손절 없는 매수        | ZERO  | ZERO |
| 단일 종목 20.00% 초과 | 금지    | 금지   |
| Margin 사용       | 초기 금지 | 금지   |
| Options/0DTE    | 초기 금지 | 금지   |
| 뉴스만 보고 진입       | 금지    | 금지   |
| AI 예측만으로 자동 매수   | ZERO  | ZERO |
| 내부 정보/비공개 정보 사용  | ZERO  | ZERO |

FINRA는 2026년 intraday margin 제도 변경으로 거래 유연성은 커지지만, frequent margin trading은 여전히 고위험이며 충분한 자본과 감내 가능한 자금만 사용해야 한다고 명시합니다. ([finra.org][3])

---

# 실행 Steps

## Step 1 — Universe 확정

| 입력 | 예시                                 |
| -- | ---------------------------------- |
| 시장 | US / Korea / UAE / Global ETF      |
| 상품 | Stocks / ETFs only                 |
| 제외 | Options, leveraged ETF, penny stock |
| 통화 | AED 기준 환산                          |

## Step 2 — Track-S 단타 Scanner 구축

필수 조건:

```text
Score ≥ 75.00
Expected R/R ≥ 2.00
Stop ≤ -4.00%
Liquidity Pass
Catalyst Pass
Market Regime Pass
```

## Step 3 — Track-L 장기 Portfolio 구축

필수 조건:

```text
Core 40.00%
Quality 20.00%
AI/Infra 15.00%
Commodity/Energy 10.00%
Bonds/Cash 15.00%
```

## Step 4 — 월간 Review

| KPI                      |                         Target |
| ------------------------ | -----------------------------: |
| Track-S Monthly Return   | +10.00% target, not guaranteed |
| Track-S Max Monthly Loss |                         -5.00% |
| Track-S Rule Violation   |                          0.00건 |
| Track-L 3Y Total Return  |                        +20.00% |
| Track-L Max Single Name  |                        ≤12.00% |
| Cash Buffer              |                         ≥5.00% |

---

# cmd3

```text
/logi-master report
```

```text
/logi-master data-spine
```

```text
/redo stock-investment-os
```

---

# ZERO Log

| 단계             | 이유                   | 위험          | 요청데이터                 | 다음 조치             |
| -------------- | -------------------- | ----------- | --------------------- | ---------------- |
| 종목 직접 추천       | 예산·시장·세금·계좌·위험성향 미확정 | 부적합 투자 가능   | 시장, 투자금, broker, 허용상품 | 후보 스캐너 먼저 구축     |
| 자동매매           | 승인·손절·로그 미정          | 손실 확대       | 주문 승인 Rule            | Dry-run → 승인형 실행 |
| Margin/Options | 숙련도·손실한도 미확정         | 원금 초과 손실 가능 | margin 사용 여부          | 초기 3개월 금지        |

**결론:**
실제 투자에 도움이 되는 구조는 “수익률 예측기”가 아니라 **Track-S 단타 실행 시스템 + Track-L 장기 배분 시스템 + 공통 Risk Gate**입니다. 단타는 자금 20.00% 이내, 손절 -4.00%, 월 손실 -5.00% 중단을 기준으로 운영합니다. 장기는 Core/Quality/AI/Commodity/Bond로 나누고, 3년 +20.00%를 CAGR 6.27% 목표로 관리하는 구조가 가장 합리적입니다.

[1]: https://www.blackrock.com/corporate/insights/blackrock-investment-institute/publications/outlook "Q2 2026 Investment Outlook | BII"
[2]: https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html "Vanguard Capital Markets Model® forecasts | Vanguard"
[3]: https://www.finra.org/investors/insights/intraday-margin-requirements "Understanding the New Intraday Margin Requirements | FINRA.org"
