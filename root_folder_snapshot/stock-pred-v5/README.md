# STOCK·PRED v5.0

> Dual-Market ML Dashboard — US + KRX
> 4-Model Ensemble · Client-Side Inference · Dark Terminal UI

---

## ▸ 빠른 실행 (Windows)

### 사전 요구
- **Node.js LTS 18+** — https://nodejs.org/

### 한 번에 실행
1. 이 폴더 안의 **`RUN.bat`** 더블클릭
2. 첫 실행 시 자동으로 `npm install` 진행 (약 30초~1분)
3. 브라우저가 자동으로 `http://localhost:5173` 열림

### 수동 실행 (PowerShell / CMD)
```bash
cd C:\Users\jichu\Downloads\주식
npm install
npm run dev
```

### 프로덕션 빌드
- **`BUILD.bat`** 더블클릭 → `dist\` 폴더에 정적 파일 생성 + 미리보기 서버 자동 실행

---

## ▸ 핵심 기능

| 영역 | 내용 |
|---|---|
| **Markets** | US 9종목 (AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ) ↔ KRX 9종목 (삼성전자·SK하이닉스·현대차·POSCO홀딩스·NAVER·카카오·LG화학·삼성SDI·포스코퓨처엠) |
| **데이터 소스** | Yahoo Finance v8 chart API via `allorigins.win` 프록시 — 6개월 일봉. 실패 시 `mulberry32` seeded PRNG로 합성 데이터 폴백 (`SYN` 뱃지) |
| **기술 지표** | EMA(12/26/50) · RSI(14) · MACD(12/26/9) · Bollinger Bands(20, 2σ) — 전부 클라이언트 계산 |
| **ML 모델** | Logistic Regression · XGBoost-sim (3 stumps) · LSTM-sim (20-step gates) · Elman RNN (15-step) — **모두 브라우저 내 추론, 외부 API 없음** |
| **앙상블** | LSTM 30% + LR 25% + XGB 25% + RNN 20%. ENS≥65 BUY · ≤35 SELL · 36~64 HOLD |
| **백테스트** | $10,000 시작, ML 신호 기반 매매 시뮬레이션, B&H 대비 Equity Curve · Alpha · Sharpe(√252) · Win Rate · Trade Log |
| **Benchmark** | 현재 마켓 전 종목 일괄 스캔 → 4모델 점수 + ENS 정렬 테이블 |
| **Export** | JSON 페이로드 / Markdown 리포트 다운로드 |

---

## ▸ 사이드바 탭

| Tab | 설명 |
|---|---|
| **SIGNAL** | 지표(RSI/MACD/BB%/EMA Cross) + ENS 점수 카드 + 4모델 바 |
| **MODELS** | 모델별 비교 차트, 가중치, 아키텍처 설명 |
| **BACKTEST** | Equity Curve (ML vs B&H), 8개 통계 그리드, 최근 12건 매매 로그 |

---

## ▸ 폴더 구조

```
주식/
├─ RUN.bat              ← 더블클릭으로 시작
├─ BUILD.bat            ← 프로덕션 빌드
├─ package.json         ← 의존성 정의
├─ vite.config.js       ← Vite 설정
├─ index.html           ← HTML 엔트리
├─ README.md            ← 이 파일
└─ src/
   ├─ main.jsx          ← React 마운트
   └─ StockPredV5.jsx   ← 메인 컴포넌트 (1,688 LOC)
```

---

## ▸ 기술 스택

- **React 18.3** + **Vite 5.4**
- **recharts 2.12** — ComposedChart, LineChart, BarChart, ReferenceLine, CartesianGrid
- **JetBrains Mono** — Google Fonts CDN 자동 로드
- ML 추론 (가격 예측): 브라우저 내 실행 — Logistic Regression · XGBoost-sim · LSTM-sim · Elman RNN (sigmoid/tanh/Math)
- 추천 시스템 (REC 탭): Flask API 서버 (`127.0.0.1:5151`)를 통한 `stock_rtx4060_unified` 연동 — 외부 추천 API 없음 (FILE 모드는 정적 JSON)

---

## ▸ KPI Targets

| KPI | Target |
|---|---|
| Data fetch latency | < 9s (allorigins timeout) |
| Indicator compute | < 50ms / symbol |
| Ensemble inference | < 20ms / symbol |
| Backtest (130 bars) | < 100ms |

---

## ▸ 주의사항

> **AMBER**: 본 도구는 학습/연구 목적입니다. 실제 투자 의사결정에 직접 사용하지 마십시오.

- Yahoo Finance API는 비공식 엔드포인트로, allorigins 프록시 의존성으로 인해 지연 또는 실패 가능
- 실패 시 자동으로 합성 데이터로 폴백되며 사이드바에 `SYN` 표시됨
- ML 모델은 시뮬레이션이며 실제 PyTorch/TensorFlow 학습 가중치 아님
- KRX 가격은 ₩ 단위, US 가격은 $ 단위

---

## ▸ 트러블슈팅

**Q. `npm install` 실패**
- Node.js 18+ 인지 확인 (`node -v`)
- 사내 프록시 사용 시: `npm config set proxy http://...`
- `node_modules` 폴더 삭제 후 재시도

