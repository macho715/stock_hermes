# STOCKPRED Kraken Dashboard Redesign Implementation

작성일: 2026-05-30

대상 화면: `root_folder_snapshot/stock-pred-v5`

현재 실행 URL: `http://127.0.0.1:5173/`

## Overview

이 문서는 `STOCKPRED Executive Dashboard v2.1` 화면을 사용자가 제공한 Kraken dark fintech 목업 이미지에 맞춰 변경한 작업 내용을 기록한다.

사용자 요청은 생성된 목업 이미지와 최대한 동일하게 현재 대시보드를 변경하는 것이었다.

기준 이미지:

- `C:\Users\jichu\Downloads\주식\생성된 이미지 1.png`

검증 캡처:

- `artifacts/dashboard-redesign/stockpred-kraken-dashboard-20260530.png`

## Goals

- 기존 Classic dashboard가 아니라 Executive layout을 기본 실행 화면으로 고정한다.
- Kraken 계열의 dark fintech 스타일을 적용한다.
- 목업 이미지의 주요 구조를 실제 React 컴포넌트에 반영한다.
- `REPORT ONLY`, `screening_output_only`, `No broker execution` 안전 경계를 유지한다.
- 실제 데이터가 없거나 0으로 오는 항목은 목업 숫자 fallback 대신 `—` 또는 unavailable 상태로 표시한다.

## Scope

### In Scope

- Executive dashboard shell.
- Header bar.
- Four KPI cards.
- Market Snapshot panel.
- Price Chart panel.
- Model Scores panel.
- AI Decision Panel.
- NotebookLM News Analysis block.
- Action Plan block.
- Watchlist panel.
- News Timeline panel.
- Scenario Outlook panel.
- Footer safety text.
- Local Vite feature flag.

### Out of Scope

- Backend recommendation algorithm 변경.
- Broker execution 기능 추가.
- NotebookLM 8088 서버 구현.
- 픽셀 단위 100% 동일성 보장.
- 생성 이미지를 배경으로 깔아 실제 UI처럼 위장하는 방식.

## Inputs

### Design Reference

`design-md-recommender`를 사용해 `C:\Users\jichu\Downloads\design-md-main\design-md` 카탈로그를 스캔했다.

결과:

- catalog size: 73
- selected candidate: `kraken`
- selected design file: `C:\Users\jichu\Downloads\design-md-main\design-md\kraken\DESIGN.md`
- generated recommendation: `out/design-md-recommender/recommendation.json`

`kraken` 디자인 기준:

- primary accent: `#7132f5`
- dark variant: `#5741d8`
- positive state: `#149e61`
- cool neutral border: `rgba(104,107,130,0.24)` 계열
- rounded but not pill 형태
- subtle shadow
- professional fintech identity

### Mockup Reference

사용자가 제공한 목업 이미지는 다음 구조를 가진다.

- 상단 header: brand, ticker, company, US/KRX, REPORT ONLY, Last Update.
- KPI row: Current Price, AI Recommendation, Confidence, Risk/Reward.
- Main row: Market Snapshot, Price Chart + Model Scores, AI Decision Panel.
- Bottom row: Watchlist, News Timeline, Scenario Outlook.
- Footer: dashboard snapshot contract and no broker execution notice.

## Changed Files

### Feature Flag

- `root_folder_snapshot/stock-pred-v5/.env.local`

추가 내용:

```env
VITE_DASHBOARD_LAYOUT=executive
VITE_API_URL=http://127.0.0.1:5151
```

이 파일로 5173 dev server가 항상 Executive layout을 로드하게 했다.

### Executive Shell

- `root_folder_snapshot/stock-pred-v5/src/StockPredV5.jsx`

변경 내용:

- Executive layout grid를 목업 비율에 맞게 조정했다.
- 배경을 dark fintech radial/linear background로 변경했다.
- Header, KPI, main grid, bottom grid, footer spacing을 8px 기반으로 조정했다.
- Watchlist용 `execSymbols`는 로드된 OHLCV cache와 추천 snapshot에서만 price, change, changePct, recommendation, confidence를 만든다.
- footer를 목업처럼 좌측 brand, 중앙 safety contract, 우측 data/source로 나눴다.

### Shared Theme

- `root_folder_snapshot/stock-pred-v5/src/components/DashboardCard.jsx`

변경 내용:

- Kraken 스타일 토큰을 `THEME`에 추가했다.
- `panelStyle`과 `labelStyle`을 공통 export로 추가했다.
- 카드 radius를 10px로 맞췄다.
- border를 cool neutral 계열로 변경했다.
- shadow를 기존 강한 terminal shadow에서 restrained fintech shadow로 낮췄다.

### Header

