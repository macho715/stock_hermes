"""AMH-Grounded Regime Memory — DuckDB backend.

Implements L1 (episodic), L2 (semantic pattern), and L3 (procedural)
memory tables.  All persistence is optional: when DuckDB is unavailable
or ADVISOR_MEMORY_ENABLED=false, the module degrades gracefully with
empty returns and no exceptions.

Design:
- session_id PRIMARY KEY → writes are idempotent (UPSERT)
- regime_label index → O(1) filter per query
- max_entries_per_regime → oldest rows removed on overflow
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

_ADVISOR_MEMORY_ENABLED: bool = (
    os.environ.get("ADVISOR_MEMORY_ENABLED", "false").lower() in ("1", "true", "yes")
)
_DEFAULT_DB_PATH: str = os.environ.get("ADVISOR_MEMORY_DB_PATH", ":memory:")
_MAX_ENTRIES: int = int(os.environ.get("ADVISOR_MEMORY_MAX_ENTRIES", "1000"))

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS regime_episodic (
    session_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    ts TIMESTAMP NOT NULL,
    regime_label TEXT NOT NULL DEFAULT '',
    final_score DOUBLE,
    reasoning_chains TEXT,   -- JSON blob
    logical_proposition TEXT DEFAULT '',
    outcome_pct DOUBLE,      -- NULL until updated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_episodic_regime_ticker
    ON regime_episodic(regime_label, ticker);

CREATE TABLE IF NOT EXISTS regime_semantic (
    id TEXT PRIMARY KEY,
    regime_label TEXT NOT NULL,
    pattern_summary TEXT NOT NULL,
    evidence_count INT DEFAULT 1,
    avg_outcome_pct DOUBLE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS advisor_procedures (
    advisor_name TEXT NOT NULL,
    regime_label TEXT NOT NULL,
    procedure_text TEXT NOT NULL,
    confidence DOUBLE DEFAULT 0.5,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (advisor_name, regime_label)
);
"""


@dataclass
class MemoryEntry:
    """L1 episodic memory record."""

    session_id: str
    ticker: str
    ts: str                         # ISO 8601
    regime_label: str
    final_score: float
    reasoning_chains: dict[str, str]   # {agent_name: rationale}
    logical_proposition: str
    outcome_pct: float | None          # None until forward return known
    layer: str = "L1"


