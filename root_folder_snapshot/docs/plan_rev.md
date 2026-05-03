**목적:** Windows i5-13500HX + RTX 4060 환경에서 Track-S 단타, Track-L 장기, Risk Gate, GPU 예측/백테스트, 리포트 출력을 하나의 실행 가능한 투자 OS로 구축한다.

# Plan 문서 재작성본 — `stock_rtx4060` 투자 OS 구축 및 운영

확인 문서: 원본 투자 운영 메모, 기존 `plan.md`, `SETUP.md`, `uiux.md`를 기준으로 재작성했다.    

---

## 1. Overview

### 사용자 요청사항

문서를 확인한 뒤, 투자 운영 구조와 Windows/GPU 실행환경을 반영한 **Plan 문서**를 다시 작성한다.

### 관찰한 사실

| 구분       | 관찰                                                                                                                        |
| -------- | ------------------------------------------------------------------------------------------------------------------------- |
| 투자 운영    | 문서의 핵심 구조는 **Track-S 단타 + Track-L 장기 + 공통 Risk Gate**이다.                                                                  |
| 목표       | Track-S는 1개월 +10.00% 목표, Track-L은 3년 이상 +20.00% 목표로 제시되어 있다.                                                              |
| 실행환경     | `SETUP.md`는 Windows, i5-13500HX, RTX 4060 Laptop, Python 3.11, TensorFlow, XGBoost GPU, Ollama 병행 실행을 전제로 한다.             |
| 코드 구조    | `stock_rtx4060/` 폴더 아래 `hw_profile.py`, `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `main.py` 구조가 제시되어 있다. |
| UI/UX 범위 | `uiux.md`는 별도 화면 와이어프레임보다는 Daily Brief, Risk Dashboard, 후보 출력표, Journal, Monthly Scorecard 중심의 출력 구조를 담고 있다.              |

### 핵심 수정사항

| 항목          | 수정 방향                                                                                                                                                                                               |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 기존 Plan 한계  | 투자 운영 중심이었고, `SETUP.md`의 Windows/GPU 구축 단계가 충분히 통합되지 않았다.                                                                                                                                           |
| 이번 Plan 기준  | 투자 Rule, GPU 모델 파이프라인, 백테스트, 리포트 출력을 하나의 실행 계획으로 통합한다.                                                                                                                                              |
| 환경 리스크      | TensorFlow 공식 문서는 Windows Native에서 TensorFlow 2.10 이후 GPU 지원이 중단되었고, TensorFlow GPU는 Windows WSL2 경로를 요구한다고 명시한다. 따라서 `SETUP.md`의 PowerShell 기반 TensorFlow GPU 설치는 실행 전 검증이 필요하다. ([TensorFlow][1]) |
| XGBoost GPU | XGBoost 공식 문서는 CUDA 12.0 및 Compute Capability 5.0 이상을 GPU 사용 조건으로 제시하고, NVIDIA GPU 환경에서 `device=cuda:0` 기반 GPU 알고리즘을 지원한다고 설명한다. ([XGBoost Documentation][2])                                       |

### 가정

| 가정    | 내용                                                                                            |
| ----- | --------------------------------------------------------------------------------------------- |
| 총 투자금 | 문서 예시값인 **100,000.00 AED** 기준으로 작성한다. 실제 금액이 다르면 비율만 적용한다.                                    |
| 실행 목적 | 예측 결과를 자동매매에 연결하지 않고, **의사결정 보조 + 백테스트 + 리포트**로 제한한다.                                         |
| UI/UX | 신규 웹앱이나 모바일앱이 아니라, 문서에 명시된 후보표·대시보드·리포트 출력으로 제한한다.                                            |
| 실행환경  | 기본은 `SETUP.md` 기준 Windows 환경이나, TensorFlow GPU가 Windows Native에서 인식되지 않으면 WSL2 검증을 필수 단계로 둔다. |

---

## 2. Goals

| 구분         | 목표                                                         | 기준                                        |
| ---------- | ---------------------------------------------------------- | ----------------------------------------- |
| 투자 운영 목표   | Track-S와 Track-L 분리 운영                                     | 단타 손실이 장기 포트폴리오를 침식하지 않도록 분리              |
| Track-S 목표 | 1개월 +10.00%                                                | 보장 수익률이 아니라 익절 Gate                       |
| Track-L 목표 | 3년 이상 +20.00%                                              | 약 6.27% CAGR 목표                           |
| Risk 목표    | 손실 제한 우선                                                   | 손절, 월간 중단, 포지션 크기 제한                      |
| 구현 목표      | RTX 4060 기반 예측/백테스트 파이프라인 구축                               | XGBoost-GPU + LSTM-FP16 + Walk-Forward CV |
| 검증 목표      | `python main.py self-test` 통과                              | 모든 핵심 모듈 검증                               |
| 리포트 목표     | Daily Brief, Risk Dashboard, Journal, Monthly Scorecard 출력 | 의사결정 기록과 사후 검토 가능                         |

---

## 3. Scope

### In Scope

| 영역         | 포함 내용                                                                                  |
| ---------- | -------------------------------------------------------------------------------------- |
| Track-S 단타 | 진입 Score, 손절, 익절, Position Sizing, 월간 손실 중단                                            |
| Track-L 장기 | Core, Quality, AI/Infra, Commodity/Energy, Bonds/Cash 배분                               |
| Risk Gate  | Green / Amber / Red / ZERO 기준                                                          |
| Windows 설치 | Python 3.11, venv, CUDA 확인, TensorFlow, XGBoost, yfinance, pandas, numpy 등             |
| GPU 최적화    | RTX 4060 VRAM 제한, Ollama 병행 시 `--lite` 실행                                              |
| 모델 파이프라인   | `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `main.py`                   |
| 백테스트       | Kelly sizing, Walk-Forward CV, 성능 비교                                                   |
| 출력물        | Daily Brief, Risk Dashboard, Track-S Journal, Track-L Thesis Report, Monthly Scorecard |
| 실행 명령      | AAPL, 005930.KS, NVDA, TSLA 예측 명령                                                      |

