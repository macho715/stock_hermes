"""Tests for portfolio_analytics module (Stage 3)."""

from __future__ import annotations

import pytest

from stock_rtx4060.portfolio_analytics import (
    PortfolioAnalytics,
    PortfolioSnapshot,
    _estimate_sector,
    _estimate_portfolio_beta,
    _compute_var_1d_95,
    _is_open,
    analyze_portfolio,
    save_analytics_report,
    SCHEMA_VERSION,
)
from stock_rtx4060.position_tracker import PositionStatus, TrackedPosition


class TestEstimateSector:
    """Sector 추정 테스트."""

    def test_known_tickers(self):
        assert _estimate_sector("AAPL") == "Technology"
        assert _estimate_sector("MSFT") == "Technology"
        assert _estimate_sector("XOM") == "Energy"
        assert _estimate_sector("JPM") == "Financial Services"
        assert _estimate_sector("LLY") == "Healthcare"
        assert _estimate_sector("GLD") == "Commodities"
        assert _estimate_sector("SPY") == "Broad Market"

    def test_unknown_ticker(self):
        assert _estimate_sector("XYZUNKNOWN") == "Other"


class TestIsOpen:
    """Position 상태 분류 테스트."""

    def test_open_statuses(self):
        assert _is_open(PositionStatus.OPEN.value)
        assert _is_open(PositionStatus.STOP_APPROACHING.value)
        assert _is_open(PositionStatus.TP_APPROACHING.value)

    def test_closed_statuses(self):
        assert not _is_open(PositionStatus.CLOSED_BY_STOP.value)
        assert not _is_open(PositionStatus.CLOSED_BY_TP2.value)
        assert not _is_open(PositionStatus.MANUAL_CLOSE.value)
        assert not _is_open(PositionStatus.UNINITIALIZED.value)


class TestEstimateBeta:
    """Beta 추정 테스트."""

    def test_single_tech_position(self):
        positions = [{"ticker": "AAPL", "current_price": 185.0, "quantity": 10}]
        assert _estimate_portfolio_beta(positions) == pytest.approx(1.30)

    def test_mixed_sectors(self):
        positions = [
            {"ticker": "AAPL", "current_price": 185.0, "quantity": 10},
            {"ticker": "XOM", "current_price": 100.0, "quantity": 10},
        ]
        # tech: 1850 * 1.30 = 2405; energy: 1000 * 1.05 = 1050; total = 2850
        # beta = 2405/2850*1.30 + 1050/2850*1.05
        beta = _estimate_portfolio_beta(positions)
        assert 1.10 < beta < 1.30


class TestVar:
    """VaR 계산 테스트."""

    def test_var_with_default_vol(self):
        positions = [{"ticker": "AAPL", "current_price": 185.0, "quantity": 10, "hist_vol_20": 0.02}]
        var = _compute_var_1d_95(positions)
        assert var == pytest.approx(1.65 * 0.02, rel=1e-10)

    def test_var_empty(self):
        assert _compute_var_1d_95([]) == 0.0


class TestPortfolioAnalytics:
    """PortfolioAnalytics.from_snapshot 테스트."""

    def _make_snapshot(self, tickers_with_prices: list[tuple[str, float, float, int]]) -> PortfolioSnapshot:
        """(ticker, entry_price, current_price, quantity)."""
        positions = []
        for ticker, entry, current, qty in tickers_with_prices:
            p = TrackedPosition(
                ticker=ticker, track="S", entry_date="2026-05-01",
                entry_price=entry, quantity=qty,
                stop=entry * 0.96, tp1=entry * 1.05, tp2=entry * 1.10,
            )
            p.mark_open(current_price=current, timestamp_utc="2026-05-01T10:00:00Z")
            positions.append(p)
        return PortfolioSnapshot.from_positions(positions)

    def test_total_exposure(self):
        snapshot = self._make_snapshot([("AAPL", 185.0, 190.0, 10)])
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        assert analytics.total_position_value == pytest.approx(1900.0)
        assert analytics.total_exposure_pct == pytest.approx(0.019)

    def test_track_separation(self):
        p1 = TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5)
        p1.mark_open(current_price=190.0, timestamp_utc="2026-05-01T10:00:00Z")
        p2 = TrackedPosition(ticker="MSFT", track="L", entry_date="2026-05-01", entry_price=415.0, quantity=5, stop=375.0, tp1=450.0, tp2=498.0)
        p2.mark_open(current_price=420.0, timestamp_utc="2026-05-01T10:00:00Z")
        snapshot = PortfolioSnapshot.from_positions([p1, p2])
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        assert analytics.track_s_exposure_pct == pytest.approx(1900 / 100_000)
        assert analytics.track_l_exposure_pct == pytest.approx(2100 / 100_000)

    def test_concentration_risk(self):
        # 4x same-sector tech positions worth ~25% each
        snapshot = self._make_snapshot([
            ("AAPL", 185.0, 185.0, 135),   # 135*185 ≈ 25000
            ("MSFT", 415.0, 415.0, 60),    # 60*415 ≈ 25000
            ("NVDA", 130.0, 130.0, 192),   # 192*130 ≈ 25000
            ("AMD", 165.0, 165.0, 152),    # 152*165 ≈ 25000
        ])
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        # All technology — each 25% → concentration = 100%
        assert analytics.concentrated_sector == "Technology"
        assert analytics.concentration_risk_pct == pytest.approx(1.0)

    def test_rebalance_needed_when_overallocated(self):
        # Track-S exposure > 20% should trigger rebalance
        snapshot = self._make_snapshot([("AAPL", 185.0, 185.0, 200)])  # 200*185 = 37000 = 37% > 20%
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        assert analytics.rebalance_needed is True
        assert any("Track-S" in s for s in analytics.rebalance_suggestions)

    def test_cash_buffer_warning(self):
        # Very high exposure leaves little cash
        snapshot = self._make_snapshot([("AAPL", 185.0, 185.0, 515)])  # 515*185 = 95275 → 4.7% cash < 5% threshold
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        assert analytics.rebalance_needed is True
        assert analytics.cash_remaining_pct < 0.05

    def test_sector_weights_sum_to_one(self):
        snapshot = self._make_snapshot([
            ("AAPL", 185.0, 185.0, 54),   # Technology
            ("XOM", 100.0, 100.0, 100),   # Energy
        ])
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)
        total = sum(analytics.sector_weights.values())
        assert total == pytest.approx(1.0, abs=0.001)

    def test_schema_version(self):
        snapshot = self._make_snapshot([("AAPL", 185.0, 190.0, 10)])
        analytics = PortfolioAnalytics.from_snapshot(snapshot)
        assert analytics.schema_version == SCHEMA_VERSION


class TestSaveAnalyticsReport:
    """저장 테스트."""

    def test_save_json_and_md(self, tmp_path):
        from datetime import datetime, timezone
        p = TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5)
        p.mark_open(current_price=190.0, timestamp_utc="2026-05-01T10:00:00Z")
        snapshot = PortfolioSnapshot.from_positions([p])
        analytics = PortfolioAnalytics.from_snapshot(snapshot, capital=100_000.0)

        json_path, md_path = save_analytics_report(analytics, tmp_path)
        assert json_path.exists()
        assert md_path.exists()
        md = md_path.read_text(encoding="utf-8")
        assert "# Portfolio Analytics" in md
        assert "Exposure" in md