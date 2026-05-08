"""Tests for compliance gate (Phase 8).

All 6 check types + ComplianceError messages.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stock_rtx4060.broker.compliance import (
    ComplianceConfig,
    ComplianceError,
    check_order,
    _check_single_position,
    _check_sector_exposure,
    _check_no_leverage,
    _check_krx_price_limit,
    _check_restricted_tickers,
    _check_wash_sale,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sector_map_file(tmp_path):
    sector_map = {
        "AAPL": "Technology",
        "MSFT": "Technology",
        "NVDA": "Technology",
        "005930": "Technology",
        "XOM": "Energy",
    }
    path = tmp_path / "sector_map.json"
    path.write_text(json.dumps(sector_map), encoding="utf-8")
    return path


@pytest.fixture
def restricted_file(tmp_path):
    path = tmp_path / "restricted.txt"
    path.write_text("BANNED_TICKER\n# comment\nSUSPECT\n", encoding="utf-8")
    return path


@pytest.fixture
def config(sector_map_file, restricted_file):
    return ComplianceConfig(
        max_single_position_pct=0.10,
        max_sector_exposure_pct=0.25,
        allow_leverage=False,
        krx_price_limit_pct=0.30,
        wash_sale_days=30,
        sector_map_path=sector_map_file,
        restricted_tickers_path=restricted_file,
    )


def _make_position(market_value: float, avg_cost: float = 100.0):
    pos = MagicMock()
    pos.market_value = market_value
    pos.avg_cost = avg_cost
    return pos


# ---------------------------------------------------------------------------
# 1. Single position limit
# ---------------------------------------------------------------------------

class TestSinglePositionCheck:
    def test_passes_within_limit(self):
        # 9% of 100k — OK
        _check_single_position("AAPL", 100, 90.0, 100_000.0, {}, 0.10)

    def test_fails_exceeds_limit(self):
        with pytest.raises(ComplianceError, match="Single-position"):
            _check_single_position("AAPL", 200, 90.0, 100_000.0, {}, 0.10)

    def test_existing_position_included(self):
        existing = {"AAPL": _make_position(market_value=8000.0)}
        with pytest.raises(ComplianceError, match="Single-position"):
            # 8k existing + 5*400=2000 new → 10k = 10% exactly = fails at >10%
            _check_single_position("AAPL", 50, 100.0, 100_000.0, existing, 0.10)
            # 50 * 100 + 8000 = 13000 > 10000 → fail

    def test_passes_with_zero_portfolio(self):
        # portfolio_value=0 → skip check
        _check_single_position("AAPL", 1000, 90.0, 0.0, {}, 0.10)


# ---------------------------------------------------------------------------
# 2. Sector exposure
# ---------------------------------------------------------------------------

class TestSectorExposureCheck:
    def test_passes_within_sector_limit(self, sector_map_file, tmp_path):
        cfg = ComplianceConfig(sector_map_path=sector_map_file, restricted_tickers_path=tmp_path/"r.txt")
        sector_map = cfg.load_sector_map()
        # MSFT existing 20k, AAPL new 2k → 22k/100k = 22% < 25%
        existing = {"MSFT": _make_position(20_000.0)}
        _check_sector_exposure("AAPL", 20, 100.0, 100_000.0, existing, sector_map, 0.25)

    def test_fails_exceeds_sector_limit(self, sector_map_file, tmp_path):
        cfg = ComplianceConfig(sector_map_path=sector_map_file, restricted_tickers_path=tmp_path/"r.txt")
        sector_map = cfg.load_sector_map()
        # MSFT 20k + NVDA 5k = 25k, add AAPL 10*100=1k → 26k/100k = 26% > 25%
        existing = {
            "MSFT": _make_position(20_000.0),
            "NVDA": _make_position(5_000.0),
        }
        with pytest.raises(ComplianceError, match="Sector exposure"):
            _check_sector_exposure("AAPL", 1000, 100.0, 100_000.0, existing, sector_map, 0.25)

    def test_unknown_ticker_skipped(self, sector_map_file, tmp_path):
        cfg = ComplianceConfig(sector_map_path=sector_map_file, restricted_tickers_path=tmp_path/"r.txt")
        sector_map = cfg.load_sector_map()
        # UNKNOWN not in sector map — no check performed
        _check_sector_exposure("UNKNOWN_TICKER", 100, 100.0, 100_000.0, {}, sector_map, 0.25)


# ---------------------------------------------------------------------------
# 3. No leverage
# ---------------------------------------------------------------------------

class TestNoLeverageCheck:
    def test_passes_no_leverage(self):
        # 20k existing + 10k new = 30k < 100k portfolio
        existing = {"MSFT": _make_position(20_000.0)}
        _check_no_leverage(100, 100.0, 100_000.0, existing)

    def test_fails_with_leverage(self):
        # 90k existing + 20k new = 110k > 100k portfolio
        existing = {"MSFT": _make_position(90_000.0)}
        with pytest.raises(ComplianceError, match="Leverage"):
            _check_no_leverage(200, 100.0, 100_000.0, existing)

    def test_passes_zero_portfolio(self):
        _check_no_leverage(100, 100.0, 0.0, {})


# ---------------------------------------------------------------------------
# 4. KRX price limit
# ---------------------------------------------------------------------------

class TestKRXPriceLimitCheck:
    def test_non_krx_skipped(self):
        _check_krx_price_limit("AAPL", 200.0, {}, 0.30)  # no exception

    def test_within_limit(self):
        pos = _make_position(market_value=1000.0, avg_cost=50000.0)
        existing = {"005930.KS": pos}
        # 51000 is +2% — within ±30%
        _check_krx_price_limit("005930.KS", 51000.0, existing, 0.30)

    def test_exceeds_limit(self):
        pos = _make_position(market_value=1000.0, avg_cost=50000.0)
        existing = {"005930.KS": pos}
        # 70000 is +40% — exceeds ±30%
        with pytest.raises(ComplianceError, match="KRX price limit"):
            _check_krx_price_limit("005930.KS", 70000.0, existing, 0.30)

    def test_no_existing_position_skipped(self):
        _check_krx_price_limit("005930.KS", 99999.0, {}, 0.30)


# ---------------------------------------------------------------------------
# 5. Restricted tickers
# ---------------------------------------------------------------------------

class TestRestrictedTickersCheck:
    def test_allowed_ticker_passes(self):
        _check_restricted_tickers("AAPL", {"BANNED_TICKER", "SUSPECT"})

    def test_restricted_ticker_fails(self):
        with pytest.raises(ComplianceError, match="restricted"):
            _check_restricted_tickers("BANNED_TICKER", {"BANNED_TICKER"})

    def test_case_insensitive(self):
        with pytest.raises(ComplianceError):
            _check_restricted_tickers("banned_ticker", {"BANNED_TICKER"})


# ---------------------------------------------------------------------------
# 6. Wash-sale
# ---------------------------------------------------------------------------

class TestWashSaleCheck:
    def test_sell_side_skipped(self):
        _check_wash_sale("AAPL", "SELL", None, 30)

    def test_krx_ticker_skipped(self):
        _check_wash_sale("005930.KS", "BUY", None, 30)

    def test_no_tracker_skipped(self):
        _check_wash_sale("AAPL", "BUY", None, 30)

    def test_no_recent_losses_passes(self):
        tracker = MagicMock()
        tracker.get_recent_closes.return_value = [
            {"date": (date.today() - timedelta(days=10)).isoformat(), "pnl": 100.0}  # profit, not a loss
        ]
        _check_wash_sale("AAPL", "BUY", tracker, 30)

    def test_recent_loss_sale_fails(self):
        tracker = MagicMock()
        tracker.get_recent_closes.return_value = [
            {"date": (date.today() - timedelta(days=5)).isoformat(), "pnl": -500.0}
        ]
        with pytest.raises(ComplianceError, match="Wash-sale"):
            _check_wash_sale("AAPL", "BUY", tracker, 30)

    def test_old_loss_sale_passes(self):
        tracker = MagicMock()
        tracker.get_recent_closes.return_value = [
            {"date": (date.today() - timedelta(days=45)).isoformat(), "pnl": -500.0}
        ]
        _check_wash_sale("AAPL", "BUY", tracker, 30)


# ---------------------------------------------------------------------------
# Integration: check_order
# ---------------------------------------------------------------------------

class TestCheckOrder:
    def test_full_pass(self, config):
        check_order(
            ticker="AAPL",
            qty=10,
            side="BUY",
            current_positions={},
            portfolio_value=200_000.0,
            config=config,
            price=100.0,
        )

    def test_restricted_ticker_fails(self, config):
        with pytest.raises(ComplianceError, match="restricted"):
            check_order(
                ticker="BANNED_TICKER",
                qty=10,
                side="BUY",
                current_positions={},
                portfolio_value=200_000.0,
                config=config,
                price=100.0,
            )

    def test_position_limit_fails(self, config):
        with pytest.raises(ComplianceError, match="Single-position"):
            check_order(
                ticker="AAPL",
                qty=3000,
                side="BUY",
                current_positions={},
                portfolio_value=100_000.0,
                config=config,
                price=100.0,
            )

    def test_no_leverage_fails(self, config):
        # Test leverage check directly (bypassing single-pos and sector checks).
        existing = {"MSFT": _make_position(95_000.0)}
        with pytest.raises(ComplianceError, match="[Ll]everage"):
            _check_no_leverage(200, 100.0, 100_000.0, existing)

    def test_sell_order_skips_notional_checks(self, config):
        # SELL orders skip single position / leverage / sector checks
        check_order(
            ticker="AAPL",
            qty=999999,
            side="SELL",
            current_positions={},
            portfolio_value=100_000.0,
            config=config,
            price=100.0,
        )

    def test_zero_price_skips_notional_checks(self, config):
        # price=0 → skip checks that require a price
        check_order(
            ticker="AAPL",
            qty=999999,
            side="BUY",
            current_positions={},
            portfolio_value=100_000.0,
            config=config,
            price=0.0,
        )

    def test_default_config_works(self):
        # Should not raise — AAPL is not in default restricted list
        check_order(
            ticker="AAPL",
            qty=1,
            side="BUY",
            current_positions={},
            portfolio_value=100_000.0,
            price=0.0,
        )
