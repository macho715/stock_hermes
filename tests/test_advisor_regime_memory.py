"""Unit tests for RegimeMemory — DuckDB L1/L2/L3 storage (AMH Memory W4)."""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.memory.regime_memory import MemoryEntry, RegimeMemory, new_session_id


@pytest.fixture()
def mem():
    """In-memory DuckDB instance — ephemeral, no file I/O."""
    m = RegimeMemory(db_path=":memory:")
    yield m
    m.close()


def _make_entry(regime: str = "risk_off", ticker: str = "AAPL", score: float = -0.3) -> MemoryEntry:
    return MemoryEntry(
        session_id=new_session_id(),
        ticker=ticker,
        ts="2026-05-29T10:00:00+00:00",
        regime_label=regime,
        final_score=score,
        reasoning_chains={"news_sentiment": "rate fears dominate"},
        logical_proposition="IF VIX>25 THEN bearish WITH 0.7",
        outcome_pct=None,
    )


def test_regime_memory_available(mem):
    assert mem.available is True


def test_write_and_read_episodic(mem):
    entry = _make_entry(regime="risk_off", ticker="AAPL")
    mem.write_episodic(entry)
    results = mem.query_episodic("risk_off", ticker="AAPL", k=5)
    assert len(results) == 1
    assert results[0].ticker == "AAPL"
    assert results[0].regime_label == "risk_off"
    assert results[0].logical_proposition == "IF VIX>25 THEN bearish WITH 0.7"


def test_regime_memory_does_not_cross_regime(mem):
    """Entries written to risk_off should NOT appear in risk_on queries."""
    mem.write_episodic(_make_entry(regime="risk_off"))
    results = mem.query_episodic("risk_on", k=5)
    assert results == []


def test_write_multiple_and_query_limit(mem):
    for i in range(7):
        e = _make_entry(ticker=f"TICK{i}")
        mem.write_episodic(e)
    results = mem.query_episodic("risk_off", k=3)
    assert len(results) == 3


def test_update_outcome(mem):
    entry = _make_entry()
    mem.write_episodic(entry)
    ok = mem.update_outcome(entry.session_id, 2.1)
    assert ok is True
    results = mem.query_episodic("risk_off", k=5)
    assert results[0].outcome_pct == pytest.approx(2.1)


def test_idempotent_write(mem):
    entry = _make_entry()
    mem.write_episodic(entry)
    mem.write_episodic(entry)  # second write of same session_id
    results = mem.query_episodic("risk_off", k=10)
    assert len(results) == 1  # no duplicates


def test_write_semantic_and_query(mem):
    mem.write_semantic("risk_off", "risk_off에서 뉴스 낙관은 평균 -2.3%")
    patterns = mem.query_semantic("risk_off")
    assert len(patterns) == 1
    assert "낙관" in patterns[0]


def test_procedure_round_trip(mem):
    mem.set_procedure("devils_advocate", "risk_off", "Increase scepticism of bullish signals")
    result = mem.get_procedure("devils_advocate", "risk_off")
    assert "scepticism" in result


def test_procedure_missing_returns_empty(mem):
    result = mem.get_procedure("nonexistent_agent", "risk_on")
    assert result == ""


def test_count_by_regime(mem):
    mem.write_episodic(_make_entry(regime="risk_off"))
    mem.write_episodic(_make_entry(regime="risk_off", ticker="MSFT"))
    mem.write_episodic(_make_entry(regime="risk_on"))
    counts = mem.count_by_regime()
    assert counts.get("risk_off", 0) == 2
    assert counts.get("risk_on", 0) == 1


def test_empty_regime_query_returns_empty(mem):
    results = mem.query_episodic("", ticker="AAPL", k=5)
    assert results == []


def test_new_session_id_unique():
    ids = {new_session_id() for _ in range(10)}
    assert len(ids) == 10
