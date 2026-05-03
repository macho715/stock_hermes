# Plan 문서 초안 — 단타 Track-S / 장기 Track-L 투자 운영 구조

## 1. Overview

**목적:** 단타 Track-S와 장기 Track-L을 분리해 운영하고, 공통 Risk Gate를 통해 손실 제한·리밸런싱·리포트를 체계화한다.

**관찰한 사실**

* 첨부 마크다운은 **1개월 +10.00% 단타 목표는 공격적**, **3년 +20.00% 장기 목표는 구조화 가능**하다고 판정한다. 
* 문서의 핵심 구조는 **Track-S 단타 실행 시스템 + Track-L 장기 배분 시스템 + 공통 Risk Gate**이다. 
* BlackRock은 2026년 Q2 전망에서 AI, 지정학, 에너지 충격 등 소수의 메가포스가 시장을 주도해 단순 분산보다 명확한 active view와 plan B가 필요하다고 설명한다. ([BlackRock][1])
* Vanguard는 2026년 3월 31일 기준 미국 주식 밸류에이션이 장기 fair value보다 여전히 높으며, 밸류에이션은 단기·중기 성과 예측 도구로는 부적절하다고 명시한다. ([Vanguard][2])
* FINRA는 2026년 6월 4일부터 새로운 intraday margin 기준이 적용되며, 잦은 margin 거래는 여전히 고위험이라고 안내한다. ([FINRA][3])

**사용자 요청사항**

* 첨부된 투자 운영 내용을 실행 가능한 **Plan 문서 초안**으로 재구성한다.

**가정:**

* 총 투자금은 첨부 문서의 예시값인 **100,000.00 AED**를 기준으로 한다.
* 실제 투자금, 시장, 브로커, 세금, 투자 가능 상품은 아직 확정되지 않았다.
* 본 문서는 개인 맞춤 투자 자문이 아니라 운영 구조 초안이다.

---

## 2. Goals

| 구분         |            목표 | 설명                          |
| ---------- | ------------: | --------------------------- |
| Track-S 단타 |   1개월 +10.00% | 보장 수익률이 아니라 **익절 Gate**로 관리 |
| Track-L 장기 | 3년 이상 +20.00% | 약 **6.27% CAGR** 기준의 장기 목표  |
| 공통         |      원금 보전 우선 | 손절, 월간 손실 제한, 리밸런싱, 리포트 운영  |
| 운영         |    룰 기반 투자 OS | 예측 중심이 아니라 진입·손절·리뷰 기준 중심   |

---

## 3. Scope

### In Scope

| 항목            | 포함 내용                                                   |
| ------------- | ------------------------------------------------------- |
| Track-S 단타 구조 | 자금 배분, 진입 조건, 손절, 익절, 월간 손실 제한                          |
| Track-L 장기 구조 | Core ETF, Quality/Growth/AI/Commodity/Bonds/Cash 배분     |
| Risk Gate     | 포지션 크기, 손절, 월간 중단 기준, 단일 종목 비중 제한                       |
| Review 체계     | 일간 체크리스트, 주간 성과 점검, 월간 리포트                              |
| 후보 평가 기준      | 단타 Score, 장기 Score, Liquidity Gate, Market Regime Gate  |
| 리포트 산출물       | Daily Brief, Risk Dashboard, Journal, Monthly Scorecard |

### Out of Scope

| 항목                      | 제외 사유                                                  |
| ----------------------- | ------------------------------------------------------ |
| 특정 종목 직접 추천             | 투자금, 시장, 세금, 브로커, 위험성향 미확정                             |
| 자동매매 실행                 | 주문 승인 Rule, 로그, 손실 제한 체계 미확정                           |
| 초기 Margin 사용            | 잦은 margin 거래는 고위험이며, FINRA도 충분한 자본과 손실 감내 가능 자금 사용을 강조 |
| Options / 0DTE          | 첨부 문서상 초기 금지 항목                                        |
| Penny stock / 유동성 부족 종목 | 거래정지, 스프레드, 급락 위험                                      |
| 내부정보·비공개 정보 활용          | 규제·윤리 리스크                                              |
| 세금·법률 자문                | 관할권과 개인 상황 미확정                                         |

---

## 4. Constraints

