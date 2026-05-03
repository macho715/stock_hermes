# KEVPE 자체 테스트 결과

- 실행일: 2026-05-03 기준 세션
- 테스트 수: 10
- 결과: 10/10 PASS
- 범위: 로직 단위 테스트, synthetic OHLCV, synthetic event
- 제외: API 키 기반 실데이터 수익률 백테스트, 실거래 주문 테스트

```text
test_01_validate_missing_column (test_kevpe.TestKEVPE.test_01_validate_missing_column) ... ok
test_02_robust_zscore_detects_outlier (test_kevpe.TestKEVPE.test_02_robust_zscore_detects_outlier) ... ok
test_03_detect_negative_shock (test_kevpe.TestKEVPE.test_03_detect_negative_shock) ... ok
test_04_detect_positive_shock (test_kevpe.TestKEVPE.test_04_detect_positive_shock) ... ok
test_05_merge_consecutive_shocks (test_kevpe.TestKEVPE.test_05_merge_consecutive_shocks) ... ok
test_06_topic_classification (test_kevpe.TestKEVPE.test_06_topic_classification) ... ok
test_07_event_score_prioritizes_high_volume_conflict (test_kevpe.TestKEVPE.test_07_event_score_prioritizes_high_volume_conflict) ... ok
test_08_event_window_matching_excludes_outside (test_kevpe.TestKEVPE.test_08_event_window_matching_excludes_outside) ... ok
test_09_current_signal_red_on_similar_negative_patterns (test_kevpe.TestKEVPE.test_09_current_signal_red_on_similar_negative_patterns) ... ok
test_10_backtest_uses_next_day_execution (test_kevpe.TestKEVPE.test_10_backtest_uses_next_day_execution) ... ok

----------------------------------------------------------------------
Ran 10 tests in 0.066s

OK
```

## 테스트 항목

| No | Test | Purpose | Result |
|---:|---|---|---|
| 1 | validate_missing_column | OHLCV 필수 컬럼 누락 탐지 | PASS |
| 2 | robust_zscore_detects_outlier | 급등락 outlier 탐지 | PASS |
| 3 | detect_negative_shock | 하락 충격 구간 탐지 | PASS |
| 4 | detect_positive_shock | 상승 충격 구간 탐지 | PASS |
| 5 | merge_consecutive_shocks | 연속 shock window 병합 | PASS |
| 6 | topic_classification | oil/FOMC/chip 이벤트 분류 | PASS |
| 7 | event_score_prioritizes_high_volume_conflict | 고위험 이벤트 우선순위 | PASS |
| 8 | event_window_matching_excludes_outside | window 외 이벤트 제외 | PASS |
| 9 | current_signal_red_on_similar_negative_patterns | 유사 악재 패턴 RED 신호 | PASS |
| 10 | backtest_uses_next_day_execution | look-ahead 방지: 다음날 반영 | PASS |
