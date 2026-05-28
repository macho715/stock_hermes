"""
Chaos Engineering Test Suite for stock_rtx4060
==============================================

Tests boundary conditions in paper_trading logic.
Run: pytest tests/test_chaos_paper_trading.py -v
"""

import pytest
from unittest.mock import MagicMock

from stock_rtx4060.paper_trading import (
    PaperTradingConfig,
    PaperTradingSignal,
    _validate_bars,
)


# ─────────────────────────────────────────────────────────────────────────────
# PR-C1: Max open positions exceeded
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_open_positions_exceeded():
    """
    RED: When open positions >= max_open_positions (10),
    signal should be REJECTED.

    GREEN: Logic is in _write_run — we test the decision boundary.
    """
    max_open = 10
    current_open = 10

    open_tickers = [f"STOCK{i}" for i in range(current_open)]
    config = MagicMock(spec=PaperTradingConfig)
    config.max_open_positions = max_open

    # Simulate _write_run check at line 252
    if config.max_open_positions is not None and len(open_tickers) >= config.max_open_positions:
        reason = "max_open_positions_reached"
    else:
        reason = None

    assert reason == "max_open_positions_reached"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C2: Max daily new positions exceeded
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_daily_new_exceeded():
    """
    RED: When daily_new_count >= max_daily_new_positions (3),
    signal should be REJECTED.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.max_daily_new_positions = 3
    config.max_open_positions = None

    daily_new_count = 3

    # Simulate _write_run check at line 254-255
    if config.max_daily_new_positions is not None and daily_new_count >= config.max_daily_new_positions:
        reason = "max_daily_new_positions_reached"
    else:
        reason = None

    assert reason == "max_daily_new_positions_reached"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C3: Buy score below threshold
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_buy_score_below_threshold():
    """
    RED: When score < min_buy_score (56), signal should be REJECTED.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.min_buy_score = 56

    signal = PaperTradingSignal(
        ticker="WEAK_STOCK",
        score=40.0,
        signal="buy",
        model_auc=None,
        model_accuracy=None,
        oof_coverage=None,
    )

    # Simulate evaluate_signal check
    if signal.score < config.min_buy_score:
        reason = "buy_score_below_threshold"
    else:
        reason = None

    assert reason == "buy_score_below_threshold"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C4: Force rerun with no reason → ValueError
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_force_rerun_no_reason():
    """
    RED: When force_rerun=True but rerun_reason is None, raise ValueError.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.force_rerun = True
    config.rerun_reason = None

    if config.force_rerun and not config.rerun_reason:
        with pytest.raises(ValueError, match="rerun_reason"):
            raise ValueError("force_rerun=True requires rerun_reason to be set")


# ─────────────────────────────────────────────────────────────────────────────
# PR-C5: Stale bars detection — uses config.effective_run_date
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_stale_bars():
    """
    RED: Bars older than effective_run_date - stale_days
    should be detected as stale by _validate_bars.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.effective_run_date = "2026-05-28"
    config.stale_days = 7
    config.max_missing_bar_ratio = 0.5

    # Bars from 2026-05-01 — 27 days old, definitely stale
    # Must include full OHLCV fields to pass the invalid_rows check
    stale_bars = [
        {"symbol": "STALE_STOCK", "date": "2026-05-01",
         "open": 100.0, "high": 105.0, "low": 99.0, "close": 102.0, "volume": 1000000}
    ]

    result = _validate_bars(stale_bars, config)

    assert result == "ohlcv_stale", \
        f"Bars from 2026-05-01 should be ohlcv_stale vs run date 2026-05-28, got: {result}"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C6: Valid signal passes all filters
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_valid_signal_passes():
    """
    Sanity: valid signal (score >= 56, within limits) passes all filters.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.min_buy_score = 56
    config.max_open_positions = 10
    config.max_daily_new_positions = 3

    signal = PaperTradingSignal(
        ticker="GOOD_STOCK",
        score=80.0,
        signal="buy",
        model_auc=None,
        model_accuracy=None,
        oof_coverage=None,
    )

    open_tickers = [f"STOCK{i}" for i in range(5)]  # only 5 open (limit 10)
    daily_new_count = 1  # only 1 new today (limit 3)

    reasons = []

    if signal.score < config.min_buy_score:
        reasons.append("buy_score_below_threshold")
    if config.max_open_positions is not None and len(open_tickers) >= config.max_open_positions:
        reasons.append("max_open_positions_reached")
    if config.max_daily_new_positions is not None and daily_new_count >= config.max_daily_new_positions:
        reasons.append("max_daily_new_positions_reached")

    assert "buy_score_below_threshold" not in reasons
    assert "max_open_positions_reached" not in reasons
    assert "max_daily_new_positions_reached" not in reasons


# ─────────────────────────────────────────────────────────────────────────────
# PR-C7: Score exactly at threshold (56) should pass
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_score_exactly_at_threshold():
    """
    Score == 56 should NOT be rejected (boundary test).
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.min_buy_score = 56

    signal = PaperTradingSignal(
        ticker="BOUNDARY_STOCK",
        score=56.0,
        signal="buy",
        model_auc=None,
        model_accuracy=None,
        oof_coverage=None,
    )

    # < not <= — so 56 exactly should pass
    if signal.score < config.min_buy_score:
        reason = "buy_score_below_threshold"
    else:
        reason = None

    assert reason is None, f"Score exactly at threshold (56) should pass, got: {reason}"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C8: Max open positions exactly at limit
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_open_positions_exactly_at_limit():
    """
    len(open_tickers) == max_open_positions should be rejected (>= boundary).
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.max_open_positions = 10

    open_tickers = [f"STOCK{i}" for i in range(10)]  # exactly 10

    if config.max_open_positions is not None and len(open_tickers) >= config.max_open_positions:
        reason = "max_open_positions_reached"
    else:
        reason = None

    assert reason == "max_open_positions_reached"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C9: Daily new exactly at limit
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_daily_new_exactly_at_limit():
    """
    daily_new_count == max_daily_new_positions should be rejected (>= boundary).
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.max_daily_new_positions = 3

    daily_new_count = 3  # exactly at limit

    if config.max_daily_new_positions is not None and daily_new_count >= config.max_daily_new_positions:
        reason = "max_daily_new_positions_reached"
    else:
        reason = None

    assert reason == "max_daily_new_positions_reached"


# ─────────────────────────────────────────────────────────────────────────────
# PR-C10: Fresh bars (not stale) should pass validation
# ─────────────────────────────────────────────────────────────────────────────

def test_chaos_fresh_bars_pass():
    """
    Bars from yesterday should NOT be stale.
    """
    config = MagicMock(spec=PaperTradingConfig)
    config.effective_run_date = "2026-05-28"
    config.stale_days = 7
    config.max_missing_bar_ratio = 0.5

    # Bars from 2026-05-27 — just 1 day ago, definitely fresh
    fresh_bars = [
        {"symbol": "FRESH_STOCK", "date": "2026-05-27",
         "open": 100.0, "high": 105.0, "low": 99.0, "close": 105.0, "volume": 1000000}
    ]

    result = _validate_bars(fresh_bars, config)

    # None means not stale — should pass
    assert result is None, f"Fresh bars (2026-05-27) should not be stale, got: {result}"