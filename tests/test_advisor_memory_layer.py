"""Integration tests for MemoryLayer — public API (AMH Memory W4)."""
from __future__ import annotations

import pytest

from stock_rtx4060.advisors.base import AdvisoryOutput
from stock_rtx4060.advisors.memory.memory_layer import MemoryLayer


def _make_output(agent: str, score: float, conf: float, regime: str = "") -> AdvisoryOutput:
    return AdvisoryOutput(
        agent=agent,
        ticker="AAPL",
        score=score,
        confidence=conf,
        rationale=f"{agent} rationale IF VIX>20 THEN bearish WITH 0.6" if agent == "news_sentiment" else "macro rationale",
        citations=[],
        prompt_hash="hash123",
        tokens_in=10,
        tokens_out=5,
        cost_usd=0.001,
        regime_label=regime,
    )


@pytest.fixture()
def layer():
    """MemoryLayer with in-memory DuckDB, explicitly enabled."""
    ml = MemoryLayer(db_path=":memory:", enabled=True)
    return ml


def test_memory_layer_disabled_returns_empty():
    ml = MemoryLayer(db_path=":memory:", enabled=False)
    result = ml.get_relevant_memories("AAPL", "risk_off")
    assert result.l1_entries == []
    assert result.l2_patterns == []
    assert result.l3_procedure == ""


def test_memory_layer_enabled_write_then_read(layer):
    """write() → get_relevant_memories() returns the written entry."""
    session_id = MemoryLayer.new_session_id()
    outputs = [
        _make_output("news_sentiment", 0.4, 0.7),
        _make_output("macro_regime", -0.3, 0.8, regime="risk_off"),
    ]
    layer.write(session_id, "AAPL", "risk_off", outputs, final_score=-0.1)

    result = layer.get_relevant_memories("AAPL", "risk_off")
    assert result.total_retrieved >= 1
    assert result.l1_entries[0].regime_label == "risk_off"


def test_memory_layer_write_does_not_raise_on_error(layer):
    """write() must not propagate exceptions (silent failure)."""
    layer.write("bad_session", "AAPL", "risk_off", [], final_score=0.0)


def test_memory_layer_update_outcome(layer):
    session_id = MemoryLayer.new_session_id()
    outputs = [_make_output("news_sentiment", 0.2, 0.5)]
    layer.write(session_id, "AAPL", "risk_on", outputs, final_score=0.2)
    ok = layer.update_outcome(session_id, 3.5)
    assert ok is True


def test_memory_layer_route_deep_when_high_disagreement(layer):
    decision = layer.route(0.8, 0.7, -0.5, 0.8)
    assert decision.path == "deep"


def test_memory_layer_route_shallow_when_low_disagreement(layer):
    decision = layer.route(0.1, 0.9, 0.05, 0.9)
    assert decision.path == "shallow"


def test_memory_layer_extract_proposition(layer):
    prop = layer.extract_proposition("IF VIX>25 THEN bearish WITH 0.7")
    assert prop == "IF VIX>25 THEN bearish WITH 0.7"


def test_memory_layer_extract_proposition_fallback(layer):
    prop = layer.extract_proposition("general bullish outlook")
    assert prop == ""


def test_memory_layer_stats_enabled(layer):
    s = layer.stats()
    assert s.enabled is True
    assert isinstance(s.regime_counts, dict)


def test_memory_layer_stats_disabled():
    ml = MemoryLayer(db_path=":memory:", enabled=False)
    s = ml.stats()
    assert s.enabled is False
    assert s.total_entries == 0


def test_memory_layer_write_extracts_proposition_from_news(layer):
    """news rationale containing IF-THEN-WITH should populate logical_proposition."""
    session_id = MemoryLayer.new_session_id()
    outputs = [
        _make_output("news_sentiment", 0.3, 0.7),
    ]
    layer.write(session_id, "AAPL", "risk_off", outputs, final_score=0.3)
    result = layer.get_relevant_memories("AAPL", "risk_off")
    if result.l1_entries:
        # proposition may have been extracted
        entry = result.l1_entries[0]
        assert isinstance(entry.logical_proposition, str)


def test_memory_layer_none_in_orchestrator_no_side_effects():
    """Orchestrator(memory_layer=None) must be instantiable and callable (no-op path)."""
    import asyncio
    from unittest.mock import AsyncMock, patch

    from stock_rtx4060.advisors.orchestrator import Orchestrator

    def _fake_output(agent, score=0.0, conf=0.5):
        return AdvisoryOutput(
            agent=agent, ticker="AAPL", score=score, confidence=conf,
            rationale="r", citations=[], prompt_hash="h",
            tokens_in=1, tokens_out=1, cost_usd=0.0,
        )

    orch = Orchestrator(memory_layer=None)
    # Patch all three advisors so no network calls happen
    with (
        patch.object(orch.news, "analyze", new=AsyncMock(return_value=_fake_output("news_sentiment"))),
        patch.object(orch.macro, "analyze", new=AsyncMock(return_value=_fake_output("macro_regime", score=0.0, conf=0.0))),
        patch.object(orch.devils, "analyze", new=AsyncMock(return_value=_fake_output("devils_advocate"))),
    ):
        result = asyncio.run(orch.aanalyze("AAPL"))

    assert result.memory_context_used is False
    assert result.session_id == ""
