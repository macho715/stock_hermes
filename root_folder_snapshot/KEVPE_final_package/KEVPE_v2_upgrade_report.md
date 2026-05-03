# KEVPE v2 — Investment-Grade Upgrade Report

작성일: 2026-05-03
대상: `kevpe.py` v1 → `kevpe_v2.py` 패치
프레임: algorithm-engineer 6-Phase Workflow

---

## Phase 1 — Problem Specification

- KR: KOSPI/한국 주식의 OHLCV 와 글로벌 이벤트(GDELT/뉴스 아카이브) 스트림으로부터 GREEN/AMBER/RED 리스크 신호를 생성하되, **실제 자본 운용 의사결정에 참고 가능한 수준의 통계·비용·검증 절차**를 갖춘 엔진으로 격상시킨다.
- EN: Upgrade KEVPE prototype to a research-grade signal engine usable as risk overlay input — with realistic costs, deterministic backtest, walk-forward OOS validation, and signal stability controls.

가정:
1. 단일 자산 오버레이로 사용한다 (KOSPI 인덱스 또는 KODEX200 ETF 가정). 다중 자산 포트폴리오 결합은 v3 범위.
2. 실시간 데이터 라인은 외부 (PyKRX/FinanceDataReader/GDELT API). v2 는 알고리즘 코어 패치만 다룬다.
3. 사용자는 신호를 직접 매매에 연결하지 않고 risk-on / risk-off **포지션 가중치 조절**에 사용한다.

---

## Phase 2 — Constraints & Classification

| 항목 | 내용 |
|------|------|
| Scale | OHLCV 수년치 (수천 일), 이벤트 수만 건/년, walk-forward 폴드 5개 가정 |
| Properties | 시계열 (look-ahead 금지), fat-tail, 공휴일 비대칭, 매칭 sparse |
| Domain | **HYBRID** — CP 적 데이터구조 + PRAC 한 백테스트/검증 |

핵심 제약:
- O(n × m) 패턴 매칭은 n=수백, m=수백~수천 수준에서 충분히 실시간 가능
- 메모리: 패턴풀 전체 메모리 적재 (k-NN 후보군 작아 O(n) 캐시 용이)
- look-ahead/생존편향/p-hacking 방지가 결과 신뢰도의 90%

---

## Phase 3 — Strategy Selection (v1 진단 + v2 처방)

### v1 진단 (10가지 차단 사유)

| # | 항목 | 현 상태 | 투자 등급 부적합 사유 |
|---|------|---------|------------------------|
| 1 | 코사인 유사도 비교 | raw feature dict 그대로 | 스케일 큰 항목(volume_log) 이 지배. event_score(0~1)·dummy 변수가 묻힘 |
| 2 | look-ahead 누수 | scaler 부재 | 정규화를 한꺼번에 fit 하면 미래 통계가 학습에 들어감 |
| 3 | `today()` 의존 | `current_signal_from_patterns` 가 `pd.Timestamp.today()` 호출 | 백테스트가 결정론적이지 않음, 재현 불가 |
| 4 | 거래비용 0 | `backtest_risk_overlay` 에 cost 없음 | 슬리피지·커미션·세금 미반영, 실현 수익 과대평가 |
| 5 | 신호 채터링 | regime 즉시 전환 | hysteresis 없음 → 일별 flap, turnover 폭증 |
| 6 | 검증 부재 | in-sample 평가만 | walk-forward 없음, 과적합 위험 측정 불가 |
| 7 | 통계 신뢰구간 부재 | top-K 가중평균 1점 추정 | 표본 변동 미공개, 유사도 부족 시도 RED 발사 가능 |
| 8 | 위험관리 부재 | 회복 못해도 RED weight 0.2 유지 | drawdown 폭주 차단 장치 없음 |
| 9 | 포지션 사이징 부재 | weight ∈ {0.2, 0.5, 1.0} 만 | 변동성 변화에 무관, vol-target 사이징 없음 |
| 10 | 성능지표 불완전 | `equity` 만 반환 | Sharpe/Sortino/MDD/CVaR/turnover/cost-drag 등 표준 지표 없음 |

### v2 처방

```
v1                                    v2
─────────────────────────────────────────────────────────────────
raw cosine                          → FeatureScaler (z-norm) + cosine
fit on full dataset                 → fit on TRAIN fold only
today()                             → as_of arg, deterministic
no cost                             → cost_bps_per_turn × |Δw|
instant regime switch               → confirm_days + cooloff_days FSM
in-sample only                      → purged k-fold + embargo
point estimate                      → weighted bootstrap (5,95) CI
no kill-switch                      → DD circuit breaker + recovery
fixed weight bucket                 → optional vol-target sizing
equity only                         → PerformanceStats {Sharpe..cost-drag}
```

