"""Tests for the advisor orchestrator (sync fallback path)."""

from __future__ import annotations

import asyncio

from stock_rtx4060.advisors.base import AdvisoryOutput
from stock_rtx4060.advisors.orchestrator import DEFAULT_WEIGHTS, Orchestrator


class _StaticAgent:
    def __init__(self, name: str, score: float, confidence: float) -> None:
        self.name = name
        self._score = score
        self._confidence = confidence
        self.invocations = 0

    async def analyze(self, ticker: str, context: dict) -> AdvisoryOutput:
        self.invocations += 1
        return AdvisoryOutput(
            agent=self.name,
            ticker=ticker,
            score=self._score,
            confidence=self._confidence,
            rationale=f"{self.name} rationale",
            citations=[f"{self.name}-cite"],
            prompt_hash=f"{self.name}-hash",
            tokens_in=10,
            tokens_out=5,
            cost_usd=0.0001,
        )


def test_orchestrator_runs_all_three_agents_and_blends():
    news = _StaticAgent("news_sentiment", 0.6, 1.0)
    macro = _StaticAgent("macro_regime", 0.3, 1.0)
    devils = _StaticAgent("devils_advocate", -0.4, 1.0)
    orch = Orchestrator(news=news, devils=devils, macro=macro)
    result = orch.analyze("AAPL", {})
    assert {o.agent for o in result.outputs} == {"news_sentiment", "macro_regime", "devils_advocate"}
    # Confidence-weighted blend with all confidences = 1.0:
    expected = 0.6 * 0.4 + (-0.4) * 0.3 + 0.3 * 0.3
    assert abs(result.advisory_score - expected) < 1e-9
    assert news.invocations == macro.invocations == devils.invocations == 1


def test_orchestrator_handles_zero_confidence_abstention():
    # If news has confidence 0.0 we expect it to be ignored — so the
    # blend reflects only macro + devils.
    news = _StaticAgent("news_sentiment", 0.9, 0.0)
    macro = _StaticAgent("macro_regime", 0.0, 1.0)
    devils = _StaticAgent("devils_advocate", -0.5, 1.0)
    orch = Orchestrator(news=news, devils=devils, macro=macro)
    result = orch.analyze("AAPL", {})
    expected_num = 0.0 * 1.0 * 0.3 + (-0.5) * 1.0 * 0.3
    expected_den = 1.0 * 0.3 + 1.0 * 0.3
    assert abs(result.advisory_score - expected_num / expected_den) < 1e-9


def test_orchestrator_returns_zero_score_when_all_abstain():
    news = _StaticAgent("news_sentiment", 0.5, 0.0)
    macro = _StaticAgent("macro_regime", 0.5, 0.0)
    devils = _StaticAgent("devils_advocate", -0.5, 0.0)
    orch = Orchestrator(news=news, devils=devils, macro=macro)
    result = orch.analyze("AAPL", {})
    assert result.advisory_score == 0.0
    assert result.confidence == 0.0


def test_orchestrator_async_path_matches_sync():
    news = _StaticAgent("news_sentiment", 0.4, 0.5)
    macro = _StaticAgent("macro_regime", 0.0, 0.4)
    devils = _StaticAgent("devils_advocate", -0.2, 0.6)
    orch = Orchestrator(news=news, devils=devils, macro=macro)
    sync = orch.analyze("AAPL", {})
    asy = asyncio.run(orch.aanalyze("AAPL", {}))
    assert abs(sync.advisory_score - asy.advisory_score) < 1e-12


def test_default_weights_sum_to_one():
    assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9


def test_orchestrator_devils_sees_prior_outputs():
    captured: list[dict] = []

    class _CaptureDevils(_StaticAgent):
        async def analyze(self, ticker, context):
            captured.append(context)
            return await super().analyze(ticker, context)

    news = _StaticAgent("news_sentiment", 0.4, 1.0)
    macro = _StaticAgent("macro_regime", 0.0, 1.0)
    devils = _CaptureDevils("devils_advocate", -0.3, 1.0)
    orch = Orchestrator(news=news, devils=devils, macro=macro)
    orch.analyze("AAPL", {})

    assert captured, "devils_advocate must be invoked"
    prior = captured[0].get("prior_outputs", [])
    assert any(p.get("agent") == "news_sentiment" for p in prior)
    assert any(p.get("agent") == "macro_regime" for p in prior)
