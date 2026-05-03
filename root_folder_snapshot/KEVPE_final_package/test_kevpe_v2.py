"""KEVPE v2 — 투자 등급 패치 검증용 pytest 스위트.

총 18개 테스트:
  T01-T03  : v1 호환 (validate, robust z, window detect)
  T04-T05  : event topic / score
  T06      : event-window matching
  T07      : FeatureScaler — fit/transform 정합
  T08-T09  : current_signal_v2 — 정규화 / 결정론 / CI
  T10-T11  : regime hysteresis — 채터링 방지 / 안전 우선
  T12-T13  : backtest_v2 — 비용 반영 / look-ahead 방지
  T14      : DD circuit breaker
  T15      : vol-target sizing
  T16      : performance stats (Sharpe, MDD, hit-rate)
  T17      : walk-forward — purged k-fold + embargo
  T18      : v1 호환 wrapper backtest_risk_overlay 재현
"""
from __future__ import annotations

import math
import sys
import os
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kevpe_v2 import (
    Event, KevpeConfig, FeatureScaler, Signal, PerformanceStats,
    validate_ohlcv, robust_zscore, detect_volatility_windows,
    classify_event_topics, event_relevance_score, match_events_to_windows,
    feature_vector_from_event, bootstrap_pattern_ci,
    current_signal_v2, apply_regime_hysteresis,
    compute_performance_stats, backtest_v2, backtest_risk_overlay,
    walk_forward_validate,
)


