"""Daily universe membership snapshots stored as Parquet under data_lake/universe."""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

UNIVERSE_ROOT = Path(os.environ.get("DATA_LAKE_ROOT", "./data_lake")) / "universe_snapshots"


def _path(universe: str, as_of: date | str) -> Path:
    UNIVERSE_ROOT.mkdir(parents=True, exist_ok=True)
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    return UNIVERSE_ROOT / f"{universe}_{as_of.isoformat()}.parquet"


def write_snapshot(universe: str, as_of: date | str, members: Iterable[str]) -> Path:
    """Persist a universe→members mapping for a single ``as_of`` date."""
    path = _path(universe, as_of)
    df = pd.DataFrame({"ticker": sorted(set(members))})
    df["universe"] = universe
    df["as_of"] = pd.Timestamp(as_of)
    df.to_parquet(path, index=False)
    return path


def load_snapshot(universe: str, as_of: date | str) -> list[str]:
    path = _path(universe, as_of)
    if not path.exists():
        return []
    return pd.read_parquet(path)["ticker"].tolist()


def list_snapshots(universe: str | None = None) -> list[Path]:
    if not UNIVERSE_ROOT.exists():
        return []
    pattern = f"{universe}_*.parquet" if universe else "*.parquet"
    return sorted(UNIVERSE_ROOT.glob(pattern))


def snapshot_kospi200(as_of: date | str | None = None) -> list[str]:
    """Snapshot KOSPI200 membership via pykrx and persist."""
    try:
        from pykrx import stock as pkx
    except ImportError:
        return []
    target = as_of or date.today()
    if isinstance(target, str):
        target = date.fromisoformat(target)
    yyyymmdd = target.strftime("%Y%m%d")
    try:
        members = list(pkx.get_index_portfolio_deposit_file("1028", yyyymmdd))
    except Exception:
        members = []
    if members:
        write_snapshot("KOSPI200", target, members)
    return members


def snapshot_sp500(as_of: date | str | None = None) -> list[str]:
    """Snapshot S&P500 membership via Wikipedia HTML table and persist.

    Note: Wikipedia returns CURRENT membership, not historical. For true PIT
    correctness, backfill from the ``archive/`` directory if available.
    """
    target = as_of or date.today()
    if isinstance(target, str):
        target = date.fromisoformat(target)
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        members = tables[0]["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()
    except Exception:
        members = []
    if members:
        write_snapshot("SP500", target, members)
    return members
