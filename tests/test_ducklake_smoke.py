"""DuckDB 1.5.3 + DuckLake 1.0 smoke tests (W2-B2).

Verifies:
  1. DuckDB version is >=1.5.3 (bumped in requirements.in)
  2. DUCKLAKE_ENABLED defaults to False
  3. DuckDBStore write/read round-trip still works after version bump
  4. PIT as_of guard holds with the upgraded DuckDB (INV-3 cross-check)
"""
from __future__ import annotations

import os

import pytest


# ---------------------------------------------------------------------------
# Test 1: DuckDB version ≥1.5.3
# ---------------------------------------------------------------------------


def test_duckdb_version_gte_1_5_3():
    """W2-B2: installed DuckDB must be >=1.5.3."""
    import importlib

    duckdb = importlib.import_module("duckdb")
    ver = tuple(int(x) for x in duckdb.__version__.split(".")[:3])
    assert ver >= (1, 5, 3), (
        f"DuckDB {duckdb.__version__} is too old — need >=1.5.3. "
        "Run: pip install 'duckdb>=1.5.3'"
    )


# ---------------------------------------------------------------------------
# Test 2: DUCKLAKE_ENABLED defaults to False
# ---------------------------------------------------------------------------


def test_ducklake_disabled_by_default(monkeypatch):
    """W2-B2: DUCKLAKE_ENABLED must default to False (no env var set)."""
    monkeypatch.delenv("DUCKLAKE_ENABLED", raising=False)
    # Re-import the module to pick up the monkeypatched env.
    import importlib
    import stock_rtx4060.data_lake as dl_mod

    importlib.reload(dl_mod)
    assert dl_mod.DUCKLAKE_ENABLED is False, (
        "DUCKLAKE_ENABLED should be False when env var is unset"
    )


def test_ducklake_enabled_by_env(monkeypatch):
    """W2-B2: DUCKLAKE_ENABLED becomes True when env var is set to 'true'."""
    monkeypatch.setenv("DUCKLAKE_ENABLED", "true")
    import importlib
    import stock_rtx4060.data_lake as dl_mod

    importlib.reload(dl_mod)
    assert dl_mod.DUCKLAKE_ENABLED is True
    monkeypatch.delenv("DUCKLAKE_ENABLED", raising=False)
    importlib.reload(dl_mod)  # reset for subsequent tests


# ---------------------------------------------------------------------------
# Test 3: DuckDBStore basic in-memory round-trip
# ---------------------------------------------------------------------------


def test_duckdb_store_write_read_roundtrip(tmp_path):
    """W2-B2: DuckDBStore write + read round-trip works with DuckDB 1.5.3."""
    import pandas as pd
    from stock_rtx4060.data_lake.store import DuckDBStore

    store = DuckDBStore(root=str(tmp_path / "lake"))
    idx = pd.to_datetime(["2025-01-02", "2025-01-03"], utc=True)
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0],
            "high": [105.0, 106.0],
            "low": [99.0, 100.0],
            "close": [103.0, 104.0],
            "volume": [1_000_000, 1_100_000],
        },
        index=idx,
    )
    rows_written = store.write("AAPL", df, source="test")
    assert rows_written == 2
    result = store.read("AAPL")
    assert result is not None and len(result) == 2


# ---------------------------------------------------------------------------
# Test 4: PIT guard invariant still holds after DuckDB upgrade
# ---------------------------------------------------------------------------


def test_pit_guard_holds_after_duckdb_upgrade():
    """W2-B2: as_of future date still raises RuntimeError with DuckDB 1.5.3."""
    from stock_rtx4060.data_providers import load_ohlcv_with_provider

    with pytest.raises(RuntimeError, match="lake miss|as_of"):
        load_ohlcv_with_provider(
            "AAPL",
            "1y",
            as_of="2099-01-01",
            data_lake_first=True,
        )
