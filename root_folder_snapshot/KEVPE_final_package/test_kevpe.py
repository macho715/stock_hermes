
import unittest
import pandas as pd
import numpy as np

from kevpe import (
    Event, validate_ohlcv, robust_zscore, detect_volatility_windows,
    classify_event_topics, event_relevance_score, match_events_to_windows,
    feature_vector_from_event, current_signal_from_patterns, backtest_risk_overlay,
    gdelt_doc_timeline_url
)


def make_market(n=80, shock_day=40, shock=-0.08):
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = 100 * np.cumprod(1 + np.full(n, 0.001))
    close[shock_day:] *= (1 + shock)
    return pd.DataFrame({
        "date": dates,
        "open": close * 0.99,
        "high": close * 1.01,
        "low": close * 0.98,
        "close": close,
        "volume": 1000000,
    })


class TestKEVPE(unittest.TestCase):
    def test_01_validate_missing_column(self):
        df = make_market().drop(columns=["close"])
        with self.assertRaises(ValueError):
            validate_ohlcv(df)

    def test_02_robust_zscore_detects_outlier(self):
        s = pd.Series([0.001] * 30 + [0.09] + [0.001] * 10)
        z = robust_zscore(s, window=20)
        self.assertGreater(z.iloc[30], 2.5)

    def test_03_detect_negative_shock(self):
        df = make_market(shock=-0.08)
        windows = detect_volatility_windows(df, min_abs_return=0.015)
        self.assertFalse(windows.empty)
        self.assertIn("DOWN", windows["direction"].tolist())

    def test_04_detect_positive_shock(self):
        df = make_market(shock=0.08)
        windows = detect_volatility_windows(df, min_abs_return=0.015)
        self.assertFalse(windows.empty)
        self.assertIn("UP", windows["direction"].tolist())

    def test_05_merge_consecutive_shocks(self):
        df = make_market()
        df.loc[40, "close"] *= 0.90
        df.loc[41, "close"] *= 0.90
        windows = detect_volatility_windows(df, min_abs_return=0.015, merge_gap_days=3)
        self.assertTrue((windows["days"] >= 2).any())

    def test_06_topic_classification(self):
        topics = classify_event_topics("Iran oil shock and FOMC rate decision hit Samsung chip stocks")
        self.assertIn("oil_energy", topics)
        self.assertIn("central_bank", topics)
        self.assertIn("semiconductor_ai", topics)

    def test_07_event_score_prioritizes_high_volume_conflict(self):
        ev_low = Event(pd.Timestamp("2024-01-01"), "minor local sports event", tone=0, volume=1, source_diversity=1)
        ev_high = Event(pd.Timestamp("2024-01-01"), "war conflict oil shock affects South Korea", tone=-8, volume=800, source_diversity=80, topics=("war_conflict", "oil_energy"))
        self.assertGreater(event_relevance_score(ev_high), event_relevance_score(ev_low))

    def test_08_event_window_matching_excludes_outside(self):
        df = make_market(shock=-0.08)
        windows = detect_volatility_windows(df, min_abs_return=0.015)
        target_date = windows.iloc[0]["start"]
        events = [
            Event(target_date, "war conflict near Korea", tone=-7, volume=300, source_diversity=30, topics=("war_conflict",)),
            Event(target_date + pd.Timedelta(days=30), "irrelevant later event", volume=1000),
        ]
        matches = match_events_to_windows(windows, events)
        self.assertTrue((matches["headline"].str.contains("war conflict")).any())
        self.assertFalse((matches["headline"].str.contains("irrelevant later")).any())

    def test_09_current_signal_red_on_similar_negative_patterns(self):
        current = {
            "event_score": 0.90, "tone": -9.0, "volume_log": 6.0, "source_diversity_log": 4.0,
            "market_ret": -0.03, "vol_z": 4.0, "is_war": 1, "is_rate": 0,
            "is_oil": 1, "is_chip_ai": 0, "is_fx": 0
        }
        hist = [current.copy() for _ in range(10)]
        fwd = [-0.06, -0.04, -0.05, -0.08, -0.02, -0.07, -0.03, -0.05, -0.04, -0.06]
        sig = current_signal_from_patterns(current, hist, fwd)
        self.assertEqual(sig.regime, "RED")

    def test_10_backtest_uses_next_day_execution(self):
        df = make_market(n=40, shock_day=20, shock=-0.05)
        sigs = pd.DataFrame({"date": [df.loc[20, "date"]], "regime": ["RED"]})
        bt = backtest_risk_overlay(df, sigs)
        # signal day itself should still use previous default weight 1.0
        self.assertAlmostEqual(bt.loc[20, "exec_weight"], 1.0)
        # next day should use RED weight 0.2
        self.assertAlmostEqual(bt.loc[21, "exec_weight"], 0.2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