| 구분       | 제약                                              |
| -------- | ----------------------------------------------- |
| 자금 분리    | Track-S 손실이 Track-L 장기 포트폴리오를 침식하지 않아야 함        |
| 단타 손실 제한 | Track-S 월간 손실 **-5.00%** 도달 시 해당 월 거래 중단        |
| 단타 손절    | 기본 손절 **-4.00%**, Hard Stop **-5.00% 초과 손실 금지** |
| 장기 리밸런싱  | 반기 1회 또는 비중 ±5.00% 이탈 시 검토                      |
| 단일 종목 집중 | 장기 포트폴리오 내 단일 종목 **12.00% 초과 시 리밸런싱 검토**        |
| 마진       | 초기 사용 금지 또는 별도 승인 필요                            |
| 자동화      | AI 예측만으로 자동매수 금지                                |
| 수익률      | 목표 수익률은 보장값이 아니라 운영 기준                          |

---

## 5. Phases

### Phase 1 — 계좌·자금 분리 확정

| 항목  | 내용                                         |
| --- | ------------------------------------------ |
| 목적  | 단타 손실과 장기 포트폴리오를 구조적으로 분리                  |
| 기준  | Track-S 20.00%, Track-L 75.00%, Cash 5.00% |
| 산출물 | 자금 배분표, 계좌/태그 분리 기준                        |

**가정:** 총 투자금 100,000.00 AED 기준.

| Track             | Allocation |         Value | 목표                | Max Loss Rule           |
| ----------------- | ---------: | ------------: | ----------------- | ----------------------- |
| Track-S 단타        |     20.00% | 20,000.00 AED | 월 +10.00% 익절 Gate | 월 -5.00% 시 거래 중단        |
| Track-L 장기        |     75.00% | 75,000.00 AED | 3년 +20.00%        | 분기 -12.00% 이상 시 리밸런싱 검토 |
| Cash / Dry Powder |      5.00% |  5,000.00 AED | 기회 대응             | 단타 손실 보전용 사용 금지         |

---

### Phase 2 — Track-S 단타 Rule 설계

| 항목    | 내용                             |
| ----- | ------------------------------ |
| 목적    | 손실 제한형 단타 실행 구조 확정             |
| 진입 기준 | Score 75.00점 이상                |
| 기본 전략 | 이벤트·모멘텀·유동성 기반                 |
| 금지    | 무손절, 과도한 margin, 옵션/0DTE 초보 진입 |

**Track-S Score 기준**

| Factor              | Weight | Rule                                    |
| ------------------- | -----: | --------------------------------------- |
| Market Regime       |  20.00 | 지수 상승 추세 또는 섹터 강세일 때만 Long              |
| Relative Strength   |  20.00 | 대상 종목이 지수/섹터 대비 20일 수익률 우위              |
| Volume Expansion    |  15.00 | 거래량 20일 평균 대비 1.50배 이상                  |
| Breakout / Pullback |  15.00 | 20일 신고가 돌파 또는 상승 추세 눌림목                 |
| Catalyst            |  15.00 | 실적, 수주, 정책, AI capex, commodity shock 등 |
| Risk/Reward         |  15.00 | 목표 +10.00%, 손절 -4.00% 구조 가능             |

---

### Phase 3 — Track-L 장기 Portfolio 구조 확정

| 항목    | 내용                                                        |
| ----- | --------------------------------------------------------- |
| 목적    | 3년 이상 +20.00% 목표를 위한 장기 배분 구조 수립                          |
| 방식    | Core + Quality + AI/Infra + Commodity/Energy + Bonds/Cash |
| 진입 기준 | Score 80.00점 이상                                           |
| 금지    | 단일 테마 몰빵, 고평가 추격매수                                        |

**Track-L 배분 기준**

| Bucket                                     | Allocation |         Value | 목적            |
| ------------------------------------------ | ---------: | ------------: | ------------- |
| Core Global Equity ETF                     |     40.00% | 30,000.00 AED | 시장 전체 성장 수익   |
| Quality / Dividend / Cashflow              |     20.00% | 15,000.00 AED | 방어력·현금흐름      |
| AI Infrastructure / Semiconductors / Power |     15.00% | 11,250.00 AED | 구조적 성장 테마     |
| Commodity / Energy / Materials             |     10.00% |  7,500.00 AED | 지정학·인플레 hedge |
| Bonds / T-bills / Money Market             |     10.00% |  7,500.00 AED | 변동성 완충        |
| Opportunistic Cash                         |      5.00% |  3,750.00 AED | 급락 시 분할매수     |

