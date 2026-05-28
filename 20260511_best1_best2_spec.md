# Spec: BEST 1 + BEST 2 High-Class Algo Dashboard

**Date**: 2026-05-11
**Approved Scope**: BEST 1, BEST 2
**Source Plan**: `20260511_high-class-algo-dashboard-report.md`
**Reference Brief**: `20260511_plan-doc.md`
**Status**: Draft for review

---

## Summary

이 Spec은 `stock_1901` 대시보드 업그레이드 중 BEST 1과 BEST 2만 계약 범위로 정의한다.

이 Spec은 사용자가 제공한 로컬 PC 사양에 맞춰 BEST 2의 Transformer Alpha 범위를 조정한다.

BEST 1은 정적 Recharts 차트를 TradingView Lightweight Charts와 WebSocket 기반 실시간 차트로 바꾸는 작업이다.

BEST 2는 기존 LightGBM/XGBoost 신호에 Transformer Alpha 채널을 추가하는 작업이다.

BEST 3인 Black-Litterman + LLM View 연결은 이번 승인 범위에서 제외한다.

자동 주문 실행도 이번 범위에서 제외한다.

---

## User Scenarios & Testing

### US-001: 실시간 캔들차트 확인

사용자는 대시보드에서 실시간 가격 흐름을 캔들차트로 확인해야 한다.

Acceptance scenario:

- Given `ENABLE_REALTIME_CHART=true`이다.
- And WebSocket 또는 mock quote stream이 사용 가능하다.
- When 사용자가 대시보드를 연다.
- Then TradingView Lightweight Charts 기반 차트가 표시된다.
- And WebSocket 상태가 `Connected`, `Reconnecting`, `Error` 중 하나의 텍스트로 표시된다.
- And 가격 업데이트가 들어오면 차트 데이터가 갱신된다.

Independent testability:

- `test_realtime_bridge.py`에서 mock quote가 서버 이벤트로 전달되는지 확인한다.
- 프론트엔드 테스트 또는 브라우저 확인에서 차트 컨테이너와 상태 텍스트를 확인한다.

### US-002: 실시간 차트 장애 시 기존 흐름 유지

사용자는 실시간 연결이 실패해도 대시보드가 완전히 멈추지 않아야 한다.

Acceptance scenario:

- Given `ENABLE_REALTIME_CHART=false`이거나 WebSocket 연결이 실패한다.
- When 사용자가 대시보드를 연다.
- Then 기존 REST polling 또는 기존 차트 흐름으로 fallback한다.
- And 화면에는 장애 상태가 텍스트로 표시된다.

Independent testability:

- feature flag를 끈 상태에서 기존 차트 또는 fallback 화면이 표시되는지 확인한다.
- WebSocket disconnect mock에서 `Reconnecting` 또는 `Error` 상태가 표시되는지 확인한다.

### US-003: Transformer Alpha 신호 확인

사용자는 기존 LightGBM/XGBoost 신호에 더해 Transformer 기반 방향성 신호를 확인해야 한다.

Acceptance scenario:

- Given `ENABLE_TRANSFORMER=true`이다.
- And Transformer Alpha 모델 또는 mock predictor가 사용 가능하다.
- When 대시보드가 특정 ticker의 알고리즘 신호를 요청한다.
- Then `down`, `neutral`, `up` 방향 확률이 계산된다.
- And 기존 LightGBM/XGBoost 신호와 함께 앙상블 신호가 표시된다.

Independent testability:

- `test_transformer_alpha.py`에서 Transformer 출력 shape이 `(batch, 3)`인지 확인한다.
- no-lookahead 검증으로 훈련 구간과 검증 구간이 섞이지 않는지 확인한다.

### US-004: Transformer 장애 시 LightGBM 단독 유지

사용자는 Transformer가 실패해도 기존 모델 신호를 계속 확인해야 한다.

Acceptance scenario:

- Given `ENABLE_TRANSFORMER=false`이거나 Transformer 추론이 실패한다.
- When 대시보드가 알고리즘 신호를 요청한다.
- Then LightGBM/XGBoost 기반 기존 신호가 유지된다.
- And 화면에는 Transformer 비활성 또는 fallback 상태가 표시된다.

Independent testability:

- feature flag를 끈 상태에서 기존 신호 응답이 유지되는지 확인한다.
- Transformer 예외 mock에서 LightGBM fallback 결과가 반환되는지 확인한다.

