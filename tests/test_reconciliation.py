"""Tests for Reconciler (Phase 8).

Tests diff detection, pause-on-large-diff, background thread.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from stock_rtx4060.broker.reconciliation import (
    Reconciler,
    ReconciliationDiff,
    LARGE_DIFF_THRESHOLD_PCT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_broker(positions: dict[str, float]):
    """Build a mock broker with .get_positions() returning the given qty dict."""
    broker = MagicMock()
    broker_positions = []
    for sym, qty in positions.items():
        pos = MagicMock()
        pos.symbol = sym
        pos.quantity = qty
        broker_positions.append(pos)
    broker.get_positions.return_value = broker_positions
    return broker


def _make_tracker(positions: dict[str, float]):
    """Build a mock position_tracker with .positions dict."""
    tracker = MagicMock()
    tracked = {}
    for sym, qty in positions.items():
        p = MagicMock()
        p.quantity = qty
        tracked[sym] = p
    tracker.positions = tracked
    return tracker


# ---------------------------------------------------------------------------
# ReconciliationDiff
# ---------------------------------------------------------------------------

class TestReconciliationDiff:
    def test_is_large_above_threshold(self):
        # 10 / max(110, 100) = 10/110 ≈ 9.09% < 10% → NOT large
        diff = ReconciliationDiff(ticker="AAPL", broker_qty=110, tracked_qty=100, delta=10)
        assert not diff.is_large
        # 200 / max(200, 100) = 200/200 = 100% > 10% → large
        diff2 = ReconciliationDiff(ticker="AAPL", broker_qty=200, tracked_qty=100, delta=100)
        assert diff2.is_large

    def test_is_large_below_threshold(self):
        diff = ReconciliationDiff(ticker="AAPL", broker_qty=101, tracked_qty=100, delta=1)
        assert not diff.is_large

    def test_to_dict(self):
        diff = ReconciliationDiff(ticker="AAPL", broker_qty=10, tracked_qty=9, delta=1)
        d = diff.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["delta"] == 1
        assert "is_large" in d


# ---------------------------------------------------------------------------
# run_once — no diff
# ---------------------------------------------------------------------------

class TestReconcilerNoDiff:
    def test_no_diff_empty(self):
        reconciler = Reconciler()
        broker = _make_broker({})
        tracker = _make_tracker({})
        diffs = reconciler.run_once(broker, tracker)
        assert diffs == []

    def test_no_diff_matching_positions(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 100, "MSFT": 50})
        tracker = _make_tracker({"AAPL": 100, "MSFT": 50})
        diffs = reconciler.run_once(broker, tracker)
        assert diffs == []


# ---------------------------------------------------------------------------
# run_once — diffs detected
# ---------------------------------------------------------------------------

class TestReconcilerDiffDetected:
    def test_broker_has_more(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 110})
        tracker = _make_tracker({"AAPL": 100})
        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 1
        assert diffs[0].ticker == "AAPL"
        assert diffs[0].delta == 10

    def test_tracker_has_more(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 90})
        tracker = _make_tracker({"AAPL": 100})
        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 1
        assert diffs[0].delta == -10

    def test_ticker_only_in_broker(self):
        reconciler = Reconciler()
        broker = _make_broker({"TSLA": 50})
        tracker = _make_tracker({})
        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 1
        assert diffs[0].ticker == "TSLA"
        assert diffs[0].tracked_qty == 0.0

    def test_ticker_only_in_tracker(self):
        reconciler = Reconciler()
        broker = _make_broker({})
        tracker = _make_tracker({"TSLA": 50})
        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 1
        assert diffs[0].ticker == "TSLA"
        assert diffs[0].broker_qty == 0.0

    def test_multiple_diffs(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 110, "MSFT": 50, "TSLA": 0})
        tracker = _make_tracker({"AAPL": 100, "MSFT": 60, "TSLA": 30})
        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 3


# ---------------------------------------------------------------------------
# Large diff — pause new orders
# ---------------------------------------------------------------------------

class TestReconcilerLargeDiff:
    def test_large_diff_sets_pause_flag(self):
        pause_flag = threading.Event()
        reconciler = Reconciler(pause_new_orders_flag=pause_flag)

        # 200 vs 100 = 100% delta → definitely large
        broker = _make_broker({"AAPL": 200})
        tracker = _make_tracker({"AAPL": 100})

        diffs = reconciler.run_once(broker, tracker)
        assert len(diffs) == 1
        assert diffs[0].is_large
        assert pause_flag.is_set()
        assert reconciler.orders_paused

    def test_large_diff_triggers_callback(self):
        callback_called = []
        def my_callback(diff):
            callback_called.append(diff)

        pause_flag = threading.Event()
        reconciler = Reconciler(on_large_diff=my_callback, pause_new_orders_flag=pause_flag)

        # Create a definitely-large diff: 200 vs 100 = 100% delta
        broker = _make_broker({"AAPL": 200})
        tracker = _make_tracker({"AAPL": 100})

        diffs = reconciler.run_once(broker, tracker)
        large_diffs = [d for d in diffs if d.is_large]
        assert len(large_diffs) > 0
        assert len(callback_called) > 0

    def test_small_diff_does_not_pause(self):
        pause_flag = threading.Event()
        reconciler = Reconciler(pause_new_orders_flag=pause_flag)

        # 101 vs 100 = 1% → not large
        broker = _make_broker({"AAPL": 101})
        tracker = _make_tracker({"AAPL": 100})

        reconciler.run_once(broker, tracker)
        assert not pause_flag.is_set()

    def test_clear_pause(self):
        pause_flag = threading.Event()
        reconciler = Reconciler(pause_new_orders_flag=pause_flag)

        broker = _make_broker({"AAPL": 200})
        tracker = _make_tracker({"AAPL": 100})

        reconciler.run_once(broker, tracker)
        # If there was a large diff, pause should be set
        reconciler.clear_pause()
        assert not pause_flag.is_set()
        assert not reconciler.orders_paused


# ---------------------------------------------------------------------------
# Background thread
# ---------------------------------------------------------------------------

class TestReconcilerBackground:
    def test_background_thread_starts_and_stops(self):
        reconciler = Reconciler()
        broker = _make_broker({})
        tracker = _make_tracker({})

        reconciler.start_background(broker, tracker, interval_secs=60)
        assert reconciler._running
        assert reconciler._thread is not None
        assert reconciler._thread.is_alive()

        reconciler.stop()
        assert not reconciler._running

    def test_background_does_not_start_twice(self):
        reconciler = Reconciler()
        broker = _make_broker({})
        tracker = _make_tracker({})

        reconciler.start_background(broker, tracker, interval_secs=60)
        thread1 = reconciler._thread

        reconciler.start_background(broker, tracker, interval_secs=60)
        assert reconciler._thread is thread1  # same thread, not a new one

        reconciler.stop()

    def test_run_once_records_last_run(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 100})
        tracker = _make_tracker({"AAPL": 100})

        assert reconciler.last_run_at is None
        reconciler.run_once(broker, tracker)
        assert reconciler.last_run_at is not None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestReconcilerErrorHandling:
    def test_broker_get_positions_failure_returns_empty(self):
        reconciler = Reconciler()

        broken_broker = MagicMock()
        broken_broker.get_positions.side_effect = Exception("Network error")
        tracker = _make_tracker({"AAPL": 100})

        diffs = reconciler.run_once(broken_broker, tracker)
        assert diffs == []

    def test_tracker_attribute_error_returns_empty(self):
        reconciler = Reconciler()
        broker = _make_broker({"AAPL": 100})

        class BadTracker:
            @property
            def positions(self):
                raise RuntimeError("broken tracker")

        diffs = reconciler.run_once(broker, BadTracker())
        assert diffs == []
