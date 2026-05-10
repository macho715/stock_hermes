"""SQLite-backed OHLCV data cache.

Caches DataFrames keyed by (ticker, period, provider) with hourly TTL.
Cache is completely opt-out via USE_DATA_CACHE=0 environment variable.
This is a read-through cache only; no order routing or execution logic.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ohlcv_cache (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT    NOT NULL,
    period        TEXT    NOT NULL,
    provider      TEXT    NOT NULL,
    fetch_date    TEXT    NOT NULL,
    row_count     INTEGER NOT NULL,
    payload_json  TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(ticker, period, provider, fetch_date)
);
"""


class DataCache:
    """SQLite-backed OHLCV cache with TTL expiry and kill-switch support."""

    DEFAULT_TTL_HOURS: int = 20
    DEFAULT_DB_PATH: Path = Path.home() / ".stock_rtx4060_cache.db"

    def __init__(
        self,
        db_path: Path = DEFAULT_DB_PATH,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> None:
        self.db_path: Path = Path(db_path)
        self.ttl_hours: int = ttl_hours
        if self.is_enabled():
            self._init_db()

    # ------------------------------------------------------------------
    # Class-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def is_enabled() -> bool:
        """Return False if USE_DATA_CACHE env var is '0'."""
        return os.environ.get("USE_DATA_CACHE", "1") != "0"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create table and configure WAL journal mode."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(_CREATE_TABLE_SQL)

    def _fetch_key(self) -> str:
        """Return current UTC hour as string: '2026-05-07T08'."""
        return datetime.now(UTC).strftime("%Y-%m-%dT%H")

    def _is_expired(self, fetch_date: str) -> bool:
        """Return True if fetch_date is older than ttl_hours."""
        try:
            fetched_at = datetime.strptime(fetch_date, "%Y-%m-%dT%H").replace(
                tzinfo=UTC
            )
            cutoff = datetime.now(UTC) - timedelta(hours=self.ttl_hours)
            return fetched_at < cutoff
        except ValueError:
            # Unparseable date — treat as expired
            return True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, ticker: str, period: str, provider: str) -> pd.DataFrame | None:
        """Return cached DataFrame or None if miss/expired/disabled."""
        if not self.is_enabled():
            return None
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                row = conn.execute(
                    "SELECT fetch_date, payload_json FROM ohlcv_cache "
                    "WHERE ticker=? AND period=? AND provider=? "
                    "ORDER BY fetch_date DESC LIMIT 1",
                    (ticker, period, provider),
                ).fetchone()
            if row is None:
                return None
            fetch_date, payload_json = row
            if self._is_expired(fetch_date):
                logger.debug("EXPIRED ticker=%s period=%s", ticker, period)
                return None
            df = pd.DataFrame(json.loads(payload_json))
            has_date_column = any(str(col).lower() in {"date", "datetime", "timestamp"} for col in df.columns)
            if isinstance(df.index, pd.RangeIndex) and not has_date_column:
                logger.debug("LEGACY_MISS ticker=%s period=%s missing date column", ticker, period)
                return None
            logger.debug("HIT ticker=%s period=%s rows=%d", ticker, period, len(df))
            return df
        except Exception as exc:
            logger.warning("DataCache.get error: %s", exc)
            return None

    def set(
        self, ticker: str, period: str, provider: str, df: pd.DataFrame
    ) -> None:
        """Persist DataFrame. No-op if disabled or df is empty."""
        if not self.is_enabled():
            return
        if df is None or df.empty:
            return
        try:
            fetch_date = self._fetch_key()
            payload_df = df.copy()
            if isinstance(payload_df.index, pd.DatetimeIndex) and not any(
                str(col).lower() in {"date", "datetime", "timestamp"} for col in payload_df.columns
            ):
                payload_df = payload_df.reset_index()
                payload_df = payload_df.rename(columns={payload_df.columns[0]: "Date"})
            payload_json = payload_df.to_json(orient="records", date_format="iso")
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO ohlcv_cache "
                    "(ticker, period, provider, fetch_date, row_count, payload_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (ticker, period, provider, fetch_date, len(payload_df), payload_json),
                )
            logger.debug("SET ticker=%s period=%s rows=%d", ticker, period, len(payload_df))
        except Exception as exc:
            logger.warning("DataCache.set error: %s", exc)

    def invalidate(self, ticker: str) -> int:
        """Delete all rows for ticker. Returns deleted row count."""
        if not self.is_enabled():
            return 0
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "DELETE FROM ohlcv_cache WHERE ticker=?", (ticker,)
                )
                return cur.rowcount
        except Exception as exc:
            logger.warning("DataCache.invalidate error: %s", exc)
            return 0

    def purge_expired(self) -> int:
        """Delete all expired rows. Returns deleted row count."""
        if not self.is_enabled():
            return 0
        try:
            cutoff = (
                datetime.now(UTC) - timedelta(hours=self.ttl_hours)
            ).strftime("%Y-%m-%dT%H")
            with sqlite3.connect(str(self.db_path)) as conn:
                cur = conn.execute(
                    "DELETE FROM ohlcv_cache WHERE fetch_date < ?", (cutoff,)
                )
                return cur.rowcount
        except Exception as exc:
            logger.warning("DataCache.purge_expired error: %s", exc)
            return 0
