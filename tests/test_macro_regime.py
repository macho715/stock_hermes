"""Tests for :class:`stock_rtx4060.advisors.macro_regime.MacroRegimeAgent`."""

from __future__ import annotations

import asyncio

from stock_rtx4060.advisors.claude_client import CallResult
from stock_rtx4060.advisors.macro_regime import REGIME_TO_SCORE, MacroRegimeAgent


class _StubClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    async def acall(self, *, system, messages, tools=None, max_tokens=None):
        return CallResult(
            text=self.payload,
            raw_message=None,
            tokens_in=80,
            tokens_out=30,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.0008,
            prompt_hash="hash-macro",
            model="claude-opus-4-7",
        )


PANEL = {
    "t10y2y": 0.10,
    "vix": 14.0,
    "dxy": 102.0,
    "kospi_trend_pct": 0.05,
    "spy_trend_pct": 0.07,
    "krwusd": 1340.0,
}


def _run(payload: str, panel=PANEL):
    agent = MacroRegimeAgent(client=_StubClient(payload))
    ctx = {"macro_panel": panel}
    return asyncio.run(agent.analyze("SPY", ctx))


def test_macro_regime_risk_on_maps_positive():
    out = _run('{"regime": "risk_on", "confidence": 0.7, "rationale": "broad strength"}')
    assert out.score == REGIME_TO_SCORE["risk_on"]
    assert 0 < out.score


def test_macro_regime_risk_off_maps_negative():
    out = _run('{"regime": "risk_off", "confidence": 0.6, "rationale": "vol spike"}')
    assert out.score == REGIME_TO_SCORE["risk_off"]
    assert out.score < 0


def test_macro_regime_neutral_zero():
    out = _run('{"regime": "neutral", "confidence": 0.4, "rationale": "mixed"}')
    assert out.score == 0.0


def test_macro_regime_unknown_label_falls_back_to_score_sign():
    out = _run('{"regime": "spicy", "score": -0.4, "confidence": 0.5, "rationale": "x"}')
    assert out.score < 0


def test_macro_regime_returns_neutral_when_panel_unavailable():
    agent = MacroRegimeAgent(client=_StubClient("ignored"))
    out = asyncio.run(agent.analyze("SPY", {}))
    assert out.score == 0.0
    assert out.confidence == 0.0
    assert "macro" in out.rationale.lower()


def test_macro_regime_honors_explicit_score_in_risk_on_direction():
    out = _run('{"regime": "risk_on", "score": 0.6, "confidence": 0.9, "rationale": "x"}')
    # When LLM score is bigger than the floor in the same direction we keep it.
    assert out.score == 0.6