### US-005: 스크리닝 전용 안전 표시 유지

사용자는 화면의 신호가 자동 주문이 아니라 스크리닝용임을 항상 알아야 한다.

Acceptance scenario:

- Given BEST 1 또는 BEST 2 기능이 켜져 있다.
- When 사용자가 대시보드를 연다.
- Then `SCREENING ONLY` 표시가 화면에 보인다.
- And 추천 결과에는 `screening_output_only=True` 기준이 유지된다.

Independent testability:

- 브라우저 확인 또는 프론트엔드 테스트에서 `SCREENING ONLY` 텍스트를 확인한다.
- API 응답 또는 snapshot 검증에서 `screening_output_only=True` 유지 여부를 확인한다.

---

## Requirements

### Functional Requirements

| ID | Requirement | Trace |
|----|-------------|-------|
| FR-001 | 대시보드는 `ENABLE_REALTIME_CHART`가 켜졌을 때 TradingView Lightweight Charts 기반 캔들차트를 표시해야 한다. | US-001 |
| FR-002 | 대시보드는 WebSocket 상태를 색상만이 아니라 텍스트로 표시해야 한다. | US-001, US-002 |
| FR-003 | 실시간 연결 실패 또는 `ENABLE_REALTIME_CHART=false` 상태에서는 기존 REST polling 또는 기존 차트 흐름으로 fallback해야 한다. | US-002 |
| FR-004 | 실시간 차트는 ticker와 timeframe 선택을 지원해야 한다. | US-001 |
| FR-005 | `ENABLE_TRANSFORMER=true` 상태에서는 Transformer Alpha가 `down`, `neutral`, `up` 방향 확률을 반환해야 한다. | US-003 |
| FR-006 | Transformer Alpha 출력은 기존 LightGBM/XGBoost 신호와 함께 표시되어야 한다. | US-003 |
| FR-007 | Transformer 실패 또는 `ENABLE_TRANSFORMER=false` 상태에서는 기존 LightGBM/XGBoost 신호가 유지되어야 한다. | US-004 |
| FR-008 | `SCREENING ONLY` 표시는 BEST 1, BEST 2 기능 상태와 무관하게 유지되어야 한다. | US-005 |
| FR-009 | 추천 결과 또는 dashboard snapshot은 `screening_output_only=True` 기준을 유지해야 한다. | US-005 |

### Non-Functional Requirements

| ID | Requirement | Trace |
|----|-------------|-------|
| NFR-001 | 신규 기능은 feature flag로 독립적으로 켜고 끌 수 있어야 한다. | FR-001, FR-005 |
| NFR-002 | WebSocket 상태 표시는 색상에만 의존하지 않아야 한다. | FR-002 |
| NFR-003 | Transformer 검증은 lookahead를 허용하지 않아야 한다. | FR-005 |
| NFR-004 | API 키와 토큰은 문서와 코드에 하드코딩하지 않아야 한다. | BEST 1 |
| NFR-005 | `[NEEDS CLARIFICATION: 성능 수치]` 차트 지연, 초기 로드, Transformer 추론 시간 목표는 구현 전 측정 기준을 확정해야 한다. | BEST 1, BEST 2 |
| NFR-006 | 기존 테스트 커버리지 기준은 낮추지 않아야 한다. | BEST 1, BEST 2 |
| NFR-007 | Transformer Alpha는 NVIDIA GeForce RTX 4060 Laptop GPU 8GB VRAM 기준으로 작은 모델부터 검증해야 한다. | BEST 2 |
| NFR-008 | 32GB RAM 환경을 기준으로 batch size와 dataloader worker 수를 제한해야 한다. | BEST 2 |
| NFR-009 | BEST 2 작업 저장 공간은 100GB 예산으로 산정하고, MLflow artifact, cache, checkpoint가 이 예산을 넘지 않게 관리해야 한다. | BEST 2 |
| NFR-010 | Intel UHD Graphics는 Transformer 학습 대상으로 사용하지 않는다. | BEST 2 |

### Out of Scope

- BEST 3: Black-Litterman + LLM View 연결
- 자동 주문 실행
- 브로커 live 주문 전송
- RL 포트폴리오 실행 에이전트
- 주문북 depth chart
- 유료 데이터 구독 전제 기능
- FinBERT 감성 분석

---

## Assumptions & Dependencies

### Assumptions