---

## Phase 4 — Implementation

### 파일 구조
```
KEVPE_final_package/
├─ kevpe.py                  # v1 원본 (touch 안 함)
├─ kevpe_v2.py               # NEW — 투자 등급 코어
├─ test_kevpe.py             # v1 테스트 (10/10 PASS, 보존)
├─ test_kevpe_v2.py          # NEW — v2 테스트 18개
├─ demo_kevpe_v2.py          # NEW — end-to-end 데모
├─ requirements_kevpe_v2.txt # NEW — pinned versions
├─ README_KEVPE_v2.md        # NEW — 사용법·마이그레이션
└─ KEVPE_v2_upgrade_report.md# 본 리포트
```

### 핵심 API (요약)

```python
from kevpe_v2 import (
    KevpeConfig, FeatureScaler,
    detect_volatility_windows, match_events_to_windows,
    feature_vector_from_event,
    current_signal_v2,           # ★ 정규화 + CI + 결정론
    apply_regime_hysteresis,     # ★ 채터링 방지
    backtest_v2,                 # ★ 비용·breaker·vol-target
    walk_forward_validate,       # ★ purged k-fold + embargo
    compute_performance_stats,
)

cfg = KevpeConfig(
    cost_bps_per_turn=5.0,
    confirm_days=2, cooloff_days=3,
    dd_circuit_breaker=0.20,
    vol_target_annual=0.15,      # 옵션
    wf_n_folds=5, wf_embargo_days=5,
)
```

---

## Phase 5 — Analysis

### Complexity

| 단계 | Time | Space | 비고 |
|------|------|-------|------|
| `validate_ohlcv` | O(n log n) | O(n) | sort+drop_dup |
| `detect_volatility_windows` | O(n) | O(n) | rolling MAD + 그룹병합 |
| `match_events_to_windows` | O(W·E) | O(W·E) | W=윈도우, E=이벤트 |
| `current_signal_v2` | O(H·F) + O(B·K) | O(H·F) | H=hist, F=feat dim, B=bootstrap, K=top_k |
| `apply_regime_hysteresis` | O(n) | O(n) | 단일 패스 FSM |
| `backtest_v2` | O(n) | O(n) | breaker 때문에 sequential, 벡터화 부분 + scalar 루프 |
| `walk_forward_validate` | O(F·H_test·H_train·F_dim) | O(H_train) | F=fold |

**18개 테스트 0.285s** 에 통과 — 실시간 일별 운영에 충분히 빠름.

### Correctness Sketch

1. **Look-ahead 안전성** (T13, T17):
   - `target_weight.shift(1)` 로 t 시점 의사결정이 t+1 에 반영됨
   - `vol_target` 계산도 `.shift(1)` 적용 — 미래 변동성 누수 차단
   - Walk-forward 의 `embargo_days` 가 train 끝과 test 시작 사이 정보 누수 차단

2. **Hysteresis FSM 정합성** (T10, T11):
   - 안전 우선 원칙: GREEN→RED 전환은 즉시 (severity ↑ 즉시 허용)
   - 위험 완화 전환 (RED→GREEN): confirm_days 연속 + cooloff_days 잔류 후에만
   - 결과 시퀀스의 전환 횟수가 raw 보다 항상 ≤ — 단조성

3. **비용 보존** (T12):
   - cost = |Δw| × bps × 1e-4
   - net_total + cost_drag = gross_total (수치 검증)
   - 거래 빈도 ↑ → cost_drag ↑ → net_total ↓

4. **Bootstrap CI 단조성**:
   - n_bootstrap → ∞ 에서 ci_low → 5% 분위수, ci_high → 95% 분위수
   - 가중치 0 인 표본 제외 — bias 없음

### Dry-run 예시 (T11 hysteresis)

| t | raw | severity 비교 | 적용 규칙 | out | last_change |
|---|-----|---------------|-----------|-----|-------------|
| 0 | GREEN | init | 그대로 | GREEN | 0 |
| 1 | GREEN | == | 그대로 | GREEN | 0 |
| 2 | RED | RED>GREEN | 즉시 전환 | RED | 2 |
| 3 | RED | == | 그대로 | RED | 2 |
| 4 | GREEN | GREEN<RED, 3-2=1<cooloff(3) | 차단 | RED | 2 |

