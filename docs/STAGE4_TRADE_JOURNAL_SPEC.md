# Stage 4: Trade Journal — 스펙

## 개요
사용자의 실제 투자 의사결정(진입/종결 사유, 리스크 평가, 결과 후기)을 기록. 자동 실행 없이 수동 기록 및 후속 분석.

## 파일 위치
`src/stock_rtx4060/trade_journal.py`

## 핵심 기능

### 1. Decision Entry
사용자가 수동으로 입력하는 거래 기록:
- 티커, 포지션 방향, 진입가, 수량, 날짜
- 진입 사유 (스크리닝 추천 / 자체 분석 / 기타)
- 기대 수익률, 리스크:Reward
- 실제 결과 (손절/익절/수동 종료)
- 후기 메모

### 2. P&L Tracker
- 기록된 거래의 실현 손익
- 기대 vs 실제 비교
- 승률 통계

### 3. Journal Entry States
```
DRAFT → OPEN → CLOSED → REVIEWED
```

## CLI 명령
```powershell
python -m stock_rtx4060.trade_journal --add --ticker AAPL --entry 185 --qty 10 --reason "추천 후 자체 분석"
python -m stock_rtx4060.trade_journal --list
python -m stock_rtx4060.trade_journal --close AAPL --close-price 195 --outcome TP
python -m stock_rtx4060.trade_journal --report
```

## 검증
1. `python -m py_compile src/stock_rtx4060/trade_journal.py`
2. `pytest tests/test_trade_journal.py -v`