- Assumption: BEST 1과 BEST 2는 사용자가 승인했다.
- Assumption: BEST 3은 이번 Spec에서 제외한다.
- Assumption: 실시간 데이터는 먼저 paper 계좌 또는 mock stream으로 검증한다.
- Assumption: 기존 LightGBM/XGBoost 신호 흐름은 유지한다.
- Assumption: Transformer Alpha는 기존 신호를 대체하지 않고 보강한다.
- Assumption: 참조 문서의 성능 수치와 일정은 확정 목표가 아니라 후보 기준이다.
- Assumption: 사용자가 제공한 PC 사양은 13th Gen Intel Core i5-13500HX, RAM 32GB, NVIDIA GeForce RTX 4060 Laptop GPU 8GB, Intel UHD Graphics 128MB, x64 Windows 환경이다.
- Assumption: BEST 2 작업 저장 공간은 사용자 지시에 따라 100GB 예산으로 산정한다.
- Assumption: 제품 ID와 장치 ID는 실행 사양 결정에 필요하지 않으므로 Spec에 저장하지 않는다.

### Local Hardware Profile

| Item | Value | Spec Decision |
|------|-------|---------------|
| CPU | 13th Gen Intel Core i5-13500HX, 2.50GHz | 데이터 전처리와 fallback 추론에 사용한다. |
| RAM | 32.0GB, 31.7GB 사용 가능 | batch size를 보수적으로 시작한다. |
| GPU 1 | NVIDIA GeForce RTX 4060 Laptop GPU, 8GB | Transformer Alpha의 1차 학습과 추론 대상으로 사용한다. |
| GPU 2 | Intel UHD Graphics, 128MB | 학습 대상으로 사용하지 않는다. |
| Storage | BEST 2 작업 예산 100GB | checkpoint, MLflow artifact, cache를 100GB 안에서 관리한다. |
| System type | 64-bit OS, x64 processor | PyTorch x64 Windows 환경을 전제로 한다. |

### Hardware-Fit Transformer Profile

| Setting | Required Starting Point | Reason |
|---------|-------------------------|--------|
| Training mode | GPU 우선, CPU fallback 유지 | RTX 4060 Laptop GPU 8GB를 활용하되 CUDA 실패 시 중단하지 않는다. |
| Model size | small encoder-first profile | 8GB VRAM에서 안정성을 우선한다. |
| Batch size | start small, then increase only after memory check | RAM 32GB와 VRAM 8GB에서 OOM을 피한다. |
| HPO | initial implementation excludes full HPO | 저장 공간과 실행 시간을 먼저 통제한다. |
| Checkpoints | keep last, best, and approved comparison checkpoints only | 100GB 예산 안에서 재현성과 저장량을 함께 관리한다. |
| MLflow artifacts | log compact metrics first; store model artifacts only for approved runs | 불필요한 대형 artifact 누적을 막는다. |
| Data scope | smoke or limited universe first | 구현 검증과 장시간 학습을 분리한다. |

### Dependencies

- TradingView Lightweight Charts
- WebSocket 또는 Socket.IO 계층
- Alpaca paper 계좌 또는 mock quote stream
- PyTorch
- NVIDIA CUDA 사용 가능 여부 확인
- 기존 LightGBM/XGBoost 모델 흐름
- MLflow artifact 기록 흐름
- 기존 대시보드 실행 환경

### Open Questions

| ID | Question | Impact |
|----|----------|--------|
| OQ-001 | Alpaca는 paper 계좌로 진행하는가, live 계좌도 필요한가? | BEST 1 데이터 연결 범위 결정 |
| OQ-002 | 현재 PATH의 Python 3.14에는 PyTorch가 설치되어 있지 않다. NVIDIA driver는 RTX 4060 Laptop GPU와 CUDA 13.1을 노출한다. PyTorch CUDA 인식은 PyTorch 설치 후 재확인해야 한다. | BEST 2 GPU 학습 가능 여부 결정 |
| OQ-003 | 성능 목표를 참조 문서의 `<400ms`, `<200ms`, `AUC >= 0.65`로 확정할 것인가? | Success Criteria 확정 |
| OQ-004 | Transformer Alpha는 full HPO 없이 small profile 검증부터 시작하는가? | BEST 2 작업 크기 결정 |
| OQ-005 | frontend 경로는 현재 repo 실제 구조 기준으로 다시 확정해야 하는가? | 테스트 파일과 컴포넌트 위치 결정 |

### Clarifications Log