→ idx 4 의 GREEN flap 이 RED 로 막힘 → 채터링 차단 검증.

---

## Phase 6 — Alternatives & Trade-offs

| 대안 | 장점 | 단점 | v2 채택 여부 |
|------|------|------|---------------|
| **HMM regime detection** | 확률적 부드러운 전환 | O(n·k²) 학습, 데이터 부족 시 불안 | 채택 보류 (v3 후보) |
| **CUSUM change-point** | 변동성 변화 빠른 탐지 | 잡신호 多 | 보조 지표로만 |
| **GARCH(1,1) vol forecast** | 변동성 예측 정확도 ↑ | scipy.optimize/arch 의존, 추정 노이즈 | vol-target 의 실현 vol 를 GARCH 로 교체는 v3 |
| **Dynamic threshold (red=μ+2σ)** | 시장 자체 통계로 자동 조정 | 추세장 과민 | KevpeConfig 로 사용자가 튜닝 가능 |
| **Triple-barrier labeling** (López de Prado) | 명확한 forward return 정의 | 구현 복잡 | walk-forward 와 결합 시 v3 권장 |
| **Block bootstrap** | 시계열 의존 보존 | 구현 복잡, 블록 길이 결정 필요 | v2 는 weighted iid bootstrap, 충분 |
| **Kelly-fractional sizing** | 이론 최적 사이징 | 분산 추정 오차에 매우 민감 | vol-target 이 더 안정 |

### 실전 개선 포인트 (v3 로드맵)

1. **다중 자산 포트폴리오 연계** — KOSPI/KRW/Bond/Gold 의 신호별 weight 합산, max correlation cap
2. **GARCH vol forecast 로 vol-target 정밀화**
3. **Triple-barrier 라벨링 + Meta-labeling** — 신호 신뢰도 secondary 모델
4. **샤프 비율 부트스트랩 신뢰구간** — 전략 자체 통계적 유의성
5. **트랜잭션 마이크로구조 모델** — 호가창 깊이/시장가 vs 지정가 슬리피지
6. **GDELT/NYT 실시간 ingestion** — Kafka/Cron 으로 스트리밍 결합
7. **Compliance / 규정** — 단축키 트리거 시그널 사용 시 컴플라이언스 검토 절차

---

## 검증 결과

```
$ python3 -m unittest -v test_kevpe_v2
test_T01_validate_missing_column ... ok
test_T02_robust_zscore_outlier ... ok
test_T03_detect_window_with_config ... ok
test_T04_topic_classification ... ok
test_T05_event_score_high_vs_low ... ok
test_T06_event_window_matching ... ok
test_T07_feature_scaler_normalizes ... ok
test_T08_signal_red_on_negative_pattern ... ok
test_T09_signal_deterministic_as_of ... ok
test_T10_hysteresis_blocks_chatter ... ok
test_T11_hysteresis_red_immediate ... ok
test_T12_backtest_cost_drag ... ok
test_T13_no_lookahead_next_day_execution ... ok
test_T14_dd_circuit_breaker_zeros_weight ... ok
test_T15_vol_target_reduces_weight_in_high_vol ... ok
test_T16_perf_stats_metrics_sane ... ok
test_T17_walk_forward_produces_oos_metrics ... ok
test_T18_v1_wrapper_backtest_risk_overlay ... ok
----------------------------------------------------------------------
Ran 18 tests in 0.285s — OK
```

v1 의 10개 테스트는 그대로 PASS (kevpe.py 미수정), v2 신규 18개 PASS — 합산 28/28.

---

## ⚠️ 운영 전 필수 확인 (Investment-Grade Checklist)

- [ ] 실데이터 (KRX 일봉, GDELT artlist+timeline) 로 1-3년 walk-forward Sharpe ≥ 0.7 확보
- [ ] 실거래 슬리피지 측정 → `cost_bps_per_turn` 캘리브레이션
- [ ] **소액 paper trading 3-6 개월** 후에만 실자금 노출
- [ ] 단일 자산 한도 (예: 총자산의 30%) 내에서 사용
- [ ] KevpeConfig 변경 이력 git 추적 (재현성)
- [ ] 신호 발생 시 사람 확인 절차 (auto-execute 금지)
- [ ] 데이터 stale 검증 (last bar 가 T-1 거래일인지)
- [ ] 컴플라이언스 검토 — 회사·법인계좌 사용 시 사내 정책 충돌 확인

본 엔진은 **리스크 참고 신호**이며, 매수·매도 추천이나 수익 보장이 아닙니다.