---

### Phase 4 — 공통 Risk Gate 구축

| Gate  | Track-S                   | Track-L                    |
| ----- | ------------------------- | -------------------------- |
| Green | Score ≥75.00, R/R ≥2.00   | Score ≥80.00, valuation 허용 |
| Amber | Score 65.00~74.99         | Score 70.00~79.99          |
| Red   | 손절가 없음, 유동성 부족            | thesis 불명확, 재무 악화          |
| ZERO  | 자동매수, margin 과다, 손실 제한 없음 | 단일 종목 몰빵, 내부정보 사용          |

---

### Phase 5 — Review / Report 운영

| 주기 | 운영 항목                                                      |
| -- | ---------------------------------------------------------- |
| 매일 | Macro/news/sector 확인, watchlist만 진입, 장 마감 후 journal 기록     |
| 매주 | 승률, 평균손익비, max drawdown, watchlist 10~20개 유지               |
| 매월 | Track-S / Track-L 별도 손익 계산, rule 위반 확인, 장기 DCA 및 thesis 점검 |

---

## 6. Tasks

### Phase 1 Tasks — 계좌·자금 분리

| No | Task                           | 완료 기준                    |
| -: | ------------------------------ | ------------------------ |
|  1 | 총 투자금 확정                       | 실제 금액 입력                 |
|  2 | Track-S / Track-L / Cash 비율 확정 | 20/75/5 또는 수정 비율 승인      |
|  3 | 계좌 또는 포트폴리오 태그 분리              | 단타 손실이 장기 자금에 반영되지 않는 구조 |
|  4 | 월간 손실 중단 기준 설정                 | Track-S -5.00% Rule 적용   |

---

### Phase 2 Tasks — Track-S 단타

| No | Task               | 완료 기준                                |
| -: | ------------------ | ------------------------------------ |
|  1 | 단타 Universe 확정     | 시장, 상품, 제외 대상 명시                     |
|  2 | Liquidity Gate 설정  | 유동성 부족 종목 제외                         |
|  3 | Entry Rule 확정      | 20일 고점 돌파 + 거래량 1.50배 등              |
|  4 | Stop / TP 설정       | Stop -4.00%, TP1 +5.00%, TP2 +10.00% |
|  5 | Position Sizing 설정 | 1회 risk 0.50%~1.00%                  |
|  6 | Daily Checklist 작성 | 주문 전 Entry, Stop, TP 기록              |

---

### Phase 3 Tasks — Track-L 장기

| No | Task              | 완료 기준                                          |
| -: | ----------------- | ---------------------------------------------- |
|  1 | 장기 Bucket 확정      | Core, Quality, AI/Infra, Commodity, Bonds/Cash |
|  2 | 각 Bucket 목표 비중 입력 | 목표 비중표 완성                                      |
|  3 | 장기 Score 기준 적용    | 80.00점 이상만 신규 편입                               |
|  4 | DCA Rule 작성       | 월별 또는 분기별 분할매수 기준 확정                           |
|  5 | Exit Rule 작성      | thesis 훼손, 과열, 단일 종목 비중 초과 기준 명시               |

---

### Phase 4 Tasks — Risk Gate

| No | Task                             | 완료 기준                       |
| -: | -------------------------------- | --------------------------- |
|  1 | Green / Amber / Red / ZERO 기준 확정 | 진입 가능·보류·금지 조건 구분           |
|  2 | Open Risk 한도 설정                  | 총 단타 open risk 계좌의 2.00% 이하 |
|  3 | Margin 사용 제한 설정                  | 초기 금지 또는 별도 승인 조건           |
|  4 | Options / 0DTE 제한 설정             | 초기 금지                       |
|  5 | Rule 위반 기록 방식 확정                 | Journal에 위반 여부 기록           |

---

### Phase 5 Tasks — Review / Report

