# 대시보드 실행 가이드

작성: 2026-05-10 | 프로젝트: `stock_1901`

---

## 전체 구성 요약

```
stock_1901/                ← 백엔드 (Python / Flask)
  api_server.py            ← API 서버  :5151
  .venv/                   ← Python 3.12 가상환경

root_folder_snapshot/
  stock-pred-v5/           ← 프론트엔드 (React / Vite)  :5173
    src/
    public/
      dashboard_config.json
      dashboard_snapshot.json   ← FILE 모드 스냅샷
    dist/                  ← 프로덕션 빌드 결과물
```

대시보드는 **두 가지 모드**로 데이터를 읽습니다.

| 모드 | 데이터 출처 | 사용 시점 |
|---|---|---|
| **API 모드** | Flask API `:5151` 실시간 호출 | 백엔드 서버가 실행 중일 때 |
| **FILE 모드** | `public/dashboard_snapshot.json` 정적 파일 | 오프라인 / 빠른 리뷰 |

---

## 사전 요구사항

| 항목 | 버전 | 확인 명령 |
|---|---|---|
| Python (`.venv`) | 3.12 | `.venv\Scripts\python.exe --version` |
| Node.js | 18 LTS 이상 | `node -v` |
| npm | 9 이상 | `npm -v` |

---

## 1. API 모드 — 실시간 대시보드

### 1-1. 백엔드 API 서버 시작

터미널 A에서 실행:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901
.\.venv\Scripts\python.exe api_server.py --port 5151
```

정상 기동 시 출력:

```
Starting stock_rtx4060 unified API server on http://0.0.0.0:5151
Dashboard: http://localhost:5151/
Endpoints:
  GET /                     — React dashboard (built static)
  GET /api/health           — health check
  GET /api/universe         — dashboard-selectable symbols
  GET /api/symbol           — latest OHLCV for dashboard charts
  GET /api/model-scores     — backend model evidence for one symbol
  GET /api/paper-status     — latest paper-only virtual trading status
```

헬스체크로 확인:

```powershell
curl http://127.0.0.1:5151/api/health
# {"status": "ok", ...}
```

### 1-2. 프론트엔드 개발 서버 시작

터미널 B에서 실행:

```powershell
cd C:\Users\jichu\Downloads\주식\root_folder_snapshot\stock-pred-v5

# 최초 1회만
npm install

# 개발 서버 기동 (자동으로 브라우저 열림)
npm run dev
```

`http://localhost:5173` 이 자동으로 열립니다.
Vite가 `/api/*` 요청을 자동으로 `:5151`로 프록시합니다.

### 1-3. API 모드 확인 포인트

| 항목 | 정상 상태 |
|---|---|
| 백엔드 포트 | `http://127.0.0.1:5151/api/health` → `{"status":"ok"}` |
| 프론트엔드 포트 | `http://localhost:5173` 접속 가능 |
| CORS | Flask가 5173, 4173, 5151 허용 — 별도 설정 불필요 |
| 데이터 소스 표시 | 대시보드 우상단에 "API" 배지 표시 |

---

## 2. FILE 모드 — 스냅샷 대시보드

백엔드 서버 없이 저장된 스냅샷 파일로 대시보드를 볼 수 있습니다.

### 2-1. 스냅샷 생성 (최신 추천 결과)

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901

# 1. 추천 실행 (synthetic 예시)
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" `
    --top 2 --model-kind logistic --cv-gap 5 `
    --output-dir reports\dashboard_snapshot_export

# 2. 스냅샷 내보내기
.\.venv\Scripts\python.exe main.py dashboard-export `
    --recommendation-json reports\dashboard_snapshot_export\recommendations_algo_v2_*.json `
    --output reports\dashboard_snapshot_export\dashboard_snapshot.json `
    --public-dir ..\root_folder_snapshot\stock-pred-v5\public
```

`public/dashboard_snapshot.json` 이 생성/갱신됩니다.

### 2-2. FILE 모드로 프론트엔드 실행

```powershell
cd C:\Users\jichu\Downloads\주식\root_folder_snapshot\stock-pred-v5
npm run dev
```

대시보드에서 **BACKEND 버튼 → FILE** 을 선택하면 스냅샷을 읽습니다.

---

## 3. 프로덕션 빌드 (배포용)

개발 서버 대신 정적 빌드를 사용할 경우:

```powershell
cd C:\Users\jichu\Downloads\주식\root_folder_snapshot\stock-pred-v5
npm run build
# dist/ 에 번들 생성

# 빌드 결과 미리보기 (포트 4173)
npm run preview
```

빌드 후 Flask 서버가 `dist/`를 정적으로 서빙합니다:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901
.\.venv\Scripts\python.exe api_server.py --port 5151
# http://127.0.0.1:5151/ 에서 빌드된 대시보드 직접 서빙
```

---

## 4. 포트 정리

| 포트 | 용도 | 프로세스 |
|---|---|---|
| **5151** | Flask API + 정적 파일 서빙 | `api_server.py` |
| **5173** | Vite 개발 서버 | `npm run dev` |
| **4173** | Vite 프로덕션 프리뷰 | `npm run preview` |

---

## 5. API 엔드포인트 목록

| 메서드 | URL | 설명 |
|---|---|---|
| GET | `/api/health` | 서버 상태 확인 |
| GET | `/api/universe?market=US` | 선택 가능한 종목 목록 |
| GET | `/api/symbol?symbol=AAPL&period=6mo` | OHLCV 차트 데이터 |
| GET | `/api/model-scores?symbol=AAPL` | ML 모델 스코어 및 근거 |
| GET | `/api/recommend?universe=AAPL,MSFT&top=5` | 추천 결과 (screening only) |
| GET | `/api/snapshot` | `dashboard_snapshot.v1` JSON |
| GET | `/api/paper-status` | 페이퍼 트레이딩 가상 상태 |

> 모든 추천 결과는 `screening_output_only=True`. 브로커 주문 실행 없음.

---

## 6. 문제 해결

### 포트 충돌

```powershell
# 5151 포트 점유 프로세스 확인
netstat -ano | findstr :5151
taskkill /PID <PID> /F
```

### npm install 실패

```powershell
cd root_folder_snapshot\stock-pred-v5
Remove-Item -Recurse -Force node_modules
npm install
```

### Flask 의존성 오류

```powershell
cd C:\Users\jichu\Downloads\주식\stock_1901
.\.venv\Scripts\pip install flask flask-cors
# 또는
.\.venv\Scripts\pip install -r requirements.txt
```

### CORS 오류 (브라우저 콘솔)

`api_server.py`의 CORS 허용 목록을 확인합니다:

```python
"origins": [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:5151",
]
```

Vite 포트가 다른 경우(예: 5174) `api_server.py` 상단 CORS 설정에 추가 후 재시작.

### 대시보드가 빈 화면

1. API 모드: `http://127.0.0.1:5151/api/health` 접속 — `{"status":"ok"}` 응답 확인
2. FILE 모드: `public/dashboard_snapshot.json` 존재 여부 확인
3. 브라우저 개발자 도구 콘솔에서 네트워크 오류 메시지 확인

---

## 7. 빠른 시작 체크리스트

```
[ ] 터미널 A: .\.venv\Scripts\python.exe api_server.py --port 5151
[ ] curl http://127.0.0.1:5151/api/health  → {"status":"ok"}
[ ] 터미널 B: cd root_folder_snapshot\stock-pred-v5 && npm run dev
[ ] 브라우저에서 http://localhost:5173 열림 확인
[ ] 대시보드 우상단 데이터 소스 표시 확인 (API / FILE)
```
