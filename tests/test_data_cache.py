"""Tests for DataCache (SQLite OHLCV cache).

All tests use tmp_path to avoid writing to ~/.stock_rtx4060_cache.db.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from stock_rtx4060.data_cache import DataCache

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_df() -> pd.DataFrame:
    """Return a minimal OHLCV DataFrame for testing."""
    return pd.DataFrame(
        {
            "date": ["2026-05-01", "2026-05-02"],
            "open": [100.0, 101.0],
            "close": [101.0, 102.0],
            "volume": [1_000_000, 900_000],
        }
    )


def make_cache(tmp_path, ttl_hours: int = DataCache.DEFAULT_TTL_HOURS) -> DataCache:
    """Construct a DataCache backed by a temp DB."""
    return DataCache(db_path=tmp_path / "test.db", ttl_hours=ttl_hours)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDataCache:

    def test_cache_miss_returns_none(self, tmp_path):
        """get() on an empty cache returns None."""
        cache = make_cache(tmp_path)
        result = cache.get("AAPL", "3y", "yfinance")
        assert result is None

    def test_cache_set_and_get_hit(self, tmp_path):
        """set() then get() returns an equivalent DataFrame."""
        cache = make_cache(tmp_path)
        df = make_df()
        cache.set("AAPL", "3y", "yfinance", df)
        result = cache.get("AAPL", "3y", "yfinance")
        assert result is not None
        assert list(result.columns) == list(df.columns)
        assert len(result) == len(df)

    def test_cache_expired_returns_none(self, tmp_path):
        """With ttl_hours=0 every entry is immediately expired."""
        cache = make_cache(tmp_path, ttl_hours=0)
        df = make_df()
        cache.set("NVDA", "1y", "yfinance", df)
        result = cache.get("NVDA", "1y", "yfinance")
        assert result is None

    def test_cache_ttl_not_expired_returns_df(self, tmp_path):
        """With a generous TTL a freshly-inserted entry is returned."""
        cache = make_cache(tmp_path, ttl_hours=48)
        df = make_df()
        cache.set("MSFT", "2y", "yfinance", df)
        result = cache.get("MSFT", "2y", "yfinance")
        assert result is not None
        assert len(result) == len(df)

    def test_cache_kill_switch_skips_read(self, tmp_path, monkeypatch):
        """get() returns None when USE_DATA_CACHE=0, even if data exists."""
        # Seed data with cache enabled
        cache_on = make_cache(tmp_path)
        cache_on.set("AAPL", "3y", "yfinance", make_df())

        # Now disable cache and create a new instance pointed at the same DB
        monkeypatch.setenv("USE_DATA_CACHE", "0")
        cache_off = DataCache(db_path=tmp_path / "test.db")
        result = cache_off.get("AAPL", "3y", "yfinance")
        assert result is None

    def test_cache_kill_switch_skips_write(self, tmp_path, monkeypatch):
        """set() is a no-op when USE_DATA_CACHE=0."""
        monkeypatch.setenv("USE_DATA_CACHE", "0")
        cache = DataCache(db_path=tmp_path / "test.db")
        # set() should not raise and DB file should not be created
        cache.set("TSLA", "1y", "yfinance", make_df())

        # Re-enable and verify nothing was stored
        monkeypatch.setenv("USE_DATA_CACHE", "1")
        cache_on = make_cache(tmp_path)
        result = cache_on.get("TSLA", "1y", "yfinance")
        assert result is None

    def test_cache_invalidate_ticker(self, tmp_path):
        """invalidate() removes all rows for the given ticker."""
        cache = make_cache(tmp_path)
        df = make_df()
        cache.set("AAPL", "3y", "yfinance", df)
        cache.set("AAPL", "1y", "yfinance", df)  # second entry
        deleted = cache.invalidate("AAPL")
        assert deleted >= 1
        assert cache.get("AAPL", "3y", "yfinance") is None
        assert cache.get("AAPL", "1y", "yfinance") is None

    def test_cache_purge_expired(self, tmp_path):
        """purge_expired() removes stale rows and leaves fresh ones alone."""
        from stock_rtx4060.data_cache import DataCache

        db_file = tmp_path / "test.db"
        # Initialise the DB schema via a normal cache instance
        cache = DataCache(db_path=db_file, ttl_hours=48)

        # Manually insert a row with an old fetch_date (72 hours ago)
        old_fetch = "2020-01-01T00"  # clearly in the past
        df = make_df()
        payload = df.to_json(orient="records", date_format="iso")
        with __import__("sqlite3").connect(str(db_file)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ohlcv_cache "
                "(ticker, period, provider, fetch_date, row_count, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("OLD", "1y", "yfinance", old_fetch, len(df), payload),
            )

        # Insert a fresh row via the normal API (fetch_date = current UTC hour)
        cache.set("NEW", "1y", "yfinance", df)

        # purge with 24-hour TTL removes the 2020 row but not the current one
        purge_cache = DataCache(db_path=db_file, ttl_hours=24)
        deleted = purge_cache.purge_expired()
        assert deleted >= 1

        # The freshly-inserted entry must still be retrievable
        result = cache.get("NEW", "1y", "yfinance")
        assert result is not None

    def test_cache_wal_mode_enabled(self, tmp_path):
        """_init_db() sets SQLite journal_mode to WAL."""
        db_file = tmp_path / "test.db"
        # Instantiate so _init_db() runs
        DataCache(db_path=db_file)
        with sqlite3.connect(str(db_file)) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"

    def test_cache_empty_df_not_stored(self, tmp_path):
        """set() with an empty DataFrame is a no-op; get() returns None."""
        cache = make_cache(tmp_path)
        cache.set("AMZN", "1y", "yfinance", pd.DataFrame())
        result = cache.get("AMZN", "1y", "yfinance")
        assert result is None

    def test_cache_insert_or_replace_same_key(self, tmp_path):
        """Second set() for the same (ticker, period, provider, fetch_date)
        replaces the existing row rather than raising a UNIQUE error."""
        cache = make_cache(tmp_path)
        df1 = make_df()
        df2 = pd.DataFrame(
            {
                "date": ["2026-05-03", "2026-05-04", "2026-05-05"],
                "open": [110.0, 111.0, 112.0],
                "close": [111.0, 112.0, 113.0],
                "volume": [500_000, 600_000, 700_000],
            }
        )
        cache.set("GOOG", "3y", "yfinance", df1)
        # Replace with df2 — should not raise
        cache.set("GOOG", "3y", "yfinance", df2)
        result = cache.get("GOOG", "3y", "yfinance")
        assert result is not None
        # The replaced payload has 3 rows
        assert len(result) == 3

    def test_cache_preserves_datetime_index_as_date_column(self, tmp_path):
        """Datetime-indexed OHLCV keeps a date column for dashboard APIs."""
        cache = make_cache(tmp_path)
        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [101.0, 102.0],
                "Low": [99.0, 100.0],
                "Close": [100.5, 101.5],
                "Volume": [1000, 2000],
            },
            index=pd.to_datetime(["2026-05-01", "2026-05-04"]),
        )

        cache.set("AAPL", "6mo", "yfinance", df)
        result = cache.get("AAPL", "6mo", "yfinance")

        assert result is not None
        assert "Date" in result.columns
        assert str(result.loc[0, "Date"]).startswith("2026-05-01")

    def test_cache_treats_legacy_payload_without_date_as_miss(self, tmp_path):
        """Old OHLCV cache rows without dates cannot support dashboard freshness."""
        cache = make_cache(tmp_path)
        db_file = tmp_path / "test.db"
        legacy = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [101.0],
                "Low": [99.0],
                "Close": [100.5],
                "Volume": [1000],
            }
        )
        with sqlite3.connect(str(db_file)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ohlcv_cache "
                "(ticker, period, provider, fetch_date, row_count, payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("005930.KS", "6mo", "yfinance", cache._fetch_key(), len(legacy), legacy.to_json(orient="records")),
            )

        assert cache.get("005930.KS", "6mo", "yfinance") is None

    def test_cache_multiple_tickers_independent(self, tmp_path):
        """Different tickers stored in the same DB do not interfere."""
        cache = make_cache(tmp_path)
        df_a = make_df()
        df_b = pd.DataFrame(
            {
                "date": ["2026-04-01"],
                "open": [200.0],
                "close": [201.0],
                "volume": [2_000_000],
            }
        )
        cache.set("AAPL", "3y", "yfinance", df_a)
        cache.set("NVDA", "3y", "yfinance", df_b)

        result_a = cache.get("AAPL", "3y", "yfinance")
        result_b = cache.get("NVDA", "3y", "yfinance")

        assert result_a is not None and len(result_a) == 2
        assert result_b is not None and len(result_b) == 1

        # Invalidate AAPL; NVDA must remain
        cache.invalidate("AAPL")
        assert cache.get("AAPL", "3y", "yfinance") is None
        assert cache.get("NVDA", "3y", "yfinance") is not None
