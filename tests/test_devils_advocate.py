"""Tests for :class:`stock_rtx4060.advisors.devils_advocate.DevilsAdvocateAgent`."""

from __future__ import annotations

import asyncio

from stock_rtx4060.advisors.claude_client import CallResult
from stock_rtx4060.advisors.devils_advocate import DevilsAdvocateAgent


class _StubClient:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    async def acall(self, *, system, messages, tools=None, max_tokens=None):
        return CallResult(
            text=self.payload,
            raw_message=None,
            tokens_in=200,
            tokens_out=80,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.002,
            prompt_hash="hash-devils",
            model="claude-opus-4-7",
        )


def _run(payload: str, ctx=None):
    agent = DevilsAdvocateAgent(client=_StubClient(payload))
    return asyncio.run(agent.analyze("TSLA", ctx or {}))


def test_devils_advocate_negative_score_passes_through():
    out = _run(
        '{"score": -0.7, "confidence": 0.8, "rationale": "1) governance 2) margin 3) demand", "citations": ["10K"]}'
    )
    assert out.score == -0.7
    assert out.confidence == 0.8
    assert "governance" in out.rationale


def test_devils_advocate_positive_score_floored_to_zero():
    out = _run('{"score": 0.9, "confidence": 0.9, "rationale": "no risks?", "citations": []}')
    # The contract: this agent never confirms a bull case.
    assert out.score == 0.0
    # Negative confidence not implied — the model may still feel confident.
    assert 0.0 <= out.confidence <= 1.0


def test_devils_advocate_score_bounded_to_minus_one_to_zero():
    out = _run('{"score": -5, "confidence": 0.9, "rationale": "x"}')
    assert out.score == -1.0
    out = _run('{"score": 5, "confidence": 0.9, "rationale": "x"}')
    assert out.score == 0.0


def test_devils_advocate_uses_factor_and_shap_context():
    agent = DevilsAdvocateAgent(client=_StubClient('{"score": -0.2, "confidence": 0.5, "rationale": "ok"}'))
    out = asyncio.run(
        agent.analyze(
            "TSLA",
            {
                "factors": {"latest": 100.0, "atr_pct": 0.06},
                "shap": {"sma20": 0.3, "rsi": -0.1},
                "bull_summary": "TSLA score=72",
            },
        )
    )
    assert out.score == -0.2
