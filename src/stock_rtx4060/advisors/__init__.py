"""LLM advisor layer for stock_rtx4060 (Phase 6).

The advisor layer never overrides the deterministic GREEN/AMBER/RED gates
emitted by :mod:`stock_rtx4060.recommendation_engine`.  It produces an
``advisory_score`` in ``[-1, +1]`` together with a ``confidence`` in
``[0, 1]`` per ticker.  Downstream consumers can:

* damp the deterministic score within a verdict bucket (the recommendation
  engine performs the blend), or
* feed the views into the Black-Litterman optimiser via
  :class:`stock_rtx4060.portfolio.views.LLMViews`.

The deterministic gate decisions are **never** overridden — the LLM may
only damp/downgrade.
"""

from __future__ import annotations

from .audit import check_completeness, log_advisor_call
from .base import Advisor, AdvisoryOutput
from .devils_advocate import DevilsAdvocateAgent
from .macro_regime import MacroRegimeAgent
from .news_sentiment import NewsSentimentAgent
from .orchestrator import Orchestrator

__all__ = [
    "Advisor",
    "AdvisoryOutput",
    "Orchestrator",
    "NewsSentimentAgent",
    "DevilsAdvocateAgent",
    "MacroRegimeAgent",
    "log_advisor_call",
    "check_completeness",
]