| Date | Clarification |
|------|---------------|
| 2026-05-11 | 사용자가 BEST 1, BEST 2를 승인했다. |
| 2026-05-11 | BEST 3은 이번 Spec 범위에서 제외했다. |
| 2026-05-11 | 사용자가 로컬 PC 사양을 제공했다: i5-13500HX, RAM 32GB, RTX 4060 Laptop GPU 8GB, Intel UHD Graphics 128MB, x64 Windows. |
| 2026-05-11 | 사용자가 BEST 2 작업 저장 공간을 100GB로 산정하라고 지시했다. |
| 2026-05-11 | 현재 PATH Python은 `C:\Python314\python.exe`이고 PyTorch import는 `ModuleNotFoundError: No module named 'torch'`로 실패했다. |
| 2026-05-11 | `nvidia-smi`는 RTX 4060 Laptop GPU 8GB, Driver 592.27, CUDA 13.1을 확인했다. |

---

## Success Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| SC-001 | `ENABLE_REALTIME_CHART=true`에서 실시간 차트 컨테이너와 WebSocket 상태 텍스트가 표시된다. | 프론트엔드 테스트 또는 브라우저 확인 |
| SC-002 | WebSocket mock quote가 들어오면 차트 데이터 갱신 경로가 실행된다. | `test_realtime_bridge.py` |
| SC-003 | `ENABLE_REALTIME_CHART=false`에서 기존 차트 또는 REST fallback 흐름이 유지된다. | feature flag 테스트 |
| SC-004 | `SCREENING ONLY` 표시가 BEST 1 화면에서 유지된다. | 브라우저 확인 또는 프론트엔드 테스트 |
| SC-005 | Transformer Alpha는 입력 batch에 대해 3개 방향 class를 반환한다. | `test_transformer_alpha.py::test_forward_shape` |
| SC-006 | Transformer 검증은 lookahead 없이 훈련 구간과 검증 구간을 분리한다. | `test_transformer_alpha.py::test_no_lookahead` |
| SC-007 | `ENABLE_TRANSFORMER=false`에서 기존 LightGBM/XGBoost 신호가 유지된다. | feature flag 테스트 |
| SC-008 | Transformer 실패 시 LightGBM fallback 결과가 반환된다. | 예외 mock 테스트 |
| SC-009 | 추천 결과 또는 dashboard snapshot에서 `screening_output_only=True`가 유지된다. | API 또는 snapshot 테스트 |
| SC-010 | 코드 구현 후 Python 테스트와 프론트엔드 검증 명령이 결과 요약과 함께 보고된다. | 완료 보고서 |
| SC-011 | Transformer Alpha 구현은 RTX 4060 Laptop GPU 8GB 기준 small profile에서 먼저 실행된다. | GPU smoke test 또는 fallback test |
| SC-012 | 학습 산출물은 100GB 작업 예산 안에서 checkpoint와 artifact 저장량을 관리한다. | artifact directory size check |
| SC-013 | PyTorch 설치 후 CUDA를 사용할 수 없으면 CPU fallback 또는 LightGBM-only fallback이 동작한다. | CUDA unavailable mock 또는 runtime check |

---

## Reviewer Checklist

- [ ] BEST 1과 BEST 2만 포함되어 있다.
- [ ] BEST 3이 범위 밖으로 명시되어 있다.
- [ ] 모든 기능 요구사항에 stable ID가 있다.
- [ ] Success Criteria가 테스트 가능한 형태다.
- [ ] 미확정 성능 수치가 확정 목표처럼 쓰이지 않았다.
- [ ] `SCREENING ONLY`와 `screening_output_only=True` 안전 기준이 남아 있다.
- [ ] feature flag fallback 기준이 포함되어 있다.
- [ ] RTX 4060 Laptop GPU 8GB와 RAM 32GB 기준의 작은 Transformer 프로필이 포함되어 있다.
- [ ] BEST 2 작업 저장 공간 100GB 기준이 포함되어 있다.
- [ ] Open Questions가 구현 전 결정 항목으로 남아 있다.

---

## Approval Readiness

현재 Spec은 BEST 1, BEST 2 구현 검토용 초안으로 사용할 수 있다.

단, OQ-001, OQ-002, OQ-003은 구현 전에 답해야 한다.

이 3개가 미확정이면 데이터 연결 방식, CUDA 사용 여부, 성능 기준이 흔들릴 수 있다.
