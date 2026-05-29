"""Hierarchical Memory Store — L1 / L2 / L3 retrieval coordination.

Retrieval order (per FinThink R-Mem / LangMem 3-tier design):
  1. L1 episodic (most recent, regime + ticker matched)
  2. L2 semantic patterns (cross-episode distillations for the regime)
  3. L3 procedural (advisor-level guidelines, slowest to change)

The store never raises; every method returns empty on failure.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .regime_memory import MemoryEntry, RegimeMemory

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Combined result from all three tiers."""

    l1_entries: list[MemoryEntry]         # episodic — highest recency
    l2_patterns: list[str]                # semantic pattern summaries
    l3_procedure: str                     # advisor procedure text
    total_retrieved: int = 0

    def as_context_dict(self) -> dict:
        """Flatten into a dict suitable for injection into advisor context."""
        return {
            "episodic_memories": [
                {
                    "session_id": e.session_id,
                    "ticker": e.ticker,
                    "ts": e.ts,
                    "regime": e.regime_label,
                    "score": e.final_score,
                    "rationale_summary": e.reasoning_chains,
                    "proposition": e.logical_proposition,
                    "outcome_pct": e.outcome_pct,
                }
                for e in self.l1_entries
            ],
            "semantic_patterns": self.l2_patterns,
            "procedure": self.l3_procedure,
        }


class HierarchicalStore:
    """Coordinates L1/L2/L3 retrieval over a single :class:`RegimeMemory`."""

    def __init__(
        self,
        memory: RegimeMemory,
        *,
        l1_k: int = 5,
        l2_k: int = 3,
    ) -> None:
        self._mem = memory
        self._l1_k = l1_k
        self._l2_k = l2_k

    def retrieve(
        self,
        ticker: str,
        regime: str,
        advisor_name: str = "",
        *,
        k: int | None = None,
    ) -> RetrievalResult:
        """Return a combined retrieval result for *ticker* + *regime*.

        Parameters
        ----------
        ticker:
            Asset being analysed.
        regime:
            Current market regime label (``"risk_on"`` / ``"neutral"`` / ``"risk_off"``).
        advisor_name:
            If provided, also fetches the L3 procedure for this advisor.
        k:
            Override L1 result count.
        """
        if not self._mem.available or not regime:
            return RetrievalResult(l1_entries=[], l2_patterns=[], l3_procedure="")

        l1 = self._mem.query_episodic(regime, ticker=ticker, k=k or self._l1_k)
        l2 = self._mem.query_semantic(regime, k=self._l2_k)
        l3 = self._mem.get_procedure(advisor_name, regime) if advisor_name else ""

        total = len(l1) + len(l2) + (1 if l3 else 0)
        return RetrievalResult(l1_entries=l1, l2_patterns=l2, l3_procedure=l3, total_retrieved=total)

    def retrieve_cross_asset(
        self,
        regime: str,
        exclude_ticker: str = "",
        k: int = 3,
    ) -> list[MemoryEntry]:
        """Return L1 entries for *regime* from *other* tickers (cross-asset)."""
        if not self._mem.available or not regime:
            return []
        all_entries = self._mem.query_episodic(regime, ticker=None, k=k * 5)
        cross = [e for e in all_entries if e.ticker != exclude_ticker]
        return cross[:k]


__all__ = ["HierarchicalStore", "RetrievalResult"]
