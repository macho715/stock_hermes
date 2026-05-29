"""Unit tests for HierarchicalStore — L1/L2/L3 retrieval order (AMH Memory W4)."""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.memory.hierarchical_store import HierarchicalStore, RetrievalResult
from stock_rtx4060.advisors.memory.regime_memory import MemoryEntry, RegimeMemory, new_session_id


@pytest.fixture()
def mem():
    m = RegimeMemory(db_path=":memory:")
    yield m
    m.close()


@pytest.fixture()
def store(mem):
    return HierarchicalStore(mem, l1_k=5, l2_k=3)


def _entry(regime: str = "risk_off", ticker: str = "AAPL") -> MemoryEntry:
    return MemoryEntry(
        session_id=new_session_id(),
        ticker=ticker,
        ts="2026-05-29T10:00:00",
        regime_label=regime,
        final_score=-0.2,
        reasoning_chains={"news": "fear dominates"},
        logical_proposition="IF VIX>25 THEN bearish WITH 0.7",
        outcome_pct=None,
    )


def test_retrieve_returns_retrieval_result(store, mem):
    mem.write_episodic(_entry())
    result = store.retrieve("AAPL", "risk_off")
    assert isinstance(result, RetrievalResult)


def test_retrieve_l1_before_empty_l2_l3(store, mem):
    mem.write_episodic(_entry(ticker="AAPL"))
    result = store.retrieve("AAPL", "risk_off")
    assert len(result.l1_entries) >= 1
    assert result.l2_patterns == []   # none written
    assert result.l3_procedure == ""  # none written


def test_retrieve_with_l2_and_l3(store, mem):
    mem.write_episodic(_entry())
    mem.write_semantic("risk_off", "risk_off에서 뉴스 낙관은 덫")
    mem.set_procedure("devils_advocate", "risk_off", "Be extra sceptical")
    result = store.retrieve("AAPL", "risk_off", advisor_name="devils_advocate")
    assert len(result.l1_entries) >= 1
    assert len(result.l2_patterns) >= 1
    assert "sceptical" in result.l3_procedure
    assert result.total_retrieved >= 3


def test_retrieve_empty_regime_returns_empty(store):
    result = store.retrieve("AAPL", "")
    assert result.l1_entries == []
    assert result.l2_patterns == []


def test_retrieve_cross_asset(store, mem):
    """Cross-asset retrieval excludes the current ticker."""
    mem.write_episodic(_entry(ticker="AAPL"))
    mem.write_episodic(_entry(ticker="MSFT"))
    cross = store.retrieve_cross_asset("risk_off", exclude_ticker="AAPL", k=5)
    tickers = [e.ticker for e in cross]
    assert "AAPL" not in tickers
    assert "MSFT" in tickers


def test_as_context_dict_structure(store, mem):
    mem.write_episodic(_entry())
    result = store.retrieve("AAPL", "risk_off")
    ctx = result.as_context_dict()
    assert "episodic_memories" in ctx
    assert "semantic_patterns" in ctx
    assert "procedure" in ctx
    assert isinstance(ctx["episodic_memories"], list)
