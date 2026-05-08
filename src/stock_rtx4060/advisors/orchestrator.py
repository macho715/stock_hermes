"""Advisor orchestration.

Two execution paths:

* a synchronous fallback (default) that runs News + Macro in parallel via
  :func:`asyncio.gather` and then DevilsAdvocate sequentially with the
  earlier outputs as additional context;
* an opt-in LangGraph path (when :mod:`langgraph` is installed) that
  exposes the same DAG.

Both paths emit identical :class:`AdvisoryOutput` lists and produce the
same blended ``advisory_score``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from .base import Advisor, AdvisoryOutput
from .devils_advocate import DevilsAdvocateAgent
from .macro_regime import MacroRegimeAgent
from .news_sentiment import NewsSentimentAgent

logger = logging.getLogger(__name__)


DEFAULT_WEIGHTS = {
    "news_sentiment": 0.40,
    "devils_advocate": 0.30,
    "macro_regime": 0.30,
}


@dataclass
class OrchestratorResult:
    advisory_score: float
    confidence: float
    outputs: list[AdvisoryOutput]


@dataclass
class Orchestrator:
    news: Advisor = field(default_factory=NewsSentimentAgent)
    devils: Advisor = field(default_factory=DevilsAdvocateAgent)
    macro: Advisor = field(default_factory=MacroRegimeAgent)
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    use_langgraph: bool = False

    async def aanalyze(self, ticker: str, context: dict[str, Any] | None = None) -> OrchestratorResult:
        ctx = dict(context or {})
        if self.use_langgraph and _langgraph_available():
            outputs = await self._langgraph_run(ticker, ctx)
        else:
            outputs = await self._fallback_run(ticker, ctx)
        score, confidence = self._blend(outputs)
        return OrchestratorResult(advisory_score=score, confidence=confidence, outputs=outputs)

    def analyze(self, ticker: str, context: dict[str, Any] | None = None) -> OrchestratorResult:
        """Synchronous facade — useful for the recommendation engine."""
        return asyncio.run(self.aanalyze(ticker, context))

    # ------------------------------------------------------------------

    async def _fallback_run(self, ticker: str, ctx: dict[str, Any]) -> list[AdvisoryOutput]:
        # News + Macro can run in parallel — neither depends on the other.
        news_task = asyncio.create_task(self.news.analyze(ticker, ctx))
        macro_task = asyncio.create_task(self.macro.analyze(ticker, ctx))
        news_out, macro_out = await asyncio.gather(news_task, macro_task)
        # DevilsAdvocate runs after — it benefits from seeing the earlier outputs.
        devils_ctx = dict(ctx)
        devils_ctx.setdefault("prior_outputs", []).append(_to_dict(news_out))
        devils_ctx["prior_outputs"].append(_to_dict(macro_out))
        devils_out = await self.devils.analyze(ticker, devils_ctx)
        return [news_out, devils_out, macro_out]

    async def _langgraph_run(
        self, ticker: str, ctx: dict[str, Any]
    ) -> list[AdvisoryOutput]:  # pragma: no cover - optional
        try:
            from langgraph.graph import END, StateGraph  # type: ignore[import-not-found]
        except ImportError:
            return await self._fallback_run(ticker, ctx)

        async def news_node(state: dict[str, Any]) -> dict[str, Any]:
            state["news"] = await self.news.analyze(ticker, ctx)
            return state

        async def macro_node(state: dict[str, Any]) -> dict[str, Any]:
            state["macro"] = await self.macro.analyze(ticker, ctx)
            return state

        async def devils_node(state: dict[str, Any]) -> dict[str, Any]:
            d_ctx = dict(ctx)
            d_ctx["prior_outputs"] = [_to_dict(state["news"]), _to_dict(state["macro"])]
            state["devils"] = await self.devils.analyze(ticker, d_ctx)
            return state

        builder: Any = StateGraph(dict)
        builder.add_node("news", news_node)
        builder.add_node("macro", macro_node)
        builder.add_node("devils", devils_node)
        builder.set_entry_point("news")
        builder.add_edge("news", "macro")
        builder.add_edge("macro", "devils")
        builder.add_edge("devils", END)
        graph = builder.compile()
        final_state: dict[str, Any] = await graph.ainvoke({})
        return [final_state["news"], final_state["devils"], final_state["macro"]]

    def _blend(self, outputs: list[AdvisoryOutput]) -> tuple[float, float]:
        weighted_score = 0.0
        weighted_conf = 0.0
        total_weight = 0.0
        total_conf_weight = 0.0
        for out in outputs:
            w = float(self.weights.get(out.agent, 0.0))
            if w <= 0.0:
                continue
            weighted_score += out.score * out.confidence * w
            total_weight += out.confidence * w
            weighted_conf += out.confidence * w
            total_conf_weight += w
        # Score normalises by confidence-weighted weight so abstaining
        # advisors don't drag the verdict toward zero.
        score = weighted_score / total_weight if total_weight > 0 else 0.0
        confidence = weighted_conf / total_conf_weight if total_conf_weight > 0 else 0.0
        score = max(-1.0, min(1.0, score))
        confidence = max(0.0, min(1.0, confidence))
        return float(score), float(confidence)


def _to_dict(out: AdvisoryOutput) -> dict[str, Any]:
    return {
        "agent": out.agent,
        "ticker": out.ticker,
        "score": out.score,
        "confidence": out.confidence,
        "rationale": out.rationale,
    }


def _langgraph_available() -> bool:
    try:
        import langgraph  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


__all__ = ["Orchestrator", "OrchestratorResult", "DEFAULT_WEIGHTS"]