**Q. 데이터가 모두 SYN으로 표시됨**
- allorigins.win 일시 장애 가능 — 잠시 후 재시도
- 회사 방화벽이 외부 API 차단 가능 — 개인 네트워크에서 시도

**Q. 차트가 표시되지 않음**
- 브라우저 콘솔 확인 (F12)
- 6개월 미만 신규 상장 종목은 데이터 부족으로 제외될 수 있음

---

## ▸ REC 탭 (Recommendation Integration)

우측 사이드바 탭바에 **SIGNAL / MODELS / BACKTEST / REC** 네 번째 탭이 추가되었습니다.

### 데이터 소스 모드

| 모드 | 설명 | 필요 조건 |
|---|---|---|
| **FILE** | `stock_rtx4060_unified/public/dashboard_snapshot.json` 정적 파일 읽기 | 서버 불필요 |
| **API** | `http://127.0.0.1:5151/api/recommend` Flask API 호출 | `api_server.py` 실행 필요 |

- FILE 모드: Vite가 `/dashboard_snapshot.json`을 public 폴더에서 직접 제공
- API 모드: Vite 프록시(`/api` → `:5151`)를 통해 Flask 서버와 통신

### verdict 배지 색상

| 배지 | 의미 |
|---|---|
| 🟢 **ELIGIBLE** | 추천 후보 —门槛 통과 |
| 🟡 **AMBER** | 주의 — 추가 검토 필요 |
| 🔴 **RED** | 비추천 — 조건 미충족 |
| ⚫ **ZERO** | 즉시 차단 — Risk Plan 실패 등 |

### 필터 / 정렬

- **필터 탭**: ALL / GREEN / AMBER / RED
- **정렬**: SCORE 내림차순 (기본) / R/R 내림차순

---

## ▸ Architecture Diagram

```mermaid
flowchart LR
  subgraph Unified["stock_rtx4060_unified"]
    RE[RecommendationEngine] --> DB[dashboard_bridge]
    DB --> SNAP[dashboard_snapshot.json]
    RE --> API[Flask :5151]
  end
  subgraph Dashboard["stock-pred-v5"]
    Vite[Vite :5173] --> Proxy[/api proxy]
    Proxy --> API
    Vite --> REC[REC tab]
    REC --> RP[RecommendationPanel]
    RP --> RC[RecommendationCard]
    RC --> RGB[RiskGateBadge]
  end
  SNAP -.->|"FILE mode"| RP
  API -.->|"API mode"| RP
```

---

## ▸ 통합 프리뷰 서버 (Option C)

`stock_rtx4060_unified` 패키지에서 두 서버를 한 번에 실행:

```bash
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.venv\Scripts\python.exe preview_server.py
```

- Flask API server → http://127.0.0.1:5151
- Vite dev server → http://localhost:5173
- 브라우저 자동 열림

개별 실행:
- API만: `python api_server.py --port 5151`
- 대시보드만: `cd stock-pred-v5 && npm run dev`

---

## ▸ 환경 설정

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `VITE_API_URL` | Flask API 서버 URL (REC 탭 API 모드) | `http://127.0.0.1:5151` |
| `VITE_DEFAULT_CURRENCY` | 기본 통화 표시 | `USD` |

.env 파일을 프로젝트 루트에 생성:
```bash
VITE_API_URL=http://127.0.0.1:5151
VITE_DEFAULT_CURRENCY=USD
```

---

## ▸ 라이선스 / 크레딧

- Personal use · MACHO-GPT v4.5 architecture
- HVDC Project · Samsung C&T Logistics — Cha

---

## Cross-Project Role

| Upstream Source | Relationship | Interface |
|-----------------|-------------|-----------|
| stock_rtx4060_unified | Recommendation data source | dashboard_snapshot.json (FILE) or Flask /api/recommend (API) |

stock-pred-v5 fetches algorithm-generated stock-candidate recommendations from stock_rtx4060_unified via the **REC tab** in the right sidebar. Two modes:
- **FILE mode**: fetches `/dashboard_snapshot.json` — no server needed
- **API mode**: fetches `/api/recommend` via Vite proxy → Flask `127.0.0.1:5151`

## System Flow (with stock_rtx4060_unified)

```mermaid
flowchart LR
    subgraph Unified["stock_rtx4060_unified"]
        RE[RecommendationEngine] --> DB[dashboard_bridge]
        DB --> SNAP[dashboard_snapshot.json]
        RE --> API[Flask :5151]
    end
    subgraph Dashboard["stock-pred-v5"]
        Vite[Vite :5173] --> Proxy[/api proxy]
        Proxy --> API
        Vite --> REC["REC tab"]
        REC --> RP[RecommendationPanel]
        RP --> RC[RecommendationCard]
        RC --> RGB[RiskGateBadge]
    end
    SNAP -.->|"FILE mode"| RP
    API -.->|"API mode"| RP
```

## Tech Stack (Updated)

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18.3 + Vite 5.4 | UI + HMR |
| Charts | recharts 2.12 | Signal/MODELS/BACKTEST visualization |
| REC API | Flask 3 + flask-cors | Recommendation REST API (port 5151) |
| ML (price) | Browser-native LR/XGB-sim/LSTM-sim/RNN | Stock price prediction |
| Font | JetBrains Mono | Monospace terminal aesthetic |
