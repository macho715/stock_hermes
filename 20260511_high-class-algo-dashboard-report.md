# High-Class Algorithm Dashboard Upgrade Plan

**Date**: 2026-05-11
**Request**: "실제 투자를 위하여, high class의 알고리즘을 갖춘 대시보드로 업그레이드"
**Repository**: `macho715/stock_1901`
**Purpose**: 실제 투자 판단에 쓸 수 있도록 대시보드, Alpha 신호, 포트폴리오 결정 흐름을 단계적으로 강화한다.

---

## Overview

현재 초안의 핵심 방향은 "스크리닝 보고서 조회" 중심의 화면을 "실시간 시그널 확인, 포트폴리오 가중치 검토, 주문 전 수동 확인" 흐름으로 끌어올리는 것이다.

이 Plan은 기존 초안의 BEST 3 범위만 실행 계획으로 정리한다.

참조 문서: `20260511_plan-doc.md`

참조 문서에서 반영한 핵심 기준은 실시간 차트, Transformer Alpha, Black-Litterman + LLM view, `SCREENING ONLY` 안전 표시, feature flag 기반 롤백이다.

Assumption: 기존 초안에 적힌 외부 자료, 일정, KPI 수치는 이 세션에서 다시 검증하지 않았다. 구현 전 별도 확인이 필요하다.

---

## Goals

1. Recharts 기반 정적 차트를 TradingView Lightweight Charts 기반 실시간 차트로 교체할 수 있는 실행 순서를 정한다.
2. 기존 LightGBM/XGBoost Alpha 흐름에 Transformer Alpha 채널을 추가할 수 있는 검토 단계를 만든다.
3. 기존 LLM 어드바이저 점수를 Black-Litterman 포트폴리오 view로 연결하는 계획을 정리한다.
4. 모든 투자 관련 출력은 `screening_output_only=True` 원칙과 수동 승인 흐름을 유지한다.
5. 코드 변경 전 승인, 검증, 롤백 기준을 먼저 확정한다.
6. 사용자가 실제 투자 판단 화면에서 자동 주문과 스크리닝 출력을 혼동하지 않도록 `SCREENING ONLY` 표시 기준을 유지한다.

---

## Scope

### In Scope

- BEST 1: TradingView Lightweight Charts + WebSocket 실시간 가격 스트리밍 계획
- BEST 2: Transformer Alpha 모듈 추가 계획
- BEST 3: Black-Litterman + LLM advisory_score view 주입 계획
- 대시보드 표시 항목과 백엔드 연결 지점 정리
- 기능별 검증 기준과 롤백 기준 정리
- 사용자 승인 전까지 코드 변경을 하지 않는 gate 유지
- `ENABLE_REALTIME_CHART`, `ENABLE_TRANSFORMER`, `ENABLE_LLM_BL` 같은 feature flag 기준 정리
- WebSocket 연결 상태 표시와 장애 시 fallback 기준 정리
- BL 가중치와 advisory_score 매핑 투명성 표시 기준 정리

### Out of Scope

- 자동 주문 실행
- HFT 수준의 초저지연 최적화
- 유료 데이터 구독 전제 기능
- RL 포트폴리오 실행 에이전트
- 주문북 depth chart
- 구현 코드 작성
- 상세 아키텍처 확정
- 운영 로그 또는 실행 결과 보고서 작성

---

## Constraints

- 이 문서는 Plan 문서다. 코드 구현은 포함하지 않는다.
- `screening_output_only=True`를 유지해야 한다.
- 브로커 주문은 수동 승인 gate 이후에만 다룬다.
- API 키와 토큰은 문서에 쓰지 않는다.
- 기존 Flask, React/Vite, MLflow, skfolio, PyTorch 사용 여부는 구현 전 현재 환경에서 다시 확인해야 한다.
- Assumption: Alpaca paper 계좌, PyTorch 설치 상태, RTX 4060 사용 가능 여부는 아직 확정되지 않았다.
- Assumption: 기존 초안의 30/60/90-day 표현은 승인된 일정이 아니라 우선순위 예시다.
- Assumption: KPI 수치는 목표 후보이며, 현재 기준값과 측정 방법을 먼저 확정해야 한다.
- Assumption: 참조 문서의 KPI, 마일스톤, API 계약, 목표 파일 트리는 검증된 실행 결과가 아니라 구현 전 후보 기준이다.

---

## Phases

### Phase 0: Approval Gate

