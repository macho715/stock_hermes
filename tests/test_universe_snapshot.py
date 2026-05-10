"""Tests for data_lake/universe/snapshot.py — covers uncovered lines.

Missing lines targeted:
  16->18, 34, 40, 47-61, 70-81
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _path — str as_of gets converted to date (line 16->18)
# ---------------------------------------------------------------------------

def test_path_string_as_of_is_converted(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import _path

    p = _path("KOSPI200", "2024-06-30")
    assert p.name == "KOSPI200_2024-06-30.parquet"


def test_path_date_as_of(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import _path

    p = _path("SP500", date(2024, 12, 31))
    assert p.name == "SP500_2024-12-31.parquet"


# ---------------------------------------------------------------------------
# load_snapshot — file not found returns [] (line 34)
# ---------------------------------------------------------------------------

def test_load_snapshot_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import load_snapshot

    result = load_snapshot("KOSPI200", "2024-01-01")
    assert result == []


# ---------------------------------------------------------------------------
# list_snapshots — UNIVERSE_ROOT does not exist (line 40)
# ---------------------------------------------------------------------------

def test_list_snapshots_missing_root_returns_empty(tmp_path, monkeypatch):
    non_existent = tmp_path / "missing_root"
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", non_existent)
    from stock_rtx4060.data_lake.universe.snapshot import list_snapshots

    result = list_snapshots()
    assert result == []


# ---------------------------------------------------------------------------
# list_snapshots — filter by universe (line 40-42)
# ---------------------------------------------------------------------------

def test_list_snapshots_filtered_by_universe(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import list_snapshots, write_snapshot

    write_snapshot("KOSPI200", "2024-01-15", ["005930", "000660"])
    write_snapshot("SP500", "2024-01-15", ["AAPL", "MSFT"])

    kospi_files = list_snapshots("KOSPI200")
    assert all("KOSPI200" in str(f) for f in kospi_files)
    assert len(kospi_files) == 1


def test_list_snapshots_all_universes(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import list_snapshots, write_snapshot

    write_snapshot("KOSPI200", "2024-02-01", ["A", "B"])
    write_snapshot("SP500", "2024-02-01", ["C", "D"])

    all_files = list_snapshots()
    assert len(all_files) >= 2


# ---------------------------------------------------------------------------
# snapshot_kospi200 — pykrx import error returns [] (lines 47-50)
# ---------------------------------------------------------------------------

def test_snapshot_kospi200_import_error_returns_empty(tmp_path, monkeypatch):
    """When pykrx is not available, snapshot_kospi200 returns []."""
    import sys
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    # Remove pykrx from sys.modules so the 'from pykrx import stock' inside the fn fails
    pykrx_backup = sys.modules.pop("pykrx", None)
    pykrx_stock_backup = sys.modules.pop("pykrx.stock", None)
    # Ensure the import raises ImportError by inserting None
    sys.modules["pykrx"] = None  # type: ignore[assignment]
    try:
        import importlib
        import stock_rtx4060.data_lake.universe.snapshot as snap_mod
        importlib.reload(snap_mod)
        snap_mod.UNIVERSE_ROOT = tmp_path
        result = snap_mod.snapshot_kospi200("2024-01-15")
        assert result == []
    finally:
        # Restore original state
        sys.modules.pop("pykrx", None)
        if pykrx_backup is not None:
            sys.modules["pykrx"] = pykrx_backup
        if pykrx_stock_backup is not None:
            sys.modules["pykrx.stock"] = pykrx_stock_backup
        importlib.reload(snap_mod)


# ---------------------------------------------------------------------------
# snapshot_kospi200 — pykrx raises exception during API call (lines 55-58)
# ---------------------------------------------------------------------------

def test_snapshot_kospi200_api_exception_returns_empty(tmp_path, monkeypatch):
    """When pykrx API call raises, snapshot_kospi200 returns []."""
    import sys
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)

    mock_stock = MagicMock()
    mock_stock.get_index_portfolio_deposit_file.side_effect = Exception("network down")

    mock_pykrx = MagicMock()
    mock_pykrx.stock = mock_stock

    pykrx_backup = sys.modules.get("pykrx")
    pykrx_stock_backup = sys.modules.get("pykrx.stock")
    sys.modules["pykrx"] = mock_pykrx
    sys.modules["pykrx.stock"] = mock_stock

    try:
        import importlib
        import stock_rtx4060.data_lake.universe.snapshot as snap_mod
        importlib.reload(snap_mod)
        snap_mod.UNIVERSE_ROOT = tmp_path

        result = snap_mod.snapshot_kospi200("2024-01-15")
        assert result == []
    finally:
        if pykrx_backup is not None:
            sys.modules["pykrx"] = pykrx_backup
        else:
            sys.modules.pop("pykrx", None)
        if pykrx_stock_backup is not None:
            sys.modules["pykrx.stock"] = pykrx_stock_backup
        else:
            sys.modules.pop("pykrx.stock", None)
        importlib.reload(snap_mod)


# ---------------------------------------------------------------------------
# snapshot_kospi200 — members found, write_snapshot called (lines 59-60)
# ---------------------------------------------------------------------------

def test_snapshot_kospi200_writes_when_members_found(tmp_path, monkeypatch):
    """When pykrx returns members, write_snapshot is called and persisted."""
    import sys
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)

    mock_stock = MagicMock()
    mock_stock.get_index_portfolio_deposit_file.return_value = ["005930", "000660", "035720"]

    mock_pykrx = MagicMock()
    mock_pykrx.stock = mock_stock

    pykrx_backup = sys.modules.get("pykrx")
    pykrx_stock_backup = sys.modules.get("pykrx.stock")
    sys.modules["pykrx"] = mock_pykrx
    sys.modules["pykrx.stock"] = mock_stock

    try:
        import importlib
        import stock_rtx4060.data_lake.universe.snapshot as snap_mod
        importlib.reload(snap_mod)
        snap_mod.UNIVERSE_ROOT = tmp_path

        members = snap_mod.snapshot_kospi200("2024-06-30")
        assert len(members) == 3
        files = list(tmp_path.glob("KOSPI200*.parquet"))
        assert len(files) == 1
    finally:
        if pykrx_backup is not None:
            sys.modules["pykrx"] = pykrx_backup
        else:
            sys.modules.pop("pykrx", None)
        if pykrx_stock_backup is not None:
            sys.modules["pykrx.stock"] = pykrx_stock_backup
        else:
            sys.modules.pop("pykrx.stock", None)
        importlib.reload(snap_mod)


# ---------------------------------------------------------------------------
# snapshot_kospi200 — string as_of gets parsed (line 53)
# ---------------------------------------------------------------------------

def test_snapshot_kospi200_string_date_parsed(tmp_path, monkeypatch):
    """String as_of is converted to date and formatted as yyyymmdd for pykrx."""
    import sys
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)

    mock_stock = MagicMock()
    mock_stock.get_index_portfolio_deposit_file.return_value = ["005930"]

    mock_pykrx = MagicMock()
    mock_pykrx.stock = mock_stock

    pykrx_backup = sys.modules.get("pykrx")
    pykrx_stock_backup = sys.modules.get("pykrx.stock")
    sys.modules["pykrx"] = mock_pykrx
    sys.modules["pykrx.stock"] = mock_stock

    try:
        import importlib
        import stock_rtx4060.data_lake.universe.snapshot as snap_mod
        importlib.reload(snap_mod)
        snap_mod.UNIVERSE_ROOT = tmp_path

        members = snap_mod.snapshot_kospi200("2024-03-15")
        assert members == ["005930"]
        call_args = mock_stock.get_index_portfolio_deposit_file.call_args[0]
        assert call_args[1] == "20240315"
    finally:
        if pykrx_backup is not None:
            sys.modules["pykrx"] = pykrx_backup
        else:
            sys.modules.pop("pykrx", None)
        if pykrx_stock_backup is not None:
            sys.modules["pykrx.stock"] = pykrx_stock_backup
        else:
            sys.modules.pop("pykrx.stock", None)
        importlib.reload(snap_mod)


# ---------------------------------------------------------------------------
# snapshot_sp500 — read_html raises exception returns [] (lines 70-80)
# ---------------------------------------------------------------------------

def test_snapshot_sp500_http_exception_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import snapshot_sp500

    with patch("pandas.read_html", side_effect=Exception("HTTP error")):
        result = snapshot_sp500("2024-01-15")
    assert result == []


# ---------------------------------------------------------------------------
# snapshot_sp500 — members found, persist + return (lines 79-81)
# ---------------------------------------------------------------------------

def test_snapshot_sp500_writes_when_members_found(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import snapshot_sp500

    import pandas as pd
    fake_table = pd.DataFrame({"Symbol": ["AAPL", "MSFT", "BRK.B"]})

    with patch("pandas.read_html", return_value=[fake_table]):
        result = snapshot_sp500("2024-01-15")

    assert "AAPL" in result
    assert "MSFT" in result
    # BRK.B → BRK-B (dot replaced)
    assert "BRK-B" in result

    files = list(tmp_path.glob("SP500*.parquet"))
    assert len(files) == 1


# ---------------------------------------------------------------------------
# snapshot_sp500 — empty members not persisted
# ---------------------------------------------------------------------------

def test_snapshot_sp500_empty_not_persisted(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import snapshot_sp500

    import pandas as pd
    fake_table = pd.DataFrame({"Symbol": []})

    with patch("pandas.read_html", return_value=[fake_table]):
        result = snapshot_sp500("2024-01-15")

    assert result == []
    files = list(tmp_path.glob("SP500*.parquet"))
    assert len(files) == 0


# ---------------------------------------------------------------------------
# snapshot_sp500 — string as_of gets parsed
# ---------------------------------------------------------------------------

def test_snapshot_sp500_string_date_parsed(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import snapshot_sp500

    import pandas as pd
    fake_table = pd.DataFrame({"Symbol": ["AAPL"]})

    with patch("pandas.read_html", return_value=[fake_table]):
        result = snapshot_sp500("2024-06-30")

    assert result == ["AAPL"]


# ---------------------------------------------------------------------------
# snapshot_sp500 — no as_of uses today's date (default)
# ---------------------------------------------------------------------------

def test_snapshot_sp500_default_as_of(tmp_path, monkeypatch):
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path)
    from stock_rtx4060.data_lake.universe.snapshot import snapshot_sp500

    import pandas as pd
    fake_table = pd.DataFrame({"Symbol": ["MSFT"]})

    with patch("pandas.read_html", return_value=[fake_table]):
        result = snapshot_sp500()

    assert result == ["MSFT"]