- `root_folder_snapshot/stock-pred-v5/src/components/HeaderBar.jsx`

변경 내용:

- `STOCKPRED` brand lockup을 목업처럼 좌측에 크게 배치했다.
- purple icon block을 추가했다.
- ticker selector, company label, US/KRX segmented control, REPORT ONLY badge, Last Update를 분리했다.
- active market 버튼을 Kraken purple gradient로 변경했다.

### KPI Cards

- `CurrentPriceCard.jsx`
- `RecommendationKpi.jsx`
- `ConfidenceKpi.jsx`
- `RiskRewardKpi.jsx`

변경 내용:

- 목업과 유사한 fixed-height KPI card layout을 적용했다.
- Current Price에는 purple sparkline SVG를 추가했다.
- AI Recommendation에는 BUY/SELL label과 circular arrow icon을 추가했다.
- Confidence는 실제 `notebooklm_confidence` 또는 `probability`가 있을 때만 표시한다.
- Risk/Reward는 실제 `risk_reward`가 있을 때만 표시하고, 없으면 `—`를 표시한다.

### Main Panels

- `MarketSnapshotPanel.jsx`
- `CompactPriceChart.jsx`
- `ModelScoresPanel.jsx`
- `AiDecisionPanel.jsx`
- `NotebookNewsAnalysis.jsx`
- `ActionPlanPanel.jsx`

변경 내용:

- Market Snapshot을 목업의 표 형태로 바꿨다.
- Price Chart title에 range buttons를 추가했다.
- Price chart line color를 Kraken purple로 변경했다.
- volume axis와 price axis를 분리해 차트 축 충돌을 줄였다.
- Model Scores를 circular score ring 형태로 변경했다.
- AI Decision Panel을 large verdict block + rationale 형태로 변경했다.
- NotebookLM News Analysis는 실제 `notebook_analysis`가 있을 때만 factor rows를 표시하고, 없으면 unavailable 상태를 표시한다.
- Action Plan은 entry, stop loss, TP1, TP2 table로 변경했다.

### Bottom Panels

- `WatchlistPanel.jsx`
- `NewsTimelinePanel.jsx`
- `ScenarioOutlookPanel.jsx`

변경 내용:

- Watchlist를 ticker, price, change, AI Rec, confidence 표 구조로 변경했다.
- News Timeline을 목업처럼 time, title, source row 구조로 변경했다.
- Scenario Outlook을 Bull/Base/Bear 3-card 구조로 변경했다.
- Scenario Outlook은 실제 `scenario_outlook`이 있을 때만 Bull/Base/Bear rows를 표시하고, 없으면 unavailable 상태를 표시한다.

## Verification

### Build

명령:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901\root_folder_snapshot\stock-pred-v5
npm run build
```

결과:

- Vite build 성공.
- 666 modules transformed.
- bundle generated.
- chunk size warning만 남음.

주의:

- chunk size warning은 기존 대시보드 번들 크기 문제다.
- 이번 변경의 syntax/blocking error는 아니다.

### Runtime

명령:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173/" -TimeoutSec 8
```

결과:

- HTTP 200.

### Browser Smoke

Playwright headless smoke를 실행했다.

확인한 DOM 문구:

- `STOCKPRED`
- `MARKET SNAPSHOT`
- `AI DECISION PANEL`
- `WATCHLIST`
- `SCENARIO OUTLOOK`
- `Report-only`
- `Source: YFINANCE`

결과 JSON:

```json
{
  "STOCKPRED": true,
  "MARKET SNAPSHOT": true,
  "AI DECISION PANEL": true,
  "WATCHLIST": true,
  "SCENARIO OUTLOOK": true,
  "Report-only": true,
  "Source: YFINANCE": true
}
```

검증 캡처:

- `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\dashboard-redesign\stockpred-kraken-dashboard-20260530.png`
- `C:\Users\jichu\Downloads\주식\stock_1901\artifacts\dashboard-redesign\stockpred-actual-data-dashboard-20260530.png`

## Actual Data Pass - 2026-05-30

`mstack-plan` 기준으로 `plan_20260530_actual_dashboard_data.md`를 작성하고, `docs/LAYOUT.md`와 root `COMPONENT_LAYOUT.md`를 확인한 뒤 Executive Dashboard의 샘플 표시를 제거했다.

변경 원칙:

- OHLCV에서 계산 가능한 값은 로드된 `cache[selected].data`에서 계산한다.
- 추천, risk/reward, confidence, scenario, NotebookLM 값은 `execSnap` 또는 backend model evidence에서만 가져온다.
- 실제 데이터가 없으면 목업 숫자 대신 `—`, `NO DATA`, 또는 unavailable 문구를 표시한다.
- report-only, screening-only, no broker execution 경계는 유지한다.