목적은 구현 전 범위와 미확정 항목을 사용자에게 확인받는 것이다.

- BEST 1, BEST 2, BEST 3을 이번 실행 범위로 승인받는다.
- Alpaca 계좌 범위를 paper 또는 live 중 하나로 확인한다.
- PyTorch와 GPU 사용 가능 여부를 확인한다.
- 먼저 시작할 항목을 BEST 1, BEST 2, BEST 3 중 하나로 확정한다.
- 참조 문서의 KPI와 일정 표현을 확정 목표로 쓸지, 후보 목표로 둘지 정한다.

### Phase 1: Real-Time Dashboard Upgrade

목적은 정적 차트와 REST polling 중심 화면을 실시간 차트 흐름으로 바꾸는 것이다.

- 백엔드 실시간 스트리밍 연결 지점을 정리한다.
- React 차트 컴포넌트 교체 범위를 정한다.
- 실시간 가격 업데이트 실패 시 REST fallback 기준을 둔다.
- 캔들스틱, 거래량, 기본 지표 표시 범위를 정한다.
- WebSocket 상태를 Connected, Reconnecting, Error처럼 사용자가 이해할 수 있게 표시하는 기준을 둔다.
- `SCREENING ONLY` 배너가 차트 교체 뒤에도 항상 보이도록 확인한다.

### Phase 2: Transformer Alpha Channel

목적은 기존 Alpha 신호에 Transformer 기반 시계열 채널을 추가할 수 있는지 검증하는 것이다.

- 입력 feature, sequence length, horizon을 확정한다.
- 기존 ensemble 흐름에 추가할 위치를 확인한다.
- MLflow 등록 기준을 정한다.
- no-lookahead 검증 기준을 둔다.

### Phase 3: Black-Litterman + LLM View

목적은 LLM advisory_score를 포트폴리오 weight 산출에 연결하되, 자동 주문으로 이어지지 않게 막는 것이다.

- advisory_score를 Black-Litterman view로 바꾸는 규칙을 확정한다.
- optimizer method 추가 범위를 정한다.
- dashboard snapshot에 BL weight 표시 항목을 추가할지 확인한다.
- compliance gate 이후에만 view를 쓰는 기준을 둔다.
- BL weight 화면에는 기존 HRP 기준선과의 차이를 보여줄지 검토한다.
- advisory_score가 어떤 excess return view로 바뀌었는지 사용자가 볼 수 있는 투명성 기준을 둔다.

### Phase 4: Review And Release Gate

목적은 구현 결과를 투자 판단 화면으로 쓰기 전에 검증 기준을 통과시키는 것이다.

- 핵심 단위 테스트를 통과시킨다.
- 대시보드 화면에서 실제 표시 상태를 확인한다.
- paper 계좌 또는 mock 데이터로 실시간 흐름을 확인한다.
- 롤백 방법을 문서화한다.

---

## Tasks

### Phase 0 Tasks

- [ ] 이번 Plan의 In Scope와 Out of Scope를 사용자에게 확인받는다.
- [ ] Alpaca 사용 범위를 paper 계좌 기준으로 먼저 정한다.
- [ ] PyTorch 설치 상태와 GPU 사용 가능 여부를 확인한다.
- [ ] `screening_output_only=True` 유지 기준을 테스트 항목에 넣는다.
- [ ] 참조 문서의 KPI 수치를 확정 목표로 둘지, 검증 전 후보로 둘지 정한다.
- [ ] 참조 문서의 `Open Questions`를 구현 전 체크리스트로 옮긴다.

### Phase 1 Tasks

- [ ] `api_server.py`에서 실시간 스트리밍을 붙일 위치를 확인한다.
- [ ] WebSocket 연결 실패 시 기존 REST polling으로 돌아가는 기준을 정한다.
- [ ] `src/dashboard` 차트 컴포넌트 교체 범위를 확인한다.
- [ ] TradingView Lightweight Charts 적용 후 캔들스틱과 거래량 표시를 확인한다.
- [ ] 실시간 업데이트 테스트 이름과 실행 명령을 정한다.
- [ ] WebSocket 상태 표시가 색상만이 아니라 텍스트로도 보이는지 확인한다.
- [ ] `SCREENING ONLY` 배너가 실시간 차트 위에서도 유지되는지 확인한다.

### Phase 2 Tasks