class RegimeMemory:
    """Low-level DuckDB CRUD for regime-tagged memory.

    Parameters
    ----------
    db_path:
        Path for DuckDB file.  ``":memory:"`` for in-process volatile store.
    max_entries_per_regime:
        When exceeded, the oldest rows for that regime are removed.
    """

    def __init__(
        self,
        db_path: str = _DEFAULT_DB_PATH,
        *,
        max_entries_per_regime: int = _MAX_ENTRIES,
    ) -> None:
        self._db_path = db_path
        self._max_entries = max_entries_per_regime
        self._conn: Any = None
        self._init_db()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        try:
            import duckdb  # type: ignore[import-not-found]

            self._conn = duckdb.connect(self._db_path)
            self._conn.execute(_SCHEMA_SQL)
        except Exception as exc:
            logger.warning("[RegimeMemory] DuckDB init failed: %s — memory disabled", exc)
            self._conn = None

    @property
    def available(self) -> bool:
        return self._conn is not None

    # ------------------------------------------------------------------
    # L1 Episodic
    # ------------------------------------------------------------------

    def write_episodic(self, entry: MemoryEntry) -> None:
        """Upsert a single episodic memory record."""
        if not self.available:
            return
        try:
            chains_json = json.dumps(entry.reasoning_chains, ensure_ascii=False)
            self._conn.execute(
                """
                INSERT INTO regime_episodic
                    (session_id, ticker, ts, regime_label, final_score,
                     reasoning_chains, logical_proposition, outcome_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (session_id) DO UPDATE SET
                    final_score=excluded.final_score,
                    reasoning_chains=excluded.reasoning_chains,
                    logical_proposition=excluded.logical_proposition,
                    outcome_pct=COALESCE(excluded.outcome_pct, regime_episodic.outcome_pct)
                """,
                [
                    entry.session_id,
                    entry.ticker,
                    entry.ts,
                    entry.regime_label,
                    entry.final_score,
                    chains_json,
                    entry.logical_proposition,
                    entry.outcome_pct,
                ],
            )
            self._trim_episodic(entry.regime_label)
        except Exception as exc:
            logger.warning("[RegimeMemory] write_episodic failed: %s", exc)

    def query_episodic(
        self,
        regime: str,
        ticker: str | None = None,
        k: int = 5,
    ) -> list[MemoryEntry]:
        """Return up to *k* L1 records for *regime*, newest first."""
        if not self.available or not regime:
            return []
        try:
            if ticker:
                rows = self._conn.execute(
                    """
                    SELECT session_id, ticker, ts, regime_label, final_score,
                           reasoning_chains, logical_proposition, outcome_pct
                    FROM regime_episodic
                    WHERE regime_label = ? AND ticker = ?
                    ORDER BY ts DESC LIMIT ?
                    """,
                    [regime, ticker, k],
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT session_id, ticker, ts, regime_label, final_score,
                           reasoning_chains, logical_proposition, outcome_pct
                    FROM regime_episodic
                    WHERE regime_label = ?
                    ORDER BY ts DESC LIMIT ?
                    """,
                    [regime, k],
                ).fetchall()
            return [self._row_to_entry(r) for r in rows]
        except Exception as exc:
            logger.warning("[RegimeMemory] query_episodic failed: %s", exc)
            return []

    def update_outcome(self, session_id: str, realized_return_pct: float) -> bool:
        """Set outcome_pct for a completed session.  Returns True on success."""
        if not self.available:
            return False
        try:
            self._conn.execute(
                "UPDATE regime_episodic SET outcome_pct=? WHERE session_id=?",
                [float(realized_return_pct), session_id],
            )
            return True
        except Exception as exc:
            logger.warning("[RegimeMemory] update_outcome failed: %s", exc)
            return False

    def archive_stale(self, regime_shift_threshold_days: int = 90) -> int:
        """Delete episodic records older than *regime_shift_threshold_days* days.

        Returns the number of deleted rows.
        """
        if not self.available:
            return 0
        try:
            cutoff = f"CURRENT_TIMESTAMP - INTERVAL {int(regime_shift_threshold_days)} DAYS"
            result = self._conn.execute(
                f"DELETE FROM regime_episodic WHERE created_at < {cutoff}"
            )
            return int(result.rowcount) if result.rowcount is not None else 0
        except Exception as exc:
            logger.warning("[RegimeMemory] archive_stale failed: %s", exc)
            return 0

    # ------------------------------------------------------------------
    # L2 Semantic
    # ------------------------------------------------------------------

    def write_semantic(self, regime: str, pattern_summary: str, avg_outcome: float | None = None) -> None:
        if not self.available:
            return
        try:
            row_id = str(uuid.uuid4())
            self._conn.execute(
                """
                INSERT INTO regime_semantic (id, regime_label, pattern_summary, avg_outcome_pct)
                VALUES (?, ?, ?, ?)
                """,
                [row_id, regime, pattern_summary, avg_outcome],
            )
        except Exception as exc:
            logger.warning("[RegimeMemory] write_semantic failed: %s", exc)

    def query_semantic(self, regime: str, k: int = 3) -> list[str]:
        """Return up to *k* semantic pattern summaries for *regime*."""
        if not self.available or not regime:
            return []
        try:
            rows = self._conn.execute(
                """
                SELECT pattern_summary FROM regime_semantic
                WHERE regime_label = ?
                ORDER BY last_updated DESC LIMIT ?
                """,
                [regime, k],
            ).fetchall()
            return [r[0] for r in rows]
        except Exception as exc:
            logger.warning("[RegimeMemory] query_semantic failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # L3 Procedural
    # ------------------------------------------------------------------

    def get_procedure(self, advisor_name: str, regime: str) -> str:
        """Return the L3 procedure text for an advisor+regime pair, or ""."""
        if not self.available:
            return ""
        try:
            rows = self._conn.execute(
                "SELECT procedure_text FROM advisor_procedures WHERE advisor_name=? AND regime_label=?",
                [advisor_name, regime],
            ).fetchall()
            return str(rows[0][0]) if rows else ""
        except Exception as exc:
            logger.warning("[RegimeMemory] get_procedure failed: %s", exc)
            return ""

    def set_procedure(self, advisor_name: str, regime: str, procedure_text: str, confidence: float = 0.5) -> None:
        if not self.available:
            return
        try:
            self._conn.execute(
                """
                INSERT INTO advisor_procedures (advisor_name, regime_label, procedure_text, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (advisor_name, regime_label) DO UPDATE SET
                    procedure_text=excluded.procedure_text,
                    confidence=excluded.confidence
                """,
                [advisor_name, regime, procedure_text, float(confidence)],
            )
        except Exception as exc:
            logger.warning("[RegimeMemory] set_procedure failed: %s", exc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def count_by_regime(self) -> dict[str, int]:
        """Return episodic entry count per regime_label."""
        if not self.available:
            return {}
        try:
            rows = self._conn.execute(
                "SELECT regime_label, COUNT(*) FROM regime_episodic GROUP BY regime_label"
            ).fetchall()
            return {r[0]: int(r[1]) for r in rows}
        except Exception as exc:
            logger.warning("[RegimeMemory] count_by_regime failed: %s", exc)
            return {}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _trim_episodic(self, regime: str) -> None:
        """Remove oldest rows for *regime* when max_entries exceeded."""
        try:
            count_rows = self._conn.execute(
                "SELECT COUNT(*) FROM regime_episodic WHERE regime_label=?", [regime]
            ).fetchone()
            count = int(count_rows[0]) if count_rows else 0
            if count > self._max_entries:
                excess = count - self._max_entries
                self._conn.execute(
                    """
                    DELETE FROM regime_episodic
                    WHERE session_id IN (
                        SELECT session_id FROM regime_episodic
                        WHERE regime_label=?
                        ORDER BY ts ASC LIMIT ?
                    )
                    """,
                    [regime, excess],
                )
        except Exception as exc:
            logger.warning("[RegimeMemory] _trim_episodic failed: %s", exc)

    @staticmethod
    def _row_to_entry(row: tuple) -> MemoryEntry:
        session_id, ticker, ts, regime_label, final_score, chains_json, proposition, outcome = row
        try:
            chains = json.loads(chains_json) if chains_json else {}
        except (json.JSONDecodeError, TypeError):
            chains = {}
        return MemoryEntry(
            session_id=str(session_id),
            ticker=str(ticker),
            ts=str(ts),
            regime_label=str(regime_label),
            final_score=float(final_score) if final_score is not None else 0.0,
            reasoning_chains=chains,
            logical_proposition=str(proposition) if proposition else "",
            outcome_pct=float(outcome) if outcome is not None else None,
        )

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None


def new_session_id() -> str:
    """Generate a unique session ID for a single aanalyze() call."""
    return f"adv_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"


__all__ = ["RegimeMemory", "MemoryEntry", "new_session_id"]