def make_market(n=120, shock_day=60, shock=-0.08, drift=0.0005, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    rets = rng.normal(drift, 0.008, size=n)
    rets[shock_day] += shock
    close = 100 * np.cumprod(1 + rets)
    return pd.DataFrame({
        "date": dates,
        "open": close * 0.999,
        "high": close * 1.005,
        "low": close * 0.995,
        "close": close,
        "volume": 1_000_000,
    })


def synth_features(n=120, neg_rate=0.4, seed=11):
    rng = np.random.default_rng(seed)
    feats, fwd = [], []
    for i in range(n):
        is_neg = rng.random() < neg_rate
        feats.append({
            "event_score": float(0.7 if is_neg else 0.2),
            "tone": float(-7 if is_neg else 1),
            "volume_log": float(rng.uniform(2, 6)),
            "source_diversity_log": float(rng.uniform(1, 4)),
            "market_ret": float(rng.normal(-0.02 if is_neg else 0.005, 0.01)),
            "vol_z": float(rng.uniform(2, 4) if is_neg else rng.uniform(0, 1.5)),
            "is_war": 1.0 if is_neg else 0.0,
            "is_rate": 0.0,
            "is_oil": 1.0 if is_neg and rng.random() < 0.5 else 0.0,
            "is_chip_ai": 0.0,
            "is_fx": 0.0,
        })
        fwd.append(rng.normal(-0.05 if is_neg else 0.01, 0.02))
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    return feats, fwd, dates


class TestKevpeV2(unittest.TestCase):

    # --------- T01-T03 v1 호환 ---------
    def test_T01_validate_missing_column(self):
        df = make_market().drop(columns=["close"])
        with self.assertRaises(ValueError):
            validate_ohlcv(df)

    def test_T02_robust_zscore_outlier(self):
        s = pd.Series([0.001] * 30 + [0.09] + [0.001] * 10)
        z = robust_zscore(s, window=20)
        self.assertGreater(z.iloc[30], 2.5)

    def test_T03_detect_window_with_config(self):
        df = make_market(shock=-0.08, shock_day=60)
        cfg = KevpeConfig(min_abs_return=0.02)
        w = detect_volatility_windows(df, cfg)
        self.assertFalse(w.empty)
        self.assertIn("DOWN", w["direction"].tolist())

    # --------- T04-T05 event ---------
    def test_T04_topic_classification(self):
        topics = classify_event_topics("Iran oil shock and FOMC rate decision hit Samsung chip stocks")
        self.assertIn("oil_energy", topics)
        self.assertIn("central_bank", topics)
        self.assertIn("semiconductor_ai", topics)

    def test_T05_event_score_high_vs_low(self):
        ev_low = Event(pd.Timestamp("2024-01-01"), "minor local sports event",
                       tone=0, volume=1, source_diversity=1)
        ev_high = Event(pd.Timestamp("2024-01-01"),
                        "war conflict oil shock affects South Korea",
                        tone=-8, volume=800, source_diversity=80,
                        topics=("war_conflict", "oil_energy"))
        self.assertGreater(event_relevance_score(ev_high),
                           event_relevance_score(ev_low))

    # --------- T06 event-window matching ---------
    def test_T06_event_window_matching(self):
        df = make_market(shock=-0.08, shock_day=60)
        w = detect_volatility_windows(df)
        target = w.iloc[0]["start"]
        events = [
            Event(target, "war conflict near Korea", tone=-7, volume=300,
                  source_diversity=30, topics=("war_conflict",)),
            Event(target + pd.Timedelta(days=30), "irrelevant later event", volume=100),
        ]
        m = match_events_to_windows(w, events)
        self.assertTrue(m["headline"].str.contains("war conflict").any())
        self.assertFalse(m["headline"].str.contains("irrelevant later").any())

    # --------- T07 FeatureScaler ---------
    def test_T07_feature_scaler_normalizes(self):
        feats = [
            {"event_score": 0.1, "volume_log": 2.0, "tone": -3.0},
            {"event_score": 0.9, "volume_log": 6.0, "tone": -8.0},
            {"event_score": 0.5, "volume_log": 4.0, "tone": -5.0},
        ]
        sc = FeatureScaler().fit(feats)
        # 학습셋의 평균은 0 근처, std 는 1 근처
        Z = np.vstack([sc.transform(f) for f in feats])
        self.assertTrue(np.allclose(Z.mean(axis=0), 0.0, atol=1e-9))
        self.assertTrue(np.allclose(Z.std(axis=0), 1.0, atol=1e-6))
        # 미fit scaler 는 RuntimeError
        with self.assertRaises(RuntimeError):
            FeatureScaler().transform({"a": 1.0})

    # --------- T08-T09 current_signal_v2 ---------
    def test_T08_signal_red_on_negative_pattern(self):
        feats, fwd, _ = synth_features(n=80, neg_rate=0.6, seed=1)
        cur = {
            "event_score": 0.95, "tone": -9, "volume_log": 6, "source_diversity_log": 4,
            "market_ret": -0.04, "vol_z": 4.0,
            "is_war": 1, "is_rate": 0, "is_oil": 1, "is_chip_ai": 0, "is_fx": 0,
        }
        sig = current_signal_v2(cur, feats, fwd, as_of=pd.Timestamp("2024-06-01"))
        self.assertEqual(sig.regime, "RED")
        self.assertLess(sig.expected_return, 0.0)
        # CI low ≤ mean ≤ high
        self.assertLessEqual(sig.ci_low, sig.expected_return + 1e-6)
        self.assertGreaterEqual(sig.ci_high, sig.expected_return - 1e-6)
        # n_matches > 0
        self.assertGreater(sig.n_matches, 0)

    def test_T09_signal_deterministic_as_of(self):
        feats, fwd, _ = synth_features(n=60, seed=3)
        cur = feats[0]
        s1 = current_signal_v2(cur, feats, fwd, as_of=pd.Timestamp("2024-06-01"))
        s2 = current_signal_v2(cur, feats, fwd, as_of=pd.Timestamp("2024-06-01"))
        self.assertEqual(s1.score, s2.score)
        self.assertEqual(s1.expected_return, s2.expected_return)
        self.assertEqual(s1.date, pd.Timestamp("2024-06-01"))

    # --------- T10-T11 hysteresis ---------
    def test_T10_hysteresis_blocks_chatter(self):
        # raw: G G G A G A G G G ... → A 단발 노이즈는 무시되어야 함
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        raw = ["GREEN", "GREEN", "GREEN", "AMBER", "GREEN", "AMBER",
               "GREEN", "GREEN", "GREEN", "GREEN"]
        df = pd.DataFrame({"date": dates, "regime": raw})
        cfg = KevpeConfig(confirm_days=2, cooloff_days=3)
        out = apply_regime_hysteresis(df, cfg)
        # A 단발 → confirm 미충족 → safer 방향이라 즉시 전환되지만 cooloff 후 G 돌아옴
        # 핵심: 결과 시퀀스가 raw 보다 안정적 (전환 횟수 적음)
        n_changes_raw = sum(1 for i in range(1, len(raw)) if raw[i] != raw[i-1])
        n_changes_out = sum(1 for i in range(1, len(out)) if out["regime"].iloc[i] != out["regime"].iloc[i-1])
        self.assertLess(n_changes_out, n_changes_raw)

    def test_T11_hysteresis_red_immediate(self):
        # GREEN → RED 는 안전을 위해 즉시 전환되어야 함
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        raw = ["GREEN", "GREEN", "RED", "RED", "GREEN"]
        df = pd.DataFrame({"date": dates, "regime": raw})
        cfg = KevpeConfig(confirm_days=2, cooloff_days=3)
        out = apply_regime_hysteresis(df, cfg)
        # idx 2 에서 RED 즉시 전환
        self.assertEqual(out["regime"].iloc[2], "RED")
        # idx 4 의 GREEN 은 cooloff 안이라 RED 유지
        self.assertEqual(out["regime"].iloc[4], "RED")

    # --------- T12-T13 backtest cost & lookahead ---------
    def test_T12_backtest_cost_drag(self):
        df = make_market(n=100, shock_day=50, shock=-0.06)
        sig = pd.DataFrame({
            "date": [df.loc[40, "date"], df.loc[60, "date"]],
            "regime": ["RED", "GREEN"],
        })
        cfg_no_cost = KevpeConfig(cost_bps_per_turn=0.0, dd_circuit_breaker=10.0)
        cfg_cost = KevpeConfig(cost_bps_per_turn=20.0, dd_circuit_breaker=10.0)
        r_nc = backtest_v2(df, sig, cfg_no_cost)
        r_c = backtest_v2(df, sig, cfg_cost)
        self.assertGreater(r_nc["stats"].net_total_return, r_c["stats"].net_total_return)
        self.assertGreater(r_c["stats"].cost_drag, 0.0)

    def test_T13_no_lookahead_next_day_execution(self):
        df = make_market(n=60, shock_day=30, shock=-0.05)
        sig = pd.DataFrame({"date": [df.loc[30, "date"]], "regime": ["RED"]})
        cfg = KevpeConfig(cost_bps_per_turn=0.0, dd_circuit_breaker=10.0)
        out = backtest_v2(df, sig, cfg)["daily"]
        # 신호 당일은 default weight 1.0
        self.assertAlmostEqual(out.loc[30, "exec_weight"], 1.0, places=6)
        # 다음날부터 RED weight 0.2
        self.assertAlmostEqual(out.loc[31, "exec_weight"], 0.2, places=6)

    # --------- T14 DD circuit breaker ---------
    def test_T14_dd_circuit_breaker_zeros_weight(self):
        # 강한 하락이 누적되도록 구성 (drift -0.5%, vol 2%)
        rng = np.random.default_rng(1)
        n = 150
        rets = rng.normal(-0.005, 0.02, size=n)
        close = 100 * np.cumprod(1 + rets)
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-02", periods=n, freq="B"),
            "open": close * 0.999, "high": close * 1.002, "low": close * 0.998,
            "close": close, "volume": 1e6,
        })
        sig = pd.DataFrame(columns=["date", "regime"])  # 신호 없음 → weight=1.0
        cfg = KevpeConfig(cost_bps_per_turn=0.0,
                          dd_circuit_breaker=0.10, dd_recovery_threshold=0.02)
        out = backtest_v2(df, sig, cfg)["daily"]
        # breaker 발동 후 exec_weight=0 인 날이 1일 이상 존재해야 함
        self.assertTrue((out["exec_weight"] == 0.0).sum() >= 1)
        # buy-and-hold MDD 가 strategy MDD 보다 더 깊다 (breaker 효과)
        bh_eq = (1 + out["ret"]).cumprod()
        bh_mdd = float((bh_eq / bh_eq.cummax() - 1).min())
        self.assertLess(bh_mdd, out["drawdown"].min() + 1e-9)

    # --------- T15 vol-target sizing ---------
    def test_T15_vol_target_reduces_weight_in_high_vol(self):
        rng = np.random.default_rng(5)
        n = 100
        # 앞 50일은 저변동성, 뒤 50일은 고변동성
        rets = np.concatenate([rng.normal(0, 0.005, 50), rng.normal(0, 0.04, 50)])
        close = 100 * np.cumprod(1 + rets)
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-02", periods=n, freq="B"),
            "open": close * 0.999, "high": close * 1.002, "low": close * 0.998,
            "close": close, "volume": 1e6,
        })
        sig = pd.DataFrame(columns=["date", "regime"])
        cfg = KevpeConfig(vol_target_annual=0.10, max_gross_leverage=1.0,
                          cost_bps_per_turn=0.0, dd_circuit_breaker=10.0)
        out = backtest_v2(df, sig, cfg)["daily"]
        # 고변동 구간 평균 weight < 저변동 구간 평균 weight
        low_w = out.iloc[20:50]["target_weight"].mean()
        high_w = out.iloc[70:99]["target_weight"].mean()
        self.assertLess(high_w, low_w)
        self.assertLessEqual(out["target_weight"].max(), cfg.max_gross_leverage + 1e-9)

    # --------- T16 performance stats ---------
    def test_T16_perf_stats_metrics_sane(self):
        rng = np.random.default_rng(2)
        n = 252
        net = rng.normal(0.0006, 0.012, size=n)
        df = pd.DataFrame({
            "ret": net, "gross_ret": net, "net_ret": net,
            "weight": np.ones(n),
        })
        s = compute_performance_stats(df, trading_days=252)
        self.assertEqual(s.n_days, n)
        self.assertGreater(s.ann_vol, 0)
        # cvar5 < 평균 (꼬리 손실)
        self.assertLess(s.cvar_5, net.mean())
        # MDD ≤ 0
        self.assertLessEqual(s.max_drawdown, 0.0)
        # hit_rate 0~1
        self.assertGreaterEqual(s.hit_rate, 0.0)
        self.assertLessEqual(s.hit_rate, 1.0)

    # --------- T17 walk-forward ---------
    def test_T17_walk_forward_produces_oos_metrics(self):
        feats, fwd, dates = synth_features(n=200, neg_rate=0.4, seed=9)
        cfg = KevpeConfig(wf_n_folds=4, wf_embargo_days=3, wf_min_train_size=80,
                          top_k=10, min_similarity=0.0)
        df = walk_forward_validate(make_market(n=200), feats, fwd, dates, cfg)
        self.assertGreaterEqual(len(df), 1)
        self.assertIn("dir_hit_rate", df.columns)
        self.assertIn("r2_oos", df.columns)
        # train/test 분리 확인
        for _, row in df.iterrows():
            self.assertGreater(row["train_n"], 0)
            self.assertGreater(row["test_n"], 0)

    # --------- T18 v1 호환 wrapper ---------
    def test_T18_v1_wrapper_backtest_risk_overlay(self):
        df = make_market(n=40, shock_day=20, shock=-0.05)
        sig = pd.DataFrame({"date": [df.loc[20, "date"]], "regime": ["RED"]})
        bt = backtest_risk_overlay(df, sig)
        # 시그널 당일 weight=1.0 (default), 다음날 0.2
        self.assertAlmostEqual(bt.loc[20, "exec_weight"], 1.0, places=6)
        self.assertAlmostEqual(bt.loc[21, "exec_weight"], 0.2, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
