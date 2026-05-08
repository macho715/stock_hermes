"""Phase 1 PIT data lake tests. Use temp dirs only — no network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_ohlcv() -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-02", periods=20)
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 1, len(idx)))
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.02,
            "Low": close * 0.98,
            "Close": close,
            "Volume": rng.integers(1_000_000, 5_000_000, len(idx)).astype(float),
        },
        index=idx,
    )


def test_duckdb_store_roundtrip(tmp_path: Path, synthetic_ohlcv: pd.DataFrame) -> None:
    from stock_rtx4060.data_lake.store import DuckDBStore

    store = DuckDBStore(root=tmp_path)
    written = store.write("AAPL", synthetic_ohlcv, source="test")
    assert written == 20
    df = store.read("AAPL")
    assert len(df) == 20
    assert "_ingested_at" in df.columns
    assert "AAPL" in store.list_tickers()
    store.close()


def test_pit_as_of_excludes_future_writes(tmp_path: Path, synthetic_ohlcv: pd.DataFrame) -> None:
    from stock_rtx4060.data_lake.store import DuckDBStore

    store = DuckDBStore(root=tmp_path)
    store.write("MSFT", synthetic_ohlcv, source="test")
    after_first = datetime.now(timezone.utc) + timedelta(seconds=1)
    df_full = store.read("MSFT", as_of=after_first + timedelta(days=1))
    assert len(df_full) == 20
    df_past = store.read("MSFT", as_of=after_first - timedelta(seconds=10))
    assert len(df_past) == 0


def test_pit_resolver_logs_provenance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, synthetic_ohlcv: pd.DataFrame) -> None:
    from stock_rtx4060.data_lake import pit_resolver
    from stock_rtx4060.data_lake.store import DuckDBStore

    log_path = tmp_path / "audit_log" / "provenance.jsonl"
    monkeypatch.setattr(
        "stock_rtx4060.data_lake.audit_provenance.DEFAULT_PROVENANCE_PATH", log_path
    )
    store = DuckDBStore(root=tmp_path / "lake")
    store.write("GOOG", synthetic_ohlcv, source="test")
    df = pit_resolver.read("GOOG", store=store)
    assert len(df) == 20
    assert log_path.exists()
    contents = log_path.read_text().splitlines()
    assert any('"event": "pit_read"' in line for line in contents)


def test_corp_actions_split_adjustment() -> None:
    from stock_rtx4060.data_lake.corp_actions import CorpAction, adjust_ohlcv

    idx = pd.bdate_range("2024-01-02", periods=10)
    df = pd.DataFrame(
        {"Open": [100] * 10, "High": [101] * 10, "Low": [99] * 10, "Close": [100] * 10, "Volume": [1_000_000] * 10},
        index=idx,
    )
    actions = [CorpAction(date=pd.Timestamp("2024-01-08"), type="split", ratio=2.0)]
    out = adjust_ohlcv(df, actions)
    pre_split = out.loc[out.index < pd.Timestamp("2024-01-08")]
    post_split = out.loc[out.index >= pd.Timestamp("2024-01-08")]
    assert (pre_split["adj_close"] == 50.0).all()
    assert (post_split["adj_close"] == 100.0).all()
    assert (pre_split["adj_volume"] == 2_000_000).all()


def test_universe_snapshot_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stock_rtx4060.data_lake.universe.snapshot.UNIVERSE_ROOT", tmp_path / "universe")
    from stock_rtx4060.data_lake.universe.snapshot import (
        list_snapshots,
        load_snapshot,
        write_snapshot,
    )

    write_snapshot("KOSPI200", "2024-06-30", ["005930", "000660", "035720"])
    members = load_snapshot("KOSPI200", "2024-06-30")
    assert members == ["000660", "005930", "035720"]
    files = list_snapshots("KOSPI200")
    assert len(files) == 1


def test_kis_credentials_require_chmod_600(tmp_path: Path) -> None:
    from stock_rtx4060.data_lake.ingest.kis_ingestor import _load_credentials

    cred_file = tmp_path / "kis.toml"
    cred_file.write_text('appkey = "demo"\nappsecret = "demo"\n')
    cred_file.chmod(0o644)
    with pytest.raises(PermissionError):
        _load_credentials(cred_file)
    cred_file.chmod(0o600)
    creds = _load_credentials(cred_file)
    assert creds.appkey == "demo"