- [ ] 기존 LightGBM/XGBoost ensemble 입력과 출력 형태를 확인한다.
- [ ] Transformer Alpha가 사용할 feature shape을 정한다.
- [ ] walk-forward 또는 out-of-fold 검증 흐름에 lookahead가 없는지 확인한다.
- [ ] MLflow artifact 등록 기준을 정한다.
- [ ] CPU fallback 기준을 정한다.

### Phase 3 Tasks

- [ ] advisory_score 범위와 threshold 규칙을 확인한다.
- [ ] Black-Litterman view 변환 규칙을 단위 테스트로 검증한다.
- [ ] optimizer에 새 method를 추가할지, 기존 method 옵션으로 둘지 확정한다.
- [ ] dashboard snapshot에 BL weight를 추가할 때 기존 schema 호환성을 확인한다.
- [ ] 대시보드에서 BL weight를 표시하되 자동 주문으로 이어지지 않는지 확인한다.
- [ ] advisory_score에서 BL view로 바뀌는 매핑을 사용자가 확인할 수 있는 표시 방식을 정한다.

### Phase 4 Tasks

- [ ] Python 단위 테스트를 실행한다.
- [ ] 프론트엔드 테스트 또는 빌드를 실행한다.
- [ ] 브라우저에서 대시보드 화면을 확인한다.
- [ ] 실패 시 기존 차트, 기존 Alpha, 기존 optimizer로 되돌릴 수 있는지 확인한다.
- [ ] 완료 보고서에는 변경 파일, 생성 파일, 테스트명, 실행 명령, 한 줄 결과 요약을 포함한다.
- [ ] 테스트 후보는 `test_transformer_alpha.py`, `test_llm_views.py`, `test_realtime_bridge.py`, `test_bl_wiring.py`에서 구현 범위에 맞춰 선택한다.

---

## Risks

- Alpaca 자격증명이나 계좌 범위가 없으면 실시간 데이터 검증이 mock 또는 paper 기준으로 제한된다.
- Transformer Alpha는 데이터 누수 방지 검증이 부족하면 실제 투자 판단에 잘못된 신호를 줄 수 있다.
- Black-Litterman view 변환 규칙이 과하게 공격적이면 LLM 점수가 포트폴리오 weight에 과도하게 반영될 수 있다.
- 실시간 차트와 WebSocket을 한 번에 바꾸면 기존 REST 기반 대시보드 안정성이 흔들릴 수 있다.
- 기존 초안의 외부 근거와 KPI는 현재 세션에서 재검증하지 않았기 때문에 구현 전 최신성 확인이 필요하다.
- 참조 문서의 세부 API, 파일 트리, 일정은 아직 승인된 구현 범위가 아니므로 그대로 확정하면 범위가 커질 수 있다.

---

## Review Criteria

- In Scope와 Out of Scope가 문서에 분리되어 있다.
- 사용자 승인 전에는 코드 변경을 시작하지 않는다.
- BEST 1은 실시간 차트가 실패해도 기존 REST 화면으로 되돌아갈 수 있다.
- BEST 2는 no-lookahead 검증을 통과해야 한다.
- BEST 3은 `screening_output_only=True`와 수동 승인 흐름을 유지해야 한다.
- `SCREENING ONLY` 표시가 화면에서 사라지지 않아야 한다.
- feature flag를 끄면 기존 차트, 기존 Alpha, 기존 optimizer 흐름으로 돌아갈 수 있어야 한다.
- 테스트 결과는 테스트명, 실행 명령, 결과 요약과 함께 보고한다.
- Assumption으로 표시한 항목은 구현 전 확정하거나 범위에서 제외한다.

Assumption: 기존 초안의 성능 목표는 구현 후 실제 기준값을 측정한 뒤 최종 KPI로 확정한다.

---

## Deliverables

- 승인용 Plan 문서: `20260511_high-class-algo-dashboard-report.md`
- 참조 문서 반영 기준: `20260511_plan-doc.md`의 목표, 안전 표시, feature flag, 테스트 후보를 Plan에 반영
- Phase 0 승인 체크 결과
- BEST 1 구현 범위와 검증 명령 목록
- BEST 2 구현 범위와 검증 명령 목록
- BEST 3 구현 범위와 검증 명령 목록
- 변경 후 완료 보고서

---

## Approval Note

이 Plan은 구현 승인 전 문서다.

다음 1개 결정을 먼저 받아야 한다.

**다음 실행은 BEST 1, BEST 2, BEST 3 중 무엇부터 시작할지 확정한다.**