| No | Task                     | 완료 기준                             |
| -: | ------------------------ | --------------------------------- |
|  1 | Daily Brief 포맷 작성        | 후보, 진입가, 손절가, 목표가                 |
|  2 | Risk Dashboard 작성        | open risk, max drawdown, exposure |
|  3 | Track-S Journal 작성       | 진입 이유, 차트, 뉴스, 수량, 손절가            |
|  4 | Track-L Thesis Report 작성 | 보유 이유와 훼손 조건                      |
|  5 | Monthly Scorecard 작성     | 성과, rule 위반, 개선점                  |

---

## 7. Risks

| Risk         | 설명                  | 대응                              |
| ------------ | ------------------- | ------------------------------- |
| 단타 목표 과도     | 월 +10.00%는 공격적 목표   | 수익 목표가 아니라 익절 Gate로 관리          |
| 손절 미이행       | 단타 손실 확대 가능         | Initial Stop, Hard Stop 사전 입력   |
| Margin 손실 확대 | 레버리지로 원금 초과 손실 가능   | 초기 margin 금지                    |
| AI/테마 과집중    | 특정 테마 급락 시 포트폴리오 훼손 | Core, Quality, Cash와 함께 운영      |
| 고평가 추격매수     | 장기 기대수익률 저하 가능      | Valuation Gate와 DCA 적용          |
| 자동매매 오류      | 예측 오류·시스템 오류로 손실 확대 | 승인형 실행, Dry-run 우선              |
| 리포트 미작성      | Rule 위반 원인 추적 불가    | Daily / Weekly / Monthly 기록 의무화 |
| 실제 조건 미확정    | 세금, 브로커, 상품 제한 미반영  | 실행 전 시장·계좌·상품 범위 확정             |

---

## 8. Review Criteria

| 구분                       | 기준                             |
| ------------------------ | ------------------------------ |
| Track-S Monthly Return   | +10.00% target, not guaranteed |
| Track-S Max Monthly Loss | -5.00% 도달 시 거래 중단              |
| Track-S Rule Violation   | 0건 목표                          |
| Track-S Risk/Reward      | 진입 전 R/R ≥2.00                 |
| Track-L 3Y Total Return  | +20.00% 목표                     |
| Track-L Max Single Name  | ≤12.00%                        |
| Cash Buffer              | ≥5.00%                         |
| 리밸런싱                     | 반기 1회 또는 비중 ±5.00% 이탈 시        |
| Journal 작성률              | 모든 진입·청산 건 기록                  |

---

## 9. Deliverables

| Deliverable              | 내용                                |
| ------------------------ | --------------------------------- |
| 자금 배분표                   | Track-S / Track-L / Cash 비중과 금액   |
| Track-S Rulebook         | 진입, 손절, 익절, 포지션 크기, 월간 중단 기준      |
| Track-L Portfolio Policy | Bucket, 목표 비중, DCA, Exit Rule     |
| Risk Gate Matrix         | Green / Amber / Red / ZERO 기준     |
| Daily Brief              | 단타 후보, 진입가, 손절가, 목표가              |
| Risk Dashboard           | open risk, max drawdown, exposure |
| Track-S Journal          | 매매 사유, 수량, 가격, 손익, rule 위반 여부     |
| Track-L Thesis Report    | 장기 보유 논리, 훼손 조건, 리밸런싱 판단          |
| Monthly Scorecard        | Track-S / Track-L 성과, 위반 사항, 개선점  |

---

## 결론

이 Plan의 핵심은 수익률 예측이 아니라 **단타와 장기를 분리한 운영 구조**다. Track-S는 제한된 자금으로 손절·익절·월간 중단 기준을 엄격히 적용하고, Track-L은 Core/Quality/AI/Commodity/Bonds/Cash 배분으로 3년 이상 목표를 관리한다. Margin, Options/0DTE, 자동매매, 특정 종목 추천은 현재 범위에서 제외한다.

[1]: https://www.blackrock.com/corporate/insights/blackrock-investment-institute/publications/outlook "Q2 2026 Investment Outlook | BII"
[2]: https://corporate.vanguard.com/content/corporatesite/us/en/corp/vemo/vemo-return-forecasts.html "Vanguard Capital Markets Model® forecasts | Vanguard"
[3]: https://www.finra.org/investors/insights/intraday-margin-requirements "Understanding the New Intraday Margin Requirements | FINRA.org"
