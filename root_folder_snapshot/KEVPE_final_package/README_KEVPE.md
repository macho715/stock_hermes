# KEVPE — Korea Event-Volatility Pattern Engine

## 목적
한국 주식시장 OHLCV 데이터에서 등락폭이 큰 구간을 탐지하고, GDELT/신문/역사 이벤트 데이터를 날짜 윈도우로 매칭하여 현재 시장을 GREEN/AMBER/RED 리스크 신호로 분류합니다.

## 파일
- `kevpe.py`: 알고리즘 본체
- `test_kevpe.py`: 자체 10회 테스트
- `KEVPE_test_report.md`: 테스트 결과

## 실행
```bash
pip install pandas numpy
python -m unittest -v test_kevpe.py
```

## 운영 데이터 연결
- 한국 시장: data.go.kr/KRX, KIS Open API, PyKRX, FinanceDataReader
- 이벤트/신문: GDELT DOC/Event, NYT Archive API, Library of Congress, Wikimedia On This Day
- 권장: 공식/유료 데이터 계약 우선, crawler는 보조로만 사용

## 주의
본 엔진은 투자 참고용 리스크 신호이며, 매수·매도 추천 또는 수익 보장을 의미하지 않습니다.
