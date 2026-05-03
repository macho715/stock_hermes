# KEVPE v2 — Korea Event-Volatility Pattern Engine (Investment-Grade)

v1 프로토타입 → 실제 자본 운용 의사결정에서 **리스크 오버레이 신호**로 참고할 수 있는 등급으로 격상한 패치.

---

## 파일

| 파일 | 역할 |
|------|------|
| `kevpe.py` | v1 원본 (보존, 미수정) |
| **`kevpe_v2.py`** | **v2 코어 (이걸 사용)** |
| `test_kevpe.py` | v1 테스트 10개 (그대로 PASS) |
| **`test_kevpe_v2.py`** | **v2 테스트 18개** |
| `demo_kevpe_v2.py` | end-to-end 데모 (synthetic) |
| `requirements_kevpe_v2.txt` | 의존성 |
| `KEVPE_v2_upgrade_report.md` | 6-Phase 분석·근거·체크리스트 |

---

## 빠른 시작

```bash
pip install -r requirements_kevpe_v2.txt
python -m unittest -v test_kevpe_v2     # 18/18 PASS 확인
python demo_kevpe_v2.py                  # synthetic e2e 데모
```

---

## 최소 사용 예 (실데이터 연결)

```python
import pandas as pd
from kevpe_v2 import (
    KevpeConfig, Event, FeatureScaler,
    detect_volatility_windows, match_events_to_windows,
    feature_vector_from_event, current_signal_v2,
    apply_regime_hysteresis, backtest_v2,
)

# 1) 데이터 로드 (PyKRX/FinanceDataReader 권장)
# ohlcv: DataFrame(date, open, high, low, close, volume)
# events: List[Event] from GDELT artlist + topics

cfg = KevpeConfig(
    cost_bps_per_turn=5.0,         # 본인 거래환경 슬리피지로 캘리브레이션
    confirm_days=2, cooloff_days=3,
    dd_circuit_breaker=0.20,
    vol_target_annual=0.15,        # 연 15% 변동성 타깃 (옵션)
)

windows = detect_volatility_windows(ohlcv, cfg)
matches = match_events_to_windows(windows, events, cfg)

# 시그널 생성: 학습용 historical feature pool + forward returns 가 필요
# (논문/계약 데이터로 사전 구축, 또는 walk-forward 로 자동 구성)
scaler = FeatureScaler().fit(historical_feats)
signal = current_signal_v2(
    current_feature=cur_feat,
    historical_features=historical_feats,
    historical_forward_returns=historical_fwd_rets,
    config=cfg, scaler=scaler,
    as_of=pd.Timestamp.today().normalize(),
)
print(signal.regime, signal.score, signal.reason)

# 백테스트
sig_df = pd.DataFrame({...})  # 일별 raw signals
sig_df = apply_regime_hysteresis(sig_df, cfg)  # 채터링 방지
res = backtest_v2(ohlcv, sig_df, cfg)
print(res["stats"])              # PerformanceStats
print(res["buy_and_hold_stats"]) # 비교용
```

---

## v1 → v2 마이그레이션

| v1 호출 | v2 호출 |
|---------|---------|
| `current_signal_from_patterns(c, h, r)` | `current_signal_v2(c, h, r, scaler=...)` |
| `backtest_risk_overlay(o, s)` | `backtest_v2(o, s, cfg)` (호환 wrapper 도 유지) |
| 변수 하드코딩 (`window=20` 등) | `KevpeConfig(z_window=20, ...)` |
| 단일 점 추정 | `Signal.expected_return + ci_low + ci_high` |

`backtest_risk_overlay` 는 v1 시그니처를 그대로 보존 (cost=0, breaker off) — 기존 노트북 영향 없음.

---

## ⚠️ 운영 체크리스트 (실투자 전 필수)

`KEVPE_v2_upgrade_report.md` 마지막 섹션 참조. 핵심:

1. 실데이터 walk-forward Sharpe ≥ 0.7 1-3년 검증
2. 실거래 슬리피지 측정 → `cost_bps_per_turn` 캘리브레이션
3. 소액 paper trading 3-6개월
4. 단일 자산 노출 한도 (예: 30% 이하)
5. KevpeConfig git 추적
6. 시그널 발생 시 사람 확인 절차 (auto-execute 금지)
7. 사내 컴플라이언스 검토

본 엔진은 **리스크 참고 신호**이며, 매수·매도 추천이 아닙니다.