추가 검증:

- `rg`로 목업 숫자와 샘플 뉴스 문구가 `root_folder_snapshot/stock-pred-v5/src`에 남아 있지 않음을 확인했다.
- `npm run build`가 다시 성공했다.
- Playwright smoke에서 실제 렌더링 화면에 `Source: YFINANCE`가 표시되는 것을 확인했다.

## Backend Snapshot Field Pass - 2026-05-30

Executive Dashboard에서 `—`로 남던 fundamentals/news/scenario 영역을 채우기 위해 backend snapshot 필드를 확장했다.

변경 파일:

- `src/stock_rtx4060/recommendation_engine.py`
- `src/stock_rtx4060/dashboard_bridge.py`
- `root_folder_snapshot/stock-pred-v5/src/StockPredV5.jsx`
- `tests/test_dashboard_bridge.py`

추가 필드:

- `fundamentals`: yfinance metadata 기반 `market_cap`, `pe_ttm`, `eps_ttm`, `dividend_yield`, `sector`, `industry`
- `news_headlines`: NotebookLM 서버가 없을 때 yfinance news로 보강한 source-backed headline rows
- `scenario_outlook`: 현재 risk plan의 entry/stop/tp1/tp2와 추천 이유에서 만든 Bull/Base/Bear case

프론트 연결 변경:

- Executive 자동 `/api/recommend` 호출의 `period=1y` 하드코딩을 제거했다.
- `dashboard_config.json`의 recommendation 기본값인 `period=3y`, `data_provider=yfinance`, `model_kind=auto`를 사용한다.
- `news_headlines`가 있으면 News Timeline에 우선 표시한다.

검증:

```powershell
py -3.12 -m py_compile src\stock_rtx4060\recommendation_engine.py src\stock_rtx4060\dashboard_bridge.py api_server.py
py -3.12 -m pytest -q tests/test_dashboard_bridge.py tests/test_dashboard_wave4_fields.py
npm run build
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5151/api/recommend?universe=AAPL&top=1&track=BOTH&data_provider=yfinance&model_kind=logistic&period=3y&advisor_run=0"
```

확인 결과:

- Python compile 통과.
- dashboard bridge targeted tests: 24 passed.
- Vite build 통과.
- API 응답에서 AAPL `market_cap=4583336181760`, `sector=Technology`, `industry=Consumer Electronics`, yfinance news 8건, `scenario_outlook.bull.range=$374.47` 확인.

주의:

- 2026-05-30 패치: NotebookLM 서버 `127.0.0.1:8088`이 내려가 있어도 `notebook_analysis`는 `null`로 남기지 않는다.
  - `iran-war-notelm` 문서의 "NotebookLM query 우선, 실패 시 rule-based fallback" 원칙을 `advisors/notebooklm_news.py`에 반영했다.
  - fallback은 yfinance source-backed headline을 입력으로 사용하고 `analysis_source="notelm_fallback"`, `cache_status="LOCAL_FALLBACK"`를 표시한다.
  - UI는 fallback 분석일 때 `Notelm Fallback News Analysis` 제목과 실제 source label을 표시한다.
- 이 경우 News Timeline은 yfinance news를 사용한다.
- Playwright 화면 재검증은 Vite/React page load 이벤트 timeout으로 완료하지 못했다. API와 build 검증은 완료했다.

## Current Differences From Mockup

현재 구현은 목업과 구조적으로 매우 가깝지만 완전한 픽셀 복제는 아니다.

차이:

- 생성 이미지의 차트는 정적 목업 선형 차트다.
- 현재 구현은 Recharts와 실제 OHLCV/volume 데이터를 사용한다.
- 숫자는 실제 API, OHLCV cache, recommendation snapshot, backend model evidence에서 온다.
- 데이터가 없는 항목은 목업 숫자로 보정하지 않는다.
- 아이콘은 lucide나 이미지 asset이 아니라 텍스트/SVG 기반이다.

## Risks

- `VITE_DASHBOARD_LAYOUT=executive`가 빠지면 Classic layout이 다시 뜬다.
- 실제 API 결과가 `0`, `null`, 또는 불완전한 값을 주면 해당 항목은 `—` 또는 unavailable로 표시된다.
- 목업과 100% 동일한 시각을 원하면 chart, icons, spacing을 추가로 pixel pass해야 한다.
- `5173` dev server는 로컬 실행 상태에 의존한다.

## Next Action

목업과 더 가깝게 만들기 위한 다음 작업은 Price Chart를 Recharts 기반에서 고정형 compact SVG 또는 Canvas chart로 교체하는 것이다.

이 작업을 하면 생성 이미지의 price chart, volume bars, y-axis label, current price marker를 더 정밀하게 맞출 수 있다.
