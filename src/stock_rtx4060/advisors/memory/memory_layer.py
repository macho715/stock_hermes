"""MemoryLayer — public API for the AMH-Grounded Hierarchical Memory system.

This is the only import callers outside the ``memory/`` sub-package should
need.  It wires together:

* :class:`RegimeMemory` — DuckDB L1/L2/L3 storage
* :class:`HierarchicalStore` — unified retrieval
* :class:`CWRMRouter` — disagreement-based routing
* :class:`STLProtocol` — proposition extraction

Feature flag
------------
Set ``ADVISOR_MEMORY_ENABLED=true`` to activate.  When false (default),
every method is a no-op that returns safe defaults.

MLflow
------
Call :meth:`log_to_mlflow` (optional) after a run to push regime counts,
hit rate, and CWRM deep path rate.
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from .cwrm_router import CWRMRouter, RoutingDecision
from .hierarchical_store import HierarchicalStore, RetrievalResult
from .regime_memory import MemoryEntry, RegimeMemory, new_session_id
from .stl_protocol import STLProtocol

logger = logging.getLogger(__name__)

_ENABLED: bool = os.environ.get("ADVISOR_MEMORY_ENABLED", "false").lower() in ("1", "true", "yes")
_DB_PATH: str = os.environ.get("ADVISOR_MEMORY_DB_PATH", ":memory:")


@dataclass
class MemoryStats:
    enabled: bool
    regime_counts: dict[str, int]
    total_entries: int
    retrieval_hit_rate: float   # fraction of calls that returned ≥1 memory
    cwrm_deep_rate: float       # fraction of route() calls that chose "deep"


class MemoryLayer:
    """Public interface for the AMH memory system.

    Parameters
    ----------
    db_path:
        DuckDB database path.  ``":memory:"`` for in-process volatile store.
    enabled:
        Override ``ADVISOR_MEMORY_ENABLED`` env var.
    """

    def __init__(
        self,
        db_path: str = _DB_PATH,
        *,
        enabled: bool = _ENABLED,
    ) -> None:
        self._enabled = enabled
        self._db: RegimeMemory | None = None
        self._store: HierarchicalStore | None = None
        self._router = CWRMRouter()
        self._stl = STLProtocol()
        # telemetry counters
        self._total_reads: int = 0
        self._reads_with_results: int = 0
        self._total_routes: int = 0
        self._deep_routes: int = 0

        if self._enabled:
            try:
                self._db = RegimeMemory(db_path=db_path)
                self._store = HierarchicalStore(self._db)
            except Exception as exc:
                logger.warning("[MemoryLayer] init failed: %s — memory disabled", exc)
                self._db = None
                self._store = None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get_relevant_memories(
        self,
        ticker: str,
        regime: str,
        k: int = 5,
        advisor_name: str = "",
    ) -> RetrievalResult:
        """Retrieve up to *k* L1 entries + L2 patterns + L3 procedure.

        Returns an empty :class:`RetrievalResult` when memory is disabled
        or unavailable — callers need not branch on ``enabled``.
        """
        if not self._enabled or self._store is None:
            return RetrievalResult(l1_entries=[], l2_patterns=[], l3_procedure="")

        t0 = time.monotonic()
        try:
            result = self._store.retrieve(ticker, regime, advisor_name=advisor_name, k=k)
            elapsed_ms = (time.monotonic() - t0) * 1000
            self._total_reads += 1
            if result.total_retrieved > 0:
                self._reads_with_results += 1
            logger.info(
                "[MemoryLayer] regime=%s ticker=%s retrieved=%d elapsed_ms=%.0f",
                regime, ticker, result.total_retrieved, elapsed_ms,
            )
            return result
        except Exception as exc:
            logger.warning("[MemoryLayer] get_relevant_memories failed: %s", exc)
            return RetrievalResult(l1_entries=[], l2_patterns=[], l3_procedure="")

    def route(
        self,
        news_score: float,
        news_conf: float,
        macro_score: float,
        macro_conf: float,
    ) -> RoutingDecision:
        """Determine shallow/deep routing via CWRM.  Always returns a decision."""
        decision = self._router.route(news_score, news_conf, macro_score, macro_conf)
        self._total_routes += 1
        if decision.path == "deep":
            self._deep_routes += 1
        return decision

    def extract_proposition(self, rationale: str) -> str:
        """Extract an STL logical proposition from a news rationale string."""
        return self._stl.extract(rationale)

    def write(
        self,
        session_id: str,
        ticker: str,
        regime: str,
        outputs: list[Any],    # list[AdvisoryOutput]
        final_score: float,
    ) -> None:
        """Persist one aanalyze() result as an L1 episodic memory.

        Fails silently — aanalyze() result is never affected by memory errors.
        """
        if not self._enabled or self._db is None:
            return
        try:
            from datetime import UTC, datetime

            chains: dict[str, str] = {}
            proposition = ""
            for out in outputs:
                agent = getattr(out, "agent", "unknown")
                chains[agent] = str(getattr(out, "rationale", ""))[:512]
                if agent == "news_sentiment":
                    raw_prop = getattr(out, "logical_proposition", "")
                    if not raw_prop:
                        raw_prop = self._stl.extract(chains[agent])
                    proposition = raw_prop

            entry = MemoryEntry(
                session_id=session_id,
                ticker=ticker,
                ts=datetime.now(UTC).isoformat(timespec="seconds"),
                regime_label=regime,
                final_score=float(final_score),
                reasoning_chains=chains,
                logical_proposition=proposition,
                outcome_pct=None,
            )
            self._db.write_episodic(entry)
            logger.debug(
                "[MemoryLayer] write session_id=%s ticker=%s regime=%s score=%.3f",
                session_id, ticker, regime, final_score,
            )
        except Exception as exc:
            logger.warning("[MemoryLayer] write failed: %s", exc)

    def update_outcome(self, session_id: str, realized_return_pct: float) -> bool:
        """Update forward return for a completed session."""
        if not self._enabled or self._db is None:
            return False
        return self._db.update_outcome(session_id, realized_return_pct)

    def get_procedure(self, advisor_name: str, regime: str) -> str:
        """Return L3 procedure text for an advisor+regime pair, or ""."""
        if not self._enabled or self._db is None:
            return ""
        return self._db.get_procedure(advisor_name, regime)

    def archive_stale(self, regime_shift_threshold_days: int = 90) -> int:
        """Delete entries older than *regime_shift_threshold_days* days."""
        if not self._enabled or self._db is None:
            return 0
        return self._db.archive_stale(regime_shift_threshold_days)

    # ------------------------------------------------------------------
    # Stats & MLflow
    # ------------------------------------------------------------------

    def stats(self) -> MemoryStats:
        counts = self._db.count_by_regime() if (self._enabled and self._db) else {}
        hit_rate = (self._reads_with_results / self._total_reads) if self._total_reads else 0.0
        deep_rate = (self._deep_routes / self._total_routes) if self._total_routes else 0.0
        return MemoryStats(
            enabled=self._enabled,
            regime_counts=counts,
            total_entries=sum(counts.values()),
            retrieval_hit_rate=round(hit_rate, 4),
            cwrm_deep_rate=round(deep_rate, 4),
        )

    def log_to_mlflow(self) -> None:
        """Push regime memory metrics to MLflow (optional).  Silent on failure."""
        try:
            import mlflow  # type: ignore[import-not-found]

            s = self.stats()
            metrics: dict[str, float] = {
                "memory_total_entries": float(s.total_entries),
                "memory_retrieval_hit_rate": s.retrieval_hit_rate,
                "cwrm_deep_path_rate": s.cwrm_deep_rate,
            }
            for regime, cnt in s.regime_counts.items():
                key = f"memory_l1_entries_{regime.replace(' ', '_')}"
                metrics[key] = float(cnt)
            mlflow.log_metrics(metrics)
        except Exception as exc:
            logger.debug("[MemoryLayer] log_to_mlflow skipped: %s", exc)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @classmethod
    def new_session_id(cls) -> str:
        return new_session_id()


__all__ = ["MemoryLayer", "MemoryStats"]
