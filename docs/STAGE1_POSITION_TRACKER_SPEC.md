# Stage 1: Position Tracker — 스펙

## 개요
추천 엔진의 출력(진입가, 손절, TP1, TP2)을 입력으로 받아, 현재가 기준 실시간 손익 계산 및 상태 추적.

## 파일 위치
`src/stock_rtx4060/position_tracker.py`

## 핵심 기능

### 1. Position State Machine
```
UNINITIALIZED → TRACKED → CLOSED_BY_STOP | CLOSED_BY_TP1 | CLOSED_BY_TP2 | MANUAL_CLOSE
```

### 2. 실시간 가격 Fetch
- `yfinance` 실시간 현재가 조회
- 주기적 갱신 (cron/폴링)
- KRX calendário 고려 (공휴일 패스)

### 3. 핵심 지표 계산
| 필드 | 계산 |
|------|------|
| `current_price` | yfinance 실시간 종가 |
| `unrealized_pnl_pct` | (current - entry) / entry |
| `unrealized_pnl_abs` | (current - entry) * quantity |
| `distance_to_stop_pct` | (current - stop) / stop |
| `distance_to_tp2_pct` | (tp2 - current) / current |
| `days_held` | business days since entry_date |
| `max_favorable_move` | peak price since entry |
| `max_adverse_move` | trough price since entry |
| `trailing_stop_激活` | True if price > TP1 and trailing stop triggered |

### 4. 데이터 구조

```python
@dataclass
class TrackedPosition:
    ticker: str
    track: str  # "S" or "L"
    entry_date: str
    entry_price: float
    quantity: int
    stop: float
    tp1: float
    tp2: float
    current_price: float
    status: str  # "open", "closed"
    close_reason: str | None
    unrealized_pnl_pct: float
    unrealized_pnl_abs: float
    distance_to_stop_pct: float
    distance_to_tp2_pct: float
    max_favorable_move: float
    max_adverse_move: float
    last_updated: str  # ISO UTC
```

### 5. 포트폴리오 뷰
```python
def portfolio_snapshot(positions: list[TrackedPosition]) -> dict:
    # 총 미실현 손익
    # Track-S / Track-L 분리
    # 전체 exposure
    # 위험 종목 필터 (stop 접근 3% 이내)
```

## CLI 명령
```powershell
python -m stock_rtx4060.position_tracker --tickers AAPL,MSFT --refresh
python -m stock_rtx4060.position_tracker --portfolio-json reports/recommendations/*.json --watch --interval 300
```

## 검증
1. `python -m py_compile src/stock_rtx4060/position_tracker.py`
2. `pytest tests/test_position_tracker.py -v`
3. 수동: 실제 티커로 현재가 Fetch 확인

## 의존성
- `yfinance` (이미 requirements.txt에 있음)
- 기존 `krx_calendar.py` (KRX 공휴일 처리)
- 기존 `data_providers.py` 활용

## 안전 경계
- 읽기 전용 (주문 실행 없음)
- `screening_output_only=True` 유지
- 포트폴리오 뷰는 분석 목적만