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
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .base import Advisor, AdvisoryOutput
from .devils_advocate import DevilsAdvocateAgent
from .macro_regime import MacroRegimeAgent
from .news_sentiment import NewsSentimentAgent
from .thompson_weights import ThompsonWeights

# [NotebookLM bridge] feature-flagged via NOTEBOOKLM_NEWS_MODE env var
try:
    from .notebooklm_news import enrich_context_with_notebooklm as _nb_enrich
    _NOTEBOOKLM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dep
    _NOTEBOOKLM_AVAILABLE = False
    def _nb_enrich(ticker: str, ctx: dict) -> dict: return ctx  # type: ignore[misc]

if TYPE_CHECKING:
    from .memory.memory_layer import MemoryLayer

logger = logging.getLogger(__name__)


DEFAULT_WEIGHTS: dict[str, float] = {
    "news_sentiment": 0.40,
    "devils_advocate": 0.30,
    "macro_regime": 0.30,
}

_ADVISOR_NAMES = ["news_sentiment", "devils_advocate", "macro_regime"]

_WEIGHTS_MODE = os.getenv("ADVISOR_WEIGHTS_MODE", "mab").lower()


@dataclass
class OrchestratorResult:
    advisory_score: float
    confidence: float
    outputs: list[AdvisoryOutput]
    debate_result: Any | None = None
    memory_context_used: bool = False   # [AMH Memory — W4] True when ≥1 memory was injected
    session_id: str = ""                # [AMH Memory — W4] session ID for outcome updates


@dataclass
class Orchestrator:
    news: Advisor = field(default_factory=NewsSentimentAgent)
    devils: Advisor = field(default_factory=DevilsAdvocateAgent)
    macro: Advisor = field(default_factory=MacroRegimeAgent)
    weights: dict[str, float] | object = field(
        default_factory=lambda: ThompsonWeights(_ADVISOR_NAMES)
    )
    use_langgraph: bool = False
    use_debate: bool = False
    memory_layer: MemoryLayer | None = field(default=None)  # [AMH Memory — W4 FR-6]

    async def aanalyze(self, ticker: str, context: dict[str, Any] | None = None) -> OrchestratorResult:
        ctx = dict(context or {})
        session_id = ""
        memory_used = False

        # [NotebookLM bridge] Enrich context with NotebookLM stock news (feature-flagged)
        if _NOTEBOOKLM_AVAILABLE:
            ctx = _nb_enrich(ticker, ctx)
            if ctx.get("notebooklm_enriched"):
                logger.debug("[NotebookLM] enriched %s with %d headlines",
                             ticker, ctx.get("notebooklm_count", 0))

        if self.use_langgraph and _langgraph_available():
            outputs = await self._langgraph_run(ticker, ctx)
        else:
            outputs = await self._fallback_run(ticker, ctx)

        score, confidence = self._blend(outputs)
        debate_result: Any | None = None

        if self._debate_enabled():
            from .debate.bull_bear_debate import BullBearDebate

            debate_client = getattr(self.news, "client", None)
            debate = BullBearDebate(client=debate_client)
            debate_result = await debate.run(ticker, outputs, ctx)
            if debate_result.consensus_confidence > confidence:
                score = float(debate_result.consensus_score)
                confidence = float(debate_result.consensus_confidence)

        # [AMH Memory — W4] post-analyze memory write
        if self.memory_layer is not None:
            from .memory.memory_layer import MemoryLayer

            session_id = MemoryLayer.new_session_id()
            regime = _extract_regime(outputs)
            self.memory_layer.write(session_id, ticker, regime, outputs, score)

        return OrchestratorResult(
            advisory_score=score,
            confidence=confidence,
            outputs=outputs,
            debate_result=debate_result,
            memory_context_used=memory_used,
            session_id=session_id,
        )

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

        # [AMH Memory — W4] inject regime memories + CWRM routing into devils context
        if self.memory_layer is not None:
            regime = str(macro_out.regime_label) or "unknown"
            memory_result = self.memory_layer.get_relevant_memories(ticker, regime)
            routing = self.memory_layer.route(
                news_out.score, news_out.confidence,
                macro_out.score, macro_out.confidence,
            )
            proposition = self.memory_layer.extract_proposition(news_out.rationale)
            devils_ctx["memory_context"] = memory_result.as_context_dict()
            devils_ctx["routing_path"] = routing.path
            devils_ctx["news_proposition"] = proposition
            logger.info(
                "[MemoryLayer] regime=%s retrieved=%d path=%s",
                regime, memory_result.total_retrieved, routing.path,
            )

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

    def _ensure_weights(self) -> dict[str, float]:
        """Return current weights dict, sampling ThompsonWeights once per call."""
        w = self.weights
        if hasattr(w, "sample"):
            return w.sample()
        if isinstance(w, dict):
            return dict(w)
        return dict(DEFAULT_WEIGHTS)

    def _blend(self, outputs: list[AdvisoryOutput]) -> tuple[float, float]:
        weights = self._ensure_weights()
        weighted_score = 0.0
        weighted_conf = 0.0
        total_weight = 0.0
        total_conf_weight = 0.0
        for out in outputs:
            w = float(weights.get(out.agent, 0.0))
            if w <= 0.0:
                continue
            weighted_score += out.score * out.confidence * w
            total_weight += out.confidence * w
            weighted_conf += out.confidence * w
            total_conf_weight += w
        score = weighted_score / total_weight if total_weight > 0 else 0.0
        confidence = weighted_conf / total_conf_weight if total_conf_weight > 0 else 0.0
        score = max(-1.0, min(1.0, score))
        confidence = max(0.0, min(1.0, confidence))
        return float(score), float(confidence)

    def update_advisor_reward(self, advisor_id: str, reward: float) -> None:
        """Record a reward outcome for the given advisor (ThompsonWeights MAB update).

        Call this after measuring the advisor's output against actual outcome.
        No-op when ADVISOR_WEIGHTS_MODE=fixed.
        """
        w = self.weights
        if hasattr(w, "update"):
            w.update(advisor_id, reward)

    def _debate_enabled(self) -> bool:
        if self.use_debate:
            return True
        return os.environ.get("DEBATE_ENABLED", "false").lower() in ("1", "true", "yes")


def _to_dict(out: AdvisoryOutput) -> dict[str, Any]:
    return {
        "agent": out.agent,
        "ticker": out.ticker,
        "score": out.score,
        "confidence": out.confidence,
        "rationale": out.rationale,
    }


def _extract_regime(outputs: list[AdvisoryOutput]) -> str:
    """Return the regime_label from the macro_regime advisor output, if any."""
    for out in outputs:
        if out.agent == "macro_regime" and out.regime_label:
            return out.regime_label
    return "unknown"


def _langgraph_available() -> bool:
    try:
        import langgraph  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False
    return True


__all__ = ["Orchestrator", "OrchestratorResult", "DEFAULT_WEIGHTS", "_extract_regime"]