### Out of Scope

| 항목                      | 제외 사유                                                             |
| ----------------------- | ----------------------------------------------------------------- |
| 특정 종목 매수/매도 추천          | 투자금, 시장, 계좌, 세금, 위험성향 미확정                                         |
| 자동매매 주문 실행              | 주문 승인 Rule, 브로커 API, 장애 대응, 로그 체계 미확정                             |
| Margin 초기 사용            | 문서상 고위험 항목이며, FINRA도 잦은 margin trading은 고위험이라고 설명한다. ([FINRA][3]) |
| Options / 0DTE          | 문서상 초기 금지 항목                                                      |
| Penny stock / 유동성 부족 종목 | 거래정지, 스프레드, 급락 위험                                                 |
| 신규 웹/모바일 UI 개발          | `uiux.md`에 구체적 화면 설계가 확정되어 있지 않음                                  |
| 별도 데이터베이스 구축            | 문서에 DB 구조가 확정되어 있지 않음                                             |
| 세무·법률 자문                | 관할권과 개인 조건 미확정                                                    |

---

## 4. Constraints

| 구분             | 제약                                                                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 자금 분리          | Track-S 손실이 Track-L 장기 자금을 침식하면 안 된다.                                                                                                                                                 |
| 단타 월간 손실 제한    | Track-S 월간 손실 **-5.00%** 도달 시 해당 월 거래를 중단한다.                                                                                                                                          |
| 단타 손절          | 기본 손절 **-4.00%**, Hard Stop **-5.00% 초과 손실 금지**.                                                                                                                                      |
| 단타 진입          | Score **75.00점 이상**일 때만 진입 후보로 본다.                                                                                                                                                    |
| 장기 진입          | Score **80.00점 이상**일 때만 신규 편입 후보로 본다.                                                                                                                                                 |
| 장기 리밸런싱        | 반기 1회 또는 비중 ±5.00% 이탈 시 검토한다.                                                                                                                                                         |
| 단일 종목 집중       | 장기 포트폴리오 내 단일 종목 **12.00% 초과 시 리밸런싱 검토**.                                                                                                                                             |
| 자동화            | AI 예측값만으로 자동매수하지 않는다.                                                                                                                                                                 |
| TensorFlow GPU | Windows Native에서 TensorFlow 2.16.1 GPU가 인식되지 않을 수 있으므로 GPU 검증을 필수 Gate로 둔다. TensorFlow 공식 문서는 Windows Native GPU 지원이 TensorFlow 2.10에서 종료되었고, 이후 버전은 WSL2 사용을 안내한다. ([TensorFlow][1]) |
| XGBoost GPU    | CUDA 12.0 및 Compute Capability 5.0 이상 조건을 충족해야 한다. ([XGBoost Documentation][2])                                                                                                       |
| 성능 벤치마크        | `SETUP.md`의 벤치마크 수치는 문서 내 기준값이므로 실제 장비에서 재측정한다.                                                                                                                                       |

