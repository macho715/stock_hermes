"""Tests for trade_journal module (Stage 4)."""

from __future__ import annotations

import pytest

from stock_rtx4060.trade_journal import (
    SCHEMA_VERSION,
    EntryState,
    JournalEntry,
    Outcome,
    TradeJournal,
)


class TestJournalEntry:
    """JournalEntry 단위 테스트."""

    def test_new_entry_has_id(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        assert entry.id != ""
        assert entry.state == EntryState.DRAFT.value

    def test_open_position(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10, entry_date="2026-05-01")
        assert entry.state == EntryState.OPEN.value
        assert entry.entry_price == 185.0
        assert entry.quantity == 10
        assert entry.entry_date == "2026-05-01"

    def test_close_position_tp(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10, entry_date="2026-05-01")
        entry.close_position(close_price=203.5, outcome=Outcome.TP.value, post_trade_notes="TP2 hit")
        assert entry.state == EntryState.CLOSED.value
        assert entry.outcome == Outcome.TP.value
        assert entry.realized_pnl_abs == pytest.approx((203.5 - 185.0) * 10)
        assert entry.realized_pnl_pct == pytest.approx((203.5 - 185.0) / 185.0)

    def test_close_position_stop(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10, entry_date="2026-05-01")
        entry.close_position(close_price=177.0, outcome=Outcome.STOP.value)
        assert entry.state == EntryState.CLOSED.value
        assert entry.realized_pnl_abs == pytest.approx((177.0 - 185.0) * 10)
        assert entry.outcome == Outcome.STOP.value

    def test_to_dict_includes_schema(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        d = entry.to_dict()
        assert d["schema_version"] == SCHEMA_VERSION
        assert d["ticker"] == "AAPL"

    def test_from_dict(self):
        entry = JournalEntry(ticker="AAPL", track="S")
        d = entry.to_dict()
        restored = JournalEntry.from_dict(d)
        assert restored.ticker == entry.ticker
        assert restored.id == entry.id


class TestTradeJournal:
    """TradeJournal 테스트."""

    def test_add_and_get_entry(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10, entry_date="2026-05-01")
        journal.add_entry(entry)

        retrieved = journal.get_entry(entry.id)
        assert retrieved is not None
        assert retrieved.ticker == "AAPL"
        assert retrieved.entry_price == 185.0

    def test_get_ticker_entry(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10)
        journal.add_entry(entry)

        found = journal.get_ticker_entry("AAPL", state=EntryState.OPEN.value)
        assert found is not None
        assert found.ticker == "AAPL"

        # Closed entry shouldn't be found as OPEN
        entry.close_position(close_price=200.0, outcome=Outcome.TP.value)
        journal.add_entry(entry)
        found_after_close = journal.get_ticker_entry("AAPL", state=EntryState.OPEN.value)
        assert found_after_close is None

    def test_list_entries_filter(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)
        for ticker in ["AAPL", "MSFT", "AAPL"]:
            entry = JournalEntry(ticker=ticker, track="S")
            entry.open_position(entry_price=185.0, quantity=10)
            journal.add_entry(entry)

        all_aapl = journal.list_entries(ticker="AAPL")
        assert len(all_aapl) == 2

        all_entries = journal.list_entries()
        assert len(all_entries) == 3

    def test_open_tickers(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)
        for ticker in ["AAPL", "MSFT"]:
            entry = JournalEntry(ticker=ticker, track="S")
            entry.open_position(entry_price=185.0, quantity=10)
            journal.add_entry(entry)

        # Close one
        e = journal.get_ticker_entry("AAPL")
        e.close_position(close_price=200.0, outcome=Outcome.TP.value)
        journal.add_entry(e)

        assert journal.open_tickers() == ["MSFT"]

    def test_statistics(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)

        # Win
        e1 = JournalEntry(ticker="AAPL", track="S")
        e1.open_position(entry_price=100.0, quantity=10, entry_date="2026-05-01")
        e1.close_position(close_price=110.0, outcome=Outcome.TP.value)
        journal.add_entry(e1)

        # Loss
        e2 = JournalEntry(ticker="MSFT", track="S")
        e2.open_position(entry_price=100.0, quantity=10, entry_date="2026-05-01")
        e2.close_position(close_price=95.0, outcome=Outcome.STOP.value)
        journal.add_entry(e2)

        # Open
        e3 = JournalEntry(ticker="NVDA", track="S")
        e3.open_position(entry_price=130.0, quantity=10, entry_date="2026-05-01")
        journal.add_entry(e3)

        stats = journal.statistics()
        assert stats["total_entries"] == 3
        assert stats["open_positions"] == 1
        assert stats["closed_positions"] == 2
        assert stats["win_count"] == 1
        assert stats["loss_count"] == 1
        assert stats["win_rate"] == pytest.approx(0.5)
        assert stats["total_realized_pnl"] == pytest.approx((110 - 100) * 10 + (95 - 100) * 10)

    def test_generate_report(self, tmp_path):
        journal = TradeJournal(output_dir=tmp_path)
        entry = JournalEntry(ticker="AAPL", track="S")
        entry.open_position(entry_price=185.0, quantity=10, entry_date="2026-05-01")
        entry.close_position(close_price=200.0, outcome=Outcome.TP.value)
        journal.add_entry(entry)

        json_path, md_path = journal.generate_report(output_dir=tmp_path)
        assert json_path.exists()
        assert md_path.exists()

        md = md_path.read_text(encoding="utf-8")
        assert "# Trade Journal Report" in md
        assert "AAPL" in md