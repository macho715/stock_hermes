# Stage 5: Broker Bridge — 스펙

## 개요
브로커 API 어댑터 구조. 실제 주문 연결은 **사용자 명시적 승인 + 수동 실행만 가능**. 자동 매매는 차단된 상태에서 구조만 준비.

## 파일 위치
`src/stock_rtx4060/broker_bridge.py`

## 핵심 원칙
1. **어댑터 패턴** — 브로커별 implementation 분리 (IBKR, Alpaca, Binance, etc.)
2. **실행은 항상 수동** — 시스템은 주문 상세만 생성하고, 사용자가 직접 승인
3. **一切的**: 이 구조는 브로커 연동을 **설명하고 준비**하는 것. 실제 주문 연결은 사용자가 별도 승인해야 함.

## 브로커 어댑터 구조

```python
class BrokerAdapter(ABC):
    @abstractmethod
    def get_account_info(self) -> AccountInfo: ...
    @abstractmethod
    def get_positions(self) -> list[BrokerPosition]: ...
    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResult: ...  # simulates only
    @abstractmethod
    def get_quote(self, ticker: str) -> Quote: ...

class PaperBroker(BrokerAdapter):
    """시뮬레이션 전용 — 항상 simulated fills만 반환"""
```

## 핵심 기능

### 1. Order Request Builder
추천 엔진의 출력을 브로커 주문 형식으로 변환:
- 티커, 수량, 가격, 유형 (market/limit)
-止损주문 (if supported)
- 브로커별 형식 정규화

### 2. Trade Plan Document Generator
주문 실행 전 **Trade Plan 문서** 생성:
- 진입/손절/목표가 명확히 기재
- 리스크:Reward 표시
- 추천 점수 및evidence 요약
- **"본 주문은 사용자가 직접 검토하고 승인해야 합니다"** 명시

### 3. Order Execution Log
모든 "주문 시뮬레이션" 기록 → 로그에 남김 (실제 실행 아님)

## Security Notes
- API 키는 브로커 어댑터에 전달되지 않음 (keyless simulation mode)
- 실제 브로커 연동 시: API 키는 환경변수 또는secure vault에서만 관리
- 이 모듈은 `screening_output_only=True` 유지

## 검증
1. `python -m py_compile src/stock_rtx4060/broker_bridge.py`
2. `pytest tests/test_broker_bridge.py -v`