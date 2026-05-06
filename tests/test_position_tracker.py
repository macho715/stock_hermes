"""Tests for position_tracker module (Stage 1)."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from stock_rtx4060.position_tracker import (
    PositionStatus,
    CloseReason,
    PriceQuote,
    TrackedPosition,
    PortfolioSnapshot,
    fetch_quote,
    fetch_quotes_bulk,
    load_positions_from_recommendation_json,
    save_portfolio_snapshot,
    refresh_positions,
    SCHEMA_VERSION,
)


class TestTrackedPosition:
    """단위 테스트: TrackedPosition 상태 머신."""

    def test_new_position_uninitialized(self):
        pos = TrackedPosition(
            ticker="AAPL",
            track="S",
            entry_date="2026-05-01",
            entry_price=150.0,
            quantity=10,
            stop=142.5,
            tp1=157.5,
            tp2=165.0,
        )
        assert pos.status == PositionStatus.UNINITIALIZED.value
        assert pos.unrealized_pnl_pct == 0.0

    def test_mark_open(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=152.0, timestamp_utc="2026-05-01T10:00:00Z")
        assert pos.status == PositionStatus.OPEN.value
        assert pos.current_price == 152.0
        assert pos.unrealized_pnl_pct == pytest.approx((152.0 - 150.0) / 150.0)
        assert pos.unrealized_pnl_abs == pytest.approx((152.0 - 150.0) * 10)

    def test_stop_loss_triggers_close(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=152.0, timestamp_utc="2026-05-01T10:00:00Z")
        reason = pos.update(current_price=142.0, timestamp_utc="2026-05-01T12:00:00Z")
        assert reason == CloseReason.STOP_HIT.value
        assert pos.status == PositionStatus.CLOSED_BY_STOP.value
        assert pos.close_reason == CloseReason.STOP_HIT.value
        assert pos.close_date is not None

    def test_tp2_triggers_close(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=152.0, timestamp_utc="2026-05-01T10:00:00Z")
        reason = pos.update(current_price=166.0, timestamp_utc="2026-05-01T14:00:00Z")
        assert reason == CloseReason.TP2_HIT.value
        assert pos.status == PositionStatus.CLOSED_BY_TP2.value

    def test_trailing_stop_activation(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=150.0, timestamp_utc="2026-05-01T10:00:00Z")
        assert not pos.trailing_stop_activated
        # Move to TP1
        pos.update(current_price=158.0, timestamp_utc="2026-05-01T11:00:00Z")
        assert pos.trailing_stop_activated
        # Pull back to trailing stop level: entry + (peak - entry) * 0.5 = 150 + (158-150)*0.5 = 154
        reason = pos.update(current_price=153.5, timestamp_utc="2026-05-01T12:00:00Z")
        assert reason == CloseReason.TRAILING_STOP.value
        assert pos.status == PositionStatus.CLOSED_BY_STOP.value

    def test_stop_approaching_warning(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=145.5, timestamp_utc="2026-05-01T10:00:00Z")
        # distance_to_stop_pct = (145.5 - 142.5) / 142.5 ≈ 2.1% < 3%
        assert pos.status == PositionStatus.STOP_APPROACHING.value

    def test_tp_approaching_warning(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=163.0, timestamp_utc="2026-05-01T10:00:00Z")
        # distance_to_tp2_pct = (165 - 163) / 163 ≈ 1.2% < 3%
        assert pos.status == PositionStatus.TP_APPROACHING.value

    def test_to_dict_schema_version(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        d = pos.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert d["ticker"] == "AAPL"
        assert d["track"] == "S"
        assert d["entry_price"] == 150.0


class TestPortfolioSnapshot:
    """포트폴리오 스냅샷 테스트."""

    def test_from_positions_open_and_closed(self):
        open_pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        open_pos.mark_open(current_price=155.0, timestamp_utc="2026-05-01T10:00:00Z")

        closed_pos = TrackedPosition(
            ticker="MSFT", track="L", entry_date="2026-04-01",
            entry_price=400.0, quantity=5, stop=380.0, tp1=420.0, tp2=440.0,
        )
        closed_pos.mark_open(current_price=405.0, timestamp_utc="2026-04-01T10:00:00Z")
        closed_pos.update(current_price=442.0, timestamp_utc="2026-04-15T14:00:00Z")
        assert closed_pos.status == PositionStatus.CLOSED_BY_TP2.value

        snapshot = PortfolioSnapshot.from_positions([open_pos, closed_pos])
        assert snapshot.total_positions == 2
        assert snapshot.open_positions == 1
        assert snapshot.closed_positions == 1
        # Unrealized from open position only
        assert snapshot.total_unrealized_pnl_abs == pytest.approx((155.0 - 150.0) * 10)
        assert snapshot.total_exposure == 155.0 * 10

    def test_track_separation(self):
        pos_s = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos_s.mark_open(current_price=155.0, timestamp_utc="2026-05-01T10:00:00Z")

        pos_l = TrackedPosition(
            ticker="MSFT", track="L", entry_date="2026-05-01",
            entry_price=400.0, quantity=5, stop=360.0, tp1=440.0, tp2=480.0,
        )
        pos_l.mark_open(current_price=410.0, timestamp_utc="2026-05-01T10:00:00Z")

        snapshot = PortfolioSnapshot.from_positions([pos_s, pos_l])
        assert snapshot.track_s_value == 155.0 * 10
        assert snapshot.track_l_value == 410.0 * 5

    def test_warning_tickers(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=145.5, timestamp_utc="2026-05-01T10:00:00Z")
        snapshot = PortfolioSnapshot.from_positions([pos])
        assert "AAPL" in snapshot.stop_approaching_tickers
        assert snapshot.warning_count == 1


class TestPriceQuote:
    """PriceQuote 테스트."""

    def test_price_quote_to_dict(self):
        quote = PriceQuote(ticker="AAPL", current_price=155.5, timestamp_utc="2026-05-01T10:00:00Z", currency="USD")
        d = quote.to_dict()
        assert d["ticker"] == "AAPL"
        assert d["current_price"] == 155.5
        assert d["currency"] == "USD"


class TestLoadRecommendationJson:
    """recommendation JSON 로드 테스트."""

    def test_load_eligible_recommendation(self, tmp_path):
        rec_json = {
            "results": [
                {
                    "ticker": "AAPL",
                    "track": "S",
                    "verdict": "ELIGIBLE_RECOMMENDATION",
                    "entry": 150.0,
                    "stop": 142.5,
                    "tp1": 157.5,
                    "tp2": 165.0,
                    "suggested_quantity": 10,
                    "generated_at_utc": "2026-05-01T10:00:00Z",
                },
                {
                    "ticker": "MSFT",
                    "track": "L",
                    "verdict": "RED_NOT_RECOMMENDED",
                    "entry": 400.0,
                    "stop": 360.0,
                    "tp1": 440.0,
                    "tp2": 480.0,
                    "suggested_quantity": 5,
                    "generated_at_utc": "2026-05-01T10:00:00Z",
                },
            ]
        }
        json_path = tmp_path / "recommendations.json"
        json_path.write_text(json.dumps(rec_json), encoding="utf-8")

        positions = load_positions_from_recommendation_json(json_path)
        assert len(positions) == 1  # only ELIGIBLE_RECOMMENDATION
        assert positions[0].ticker == "AAPL"
        assert positions[0].track == "S"
        assert positions[0].entry_price == 150.0
        assert positions[0].stop == 142.5


class TestSaveSnapshot:
    """스냅샷 저장 테스트."""

    def test_save_json_and_md(self, tmp_path):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=155.0, timestamp_utc="2026-05-01T10:00:00Z")
        snapshot = PortfolioSnapshot.from_positions([pos])

        json_path, md_path = save_portfolio_snapshot(snapshot, tmp_path)

        assert json_path.exists()
        assert md_path.exists()

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["total_positions"] == 1
        assert data["open_positions"] == 1

        md = md_path.read_text(encoding="utf-8")
        assert "# Portfolio Snapshot" in md
        assert "AAPL" in md


class TestRefreshPositions:
    """refresh_positions 시그니처 테스트 (yfinance mocking 없음)."""

    def test_refresh_skips_closed_positions(self):
        pos = TrackedPosition(
            ticker="AAPL", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=152.0, timestamp_utc="2026-05-01T10:00:00Z")
        pos.update(current_price=166.0, timestamp_utc="2026-05-01T14:00:00Z")  # TP2 hit

        refreshed = refresh_positions([pos], delay=0.0)
        assert len(refreshed) == 1
        assert refreshed[0].status == PositionStatus.CLOSED_BY_TP2.value

    def test_refresh_handles_missing_quote(self):
        pos = TrackedPosition(
            ticker="NONEXISTTICKERXYZV", track="S", entry_date="2026-05-01",
            entry_price=150.0, quantity=10, stop=142.5, tp1=157.5, tp2=165.0,
        )
        pos.mark_open(current_price=150.0, timestamp_utc="2026-05-01T10:00:00Z")
        refreshed = refresh_positions([pos], delay=0.0)
        # Should not crash, position stays open
        assert refreshed[0].status == PositionStatus.OPEN.value