---

## 5. Phases

### Phase 1 — 기준선 확정

| 항목  | 내용                                  |
| --- | ----------------------------------- |
| 목적  | 투자 운영 범위와 구현 범위를 혼합하지 않고 기준선을 확정한다. |
| 입력  | `plan.md`, `uiux.md`, `SETUP.md`    |
| 산출물 | 확정 Scope, Out of Scope, 가정 목록       |

### Phase 2 — Windows / GPU 실행환경 구축

| 항목 | 내용                                                              |
| -- | --------------------------------------------------------------- |
| 목적 | RTX 4060 Laptop에서 모델 학습과 백테스트가 가능한 환경을 만든다.                     |
| 기준 | Python 3.11, venv, TensorFlow, XGBoost, yfinance, pandas, numpy |
| 검증 | `nvidia-smi`, TensorFlow GPU 확인, XGBoost 버전 확인                  |

### Phase 3 — 코드 구조 정리

| 항목    | 내용                                                                                    |
| ----- | ------------------------------------------------------------------------------------- |
| 목적    | `stock_rtx4060/` 구조를 기준으로 구현 파일을 정리한다.                                                |
| 기준 파일 | `hw_profile.py`, `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `main.py` |
| 제한    | 새 폴더 구조를 확정하지 않는다. 필요 시 후속 승인 항목으로 둔다.                                                |

### Phase 4 — Track-S / Track-L Rule 구현

| 항목      | 내용                                         |
| ------- | ------------------------------------------ |
| 목적      | 투자 운영 Rule을 코드와 리포트 기준으로 변환한다.             |
| Track-S | 단타 Score, Entry, Stop, TP, Position Sizing |
| Track-L | 장기 Bucket, Score, DCA, Exit Rule           |
| 공통      | Risk Gate, Journal, Monthly Review         |

### Phase 5 — 모델·백테스트 파이프라인 구현

| 항목 | 내용                                              |
| -- | ----------------------------------------------- |
| 목적 | 피처 생성, XGBoost-GPU, LSTM-FP16, 백테스트를 연결한다.      |
| 기준 | 30종 지표, 16 워커 병렬, Kelly sizing, Walk-Forward CV |
| 제한 | 예측값은 매수/매도 자동 실행이 아니라 후보 평가에만 사용한다.             |

### Phase 6 — 리포트 / 출력 포맷 구현

| 항목       | 내용                                                                                     |
| -------- | -------------------------------------------------------------------------------------- |
| 목적       | 사용자가 매일·매주·매월 검토할 수 있는 출력물을 만든다.                                                       |
| 출력       | Daily Brief, Risk Dashboard, Track-S Journal, Track-L Thesis Report, Monthly Scorecard |
| UI/UX 기준 | 문서에 제시된 표 기반 출력 포맷을 우선 사용한다.                                                           |

### Phase 7 — 운영 전환 검증

| 항목    | 내용                                                                              |
| ----- | ------------------------------------------------------------------------------- |
| 목적    | 테스트 명령과 샘플 티커 실행으로 운영 가능성을 확인한다.                                                |
| 기준 명령 | `python main.py self-test`, `python main.py predict --ticker AAPL --horizon 5 --period 5y` |
| 완료 조건 | 테스트 통과, GPU/CPU 경로 확인, 리포트 출력 확인                                                |

---

## 6. Tasks

### Phase 1 Tasks — 기준선 확정

| No | Task                       | 완료 기준                                                    |
| -: | -------------------------- | -------------------------------------------------------- |
|  1 | 문서별 역할 구분                  | `plan.md`는 운영 Rule, `SETUP.md`는 환경, `uiux.md`는 출력 구조로 분리 |
|  2 | In Scope / Out of Scope 확정 | 자동매매, 특정 종목 추천, 신규 UI 개발 제외                              |
|  3 | 가정 목록 작성                   | 투자금, 시장, 실행환경, UI/UX 범위 명시                               |
|  4 | 기존 Plan 중복 제거              | 투자 운영과 구현 계획이 중복되지 않도록 정리                                |

### Phase 2 Tasks — Windows / GPU 실행환경

| No | Task              | 완료 기준                                                                         |
| -: | ----------------- | ----------------------------------------------------------------------------- |
|  1 | CUDA 상태 확인        | `nvidia-smi` 실행 결과 기록                                                         |
|  2 | Python 3.11 설치    | `winget install Python.Python.3.11` 완료                                        |
|  3 | venv 생성           | `.venv` 생성 및 PowerShell 활성화                                                   |
|  4 | 패키지 설치            | TensorFlow, XGBoost, yfinance, pandas, numpy, scikit-learn, joblib, psutil 설치 |
|  5 | TensorFlow GPU 검증 | `tf.config.list_physical_devices('GPU')` 결과 기록                                |
|  6 | XGBoost 검증        | `xgboost.__version__` 확인                                                      |
|  7 | GPU 미인식 시 Gate 처리 | Windows Native 문제인지 확인하고 WSL2 경로 검토 항목으로 분리                                   |

### Phase 3 Tasks — 코드 구조 정리

| No | Task                   | 완료 기준                      |
| -: | ---------------------- | -------------------------- |
|  1 | `stock_rtx4060/` 폴더 생성 | SETUP 기준 폴더 구조 반영          |
|  2 | `hw_profile.py` 작성     | VRAM 제한값 설정 함수 포함          |
|  3 | `feature_engine.py` 작성 | 30종 지표 및 병렬 피처 생성 구조       |
|  4 | `ensemble_model.py` 작성 | XGBoost-GPU + LSTM-FP16 구조 |
|  5 | `backtester.py` 작성     | Kelly sizing + 백테스트 구조     |
|  6 | `main.py` 작성           | CLI 실행, 테스트, 티커별 예측 흐름 포함  |

### Phase 4 Tasks — Track-S / Track-L Rule

| No | Task                       | 완료 기준                                                      |
| -: | -------------------------- | ---------------------------------------------------------- |
|  1 | Track-S Score 정의           | Market Regime, Relative Strength, Volume, Catalyst, R/R 반영 |
|  2 | Track-S Entry/Exit 정의      | Entry, Stop -4.00%, TP1 +5.00%, TP2 +10.00%                |
|  3 | Track-S Position Sizing 정의 | 1회 risk 0.50%~1.00% 기준                                     |
|  4 | Track-L Bucket 정의          | Core, Quality, AI/Infra, Commodity/Energy, Bonds/Cash      |
|  5 | Track-L Score 정의           | Business Quality, Earnings, Balance Sheet, Valuation 등     |
|  6 | Risk Gate 정의               | Green / Amber / Red / ZERO 기준 적용                           |
|  7 | Fail-safe 정의               | 손절 없는 매수, Margin, Options/0DTE, 자동매수 금지                    |

### Phase 5 Tasks — 모델·백테스트

| No | Task            | 완료 기준                   |
| -: | --------------- | ----------------------- |
|  1 | OHLCV 데이터 로딩    | yfinance 기반 티커 데이터 수집   |
|  2 | 피처 생성           | 30종 지표 생성 및 결측 처리       |
|  3 | XGBoost 학습      | GPU 사용 가능 시 CUDA 경로 적용  |
|  4 | LSTM 학습         | FP16 및 Batch 설정 적용      |
|  5 | Walk-Forward CV | 기간별 성능 기록               |
|  6 | Backtest 실행     | Kelly sizing 및 성과 지표 출력 |
|  7 | Lite Mode 적용    | Ollama 병행 시 VRAM 제한 적용  |

### Phase 6 Tasks — 리포트 / 출력

| No | Task                     | 완료 기준                                  |
| -: | ------------------------ | -------------------------------------- |
|  1 | Daily Brief 출력           | 후보, Score, Entry, Stop, TP, Verdict 표시 |
|  2 | Risk Dashboard 출력        | open risk, max drawdown, exposure 표시   |
|  3 | Track-S Journal 출력       | 진입 이유, 손절가, 수량, 결과 기록                  |
|  4 | Track-L Thesis Report 출력 | 보유 이유, 훼손 조건, 리밸런싱 기준 기록               |
|  5 | Monthly Scorecard 출력     | 성과, Rule 위반, 개선 항목 기록                  |

### Phase 7 Tasks — 운영 전환 검증

| No | Task           | 완료 기준                                                          |
| -: | -------------- | -------------------------------------------------------------- |
|  1 | 전체 테스트 실행      | `python main.py self-test` 통과                                  |
|  2 | AAPL 예측 실행     | `python main.py predict --ticker AAPL --horizon 5 --period 5y` 실행 |
|  3 | KRX 예측 실행      | `python main.py predict --ticker 005930.KS --horizon 5 --period 3y` 실행 |
|  4 | NVDA / TSLA 실행 | 문서 기준 명령 실행                                                    |
|  5 | GPU/CPU 성능 기록  | CPU-only, GPU, Lite Mode 결과 비교                                 |
|  6 | 운영 중단 Rule 확인  | Track-S -5.00% 월간 손실 중단 조건 반영                                  |

---

## 7. Risks

| Risk                | 설명                                                                                                                     | 대응                                                                   |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| TensorFlow GPU 미인식  | `SETUP.md`는 Windows PowerShell 설치를 제시하지만, TensorFlow 공식 문서는 TensorFlow 2.11 이후 Windows Native GPU 미지원 및 WSL2 필요를 안내한다. | GPU 검증 Gate를 먼저 수행하고, 실패 시 WSL2 검토 항목으로 분리한다. ([TensorFlow][1])      |
| 버전 충돌               | `tensorflow[and-cuda]==2.16.1`, `xgboost==2.1.0`이 현재 드라이버/CUDA와 충돌할 수 있다.                                              | 패키지 설치 후 GPU 검증 로그를 남긴다.                                             |
| XGBoost CUDA 조건 미충족 | XGBoost GPU는 CUDA 12.0 및 Compute Capability 5.0 이상이 필요하다.                                                              | `nvidia-smi`와 XGBoost GPU 학습 테스트를 실행한다. ([XGBoost Documentation][2]) |
| VRAM 부족             | Ollama 병행 시 TF, XGBoost, LSTM이 VRAM을 경합할 수 있다.                                                                         | `--lite` 플래그와 `configure_gpu(vram_limit_mb=4096)` 적용                 |
| 단타 목표 과도            | 1개월 +10.00%는 공격적 목표이다.                                                                                                 | 수익률 목표가 아니라 익절 Gate로 취급                                              |
| Margin 손실 확대        | Frequent margin trading은 고위험이다.                                                                                        | 초기 Margin 사용 금지. FINRA도 충분한 자본과 손실 감내 가능 자금 사용을 강조한다. ([FINRA][3])   |
| 백테스트 과최적화           | Walk-Forward CV가 약하면 실전 성과와 괴리 가능                                                                                      | 기간별 성능 분리 기록                                                         |
| 자동매매 오용             | 예측값을 주문으로 직접 연결하면 손실 통제가 어려움                                                                                           | 자동매수 금지, 리포트 기반 수동 검토                                                |
| UI/UX 범위 오해         | `uiux.md`는 화면 설계보다 출력 포맷 중심                                                                                            | 신규 프론트엔드 개발은 Out of Scope 유지                                         |

---

## 8. Review Criteria

| 구분            | 검토 기준                                                               |
| ------------- | ------------------------------------------------------------------- |
| 환경 검증         | `nvidia-smi` 실행 결과가 기록되어야 한다.                                       |
| TensorFlow 검증 | GPU 사용 경로에서는 `tf.config.list_physical_devices('GPU')` 결과가 기록되어야 한다. |
| XGBoost 검증    | XGBoost 버전과 GPU 학습 가능 여부가 확인되어야 한다.                                 |
| 테스트 검증        | `python main.py self-test`가 통과해야 한다.                                |
| 샘플 실행         | AAPL, 005930.KS, NVDA, TSLA 명령이 실행되어야 한다.                           |
| Track-S Rule  | Score ≥75.00, Stop -4.00%, TP1 +5.00%, TP2 +10.00% 기준이 반영되어야 한다.    |
| Track-S 손실 제한 | 월간 손실 -5.00% 도달 시 거래 중단 Rule이 반영되어야 한다.                             |
| Track-L Rule  | Score ≥80.00, Bucket 배분, DCA, Exit Rule이 반영되어야 한다.                  |
| Risk Gate     | Green / Amber / Red / ZERO 구분이 출력되어야 한다.                            |
| 리포트           | Daily Brief, Risk Dashboard, Journal, Monthly Scorecard가 생성되어야 한다.  |
| 자동매매 제한       | 예측 결과가 주문 실행으로 직접 연결되지 않아야 한다.                                      |

---

## 9. Deliverables

| Deliverable                | 내용                                                                                    |
| -------------------------- | ------------------------------------------------------------------------------------- |
| Revised Plan 문서            | 본 문서                                                                                  |
| Environment Validation Log | `nvidia-smi`, TensorFlow GPU, XGBoost 버전 확인 결과                                        |
| `stock_rtx4060/` 코드 구조     | `hw_profile.py`, `feature_engine.py`, `ensemble_model.py`, `backtester.py`, `main.py` |
| Track-S Rulebook           | 단타 Score, Entry, Stop, TP, Position Sizing, 월간 손실 중단                                  |
| Track-L Portfolio Policy   | Bucket, Score, DCA, Exit Rule, 리밸런싱 기준                                                |
| Risk Gate Matrix           | Green / Amber / Red / ZERO 기준                                                         |
| Backtest Report            | Kelly sizing, Walk-Forward CV, CPU/GPU 성능 비교                                          |
| Daily Brief                | 단타·장기 후보, Score, Entry, Stop, TP, Verdict                                             |
| Risk Dashboard             | open risk, max drawdown, exposure                                                     |
| Track-S Journal            | 진입 이유, 차트/뉴스 근거, 손절가, 수량, 결과                                                          |
| Track-L Thesis Report      | 보유 이유, 훼손 조건, 리밸런싱 판단                                                                 |
| Monthly Scorecard          | Track-S / Track-L 성과, Rule 위반, 개선 항목                                                  |

---

## 최종 정리

이번 Plan은 단순 투자 계획이 아니라 **Windows RTX 4060 기반 투자 OS 구축 계획**이다. 본문 확정 범위는 Track-S 단타, Track-L 장기, Risk Gate, GPU 예측/백테스트, 리포트 출력까지다. 자동매매, 특정 종목 추천, Margin, Options/0DTE, 신규 웹/모바일 UI는 현재 범위에서 제외한다. TensorFlow GPU는 문서 기준 설치만으로 확정하지 않고, 공식 문서와 충돌 가능성이 있으므로 **GPU 검증 Gate**를 반드시 통과해야 한다.

[1]: https://www.tensorflow.org/install/pip "Install TensorFlow with pip"
[2]: https://xgboost.readthedocs.io/en/stable/gpu/ "XGBoost GPU Support — xgboost 3.2.0 documentation"
[3]: https://www.finra.org/investors/insights/intraday-margin-requirements "Understanding the New Intraday Margin Requirements | FINRA.org"
