"""PIT data lake storage backends. DuckDB+Parquet is the default zero-infra path."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_LAKE_ROOT = Path(os.environ.get("DATA_LAKE_ROOT", "./data_lake"))
DEFAULT_PARQUET_ROOT = DEFAULT_LAKE_ROOT / "parquet"


class PITStore(ABC):
    """Bitemporal OHLCV store interface."""

    @abstractmethod
    def write(self, ticker: str, frame: pd.DataFrame, *, source: str) -> int:
        """Write OHLCV rows. ``frame`` index must be DatetimeIndex of bar dates.

        Returns count of rows written. Backends MUST stamp ``_ingested_at`` =
        wall-clock UTC at write time (bitemporal column).
        """

    @abstractmethod
    def read(
        self,
        ticker: str,
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        as_of: str | datetime | None = None,
    ) -> pd.DataFrame:
        """Read PIT-correct OHLCV. When ``as_of`` is set, only rows whose
        ``_ingested_at <= as_of`` are returned."""

    @abstractmethod
    def list_tickers(self) -> list[str]:
        """Enumerate tickers stored."""

    @abstractmethod
    def close(self) -> None:
        ...


class DuckDBStore(PITStore):
    """Hive-partitioned Parquet store with DuckDB query layer.

    Layout::
        <root>/symbol=<TICKER>/date=YYYY-MM/part-<ts>.parquet

    Each parquet file holds a single ingest batch with ``_ingested_at`` set to
    the time of write. Idempotent re-writes are append-only — caller is
    responsible for de-duplicating with ``as_of`` queries.
    """

    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root) if root else DEFAULT_PARQUET_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        try:
            import duckdb  # type: ignore[import-not-found]

            self._duck = duckdb.connect(database=":memory:")
        except ImportError:
            self._duck = None

    def _partition_dir(self, ticker: str, period: str) -> Path:
        path = self.root / f"symbol={ticker}" / f"date={period}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write(self, ticker: str, frame: pd.DataFrame, *, source: str) -> int:
        if frame.empty:
            return 0
        if not isinstance(frame.index, pd.DatetimeIndex):
            raise ValueError("frame.index must be a DatetimeIndex")
        df = frame.copy()
        ingested_at = datetime.now(timezone.utc)
        df["_ingested_at"] = ingested_at
        df["_source"] = source
        df["_ticker"] = ticker
        df["_date"] = df.index.strftime("%Y-%m-%d")
        for period, sub in df.groupby(df.index.strftime("%Y-%m")):
            part_dir = self._partition_dir(ticker, str(period))
            ts = ingested_at.strftime("%Y%m%dT%H%M%S%f")
            sub.to_parquet(part_dir / f"part-{ts}.parquet", index=True)
        return int(len(df))

    def _glob(self, ticker: str | None) -> str:
        if ticker:
            return str(self.root / f"symbol={ticker}" / "**" / "*.parquet")
        return str(self.root / "**" / "*.parquet")

    def read(
        self,
        ticker: str,
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        as_of: str | datetime | None = None,
    ) -> pd.DataFrame:
        pattern = self._glob(ticker)
        files = list(Path().glob(pattern.replace(str(self.root) + "/", "").lstrip("/"))) or list(
            self.root.glob(f"symbol={ticker}/**/*.parquet")
        )
        if not files:
            return pd.DataFrame()
        dfs: list[pd.DataFrame] = []
        for fp in files:
            try:
                dfs.append(pd.read_parquet(fp))
            except Exception:
                continue
        if not dfs:
            return pd.DataFrame()
        merged = pd.concat(dfs).sort_index()
        if as_of is not None:
            as_of_ts = pd.Timestamp(as_of, tz="UTC") if pd.Timestamp(as_of).tz is None else pd.Timestamp(as_of)
            merged = merged[merged["_ingested_at"] <= as_of_ts]
        merged = merged[~merged.index.duplicated(keep="last")]
        if start is not None:
            merged = merged.loc[pd.Timestamp(start) :]
        if end is not None:
            merged = merged.loc[: pd.Timestamp(end)]
        return merged

    def list_tickers(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted({p.name.split("=", 1)[1] for p in self.root.glob("symbol=*") if p.is_dir()})

    def close(self) -> None:
        if self._duck is not None:
            self._duck.close()


_default_store: PITStore | None = None


def get_default_store() -> PITStore:
    """Resolve store from ``DATA_LAKE_BACKEND`` env. Caches singleton."""
    global _default_store
    if _default_store is not None:
        return _default_store
    backend = os.environ.get("DATA_LAKE_BACKEND", "duckdb").lower()
    if backend == "arctic":
        try:
            from arcticdb import Arctic  # type: ignore[import-not-found]

            uri = os.environ.get("ARCTIC_URI", f"lmdb://{DEFAULT_LAKE_ROOT}/arctic")
            ac = Arctic(uri)
            lib = ac.get_library("ohlcv", create_if_missing=True)
            _default_store = _ArcticAdapter(lib)
            return _default_store
        except ImportError:
            backend = "duckdb"
    _default_store = DuckDBStore()
    return _default_store


class _ArcticAdapter(PITStore):
    """Thin adapter over an arcticdb library, used when ``arcticdb`` is installed."""

    def __init__(self, library: Any) -> None:
        self._lib = library

    def write(self, ticker: str, frame: pd.DataFrame, *, source: str) -> int:
        if frame.empty:
            return 0
        df = frame.copy()
        df["_ingested_at"] = datetime.now(timezone.utc)
        df["_source"] = source
        self._lib.append(ticker, df, validate_index=True, prune_previous_versions=False)
        return len(df)

    def read(
        self,
        ticker: str,
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        as_of: str | datetime | None = None,
    ) -> pd.DataFrame:
        if ticker not in self._lib.list_symbols():
            return pd.DataFrame()
        df = self._lib.read(ticker).data
        if as_of is not None:
            as_of_ts = pd.Timestamp(as_of, tz="UTC")
            df = df[df["_ingested_at"] <= as_of_ts]
        if start is not None:
            df = df.loc[pd.Timestamp(start) :]
        if end is not None:
            df = df.loc[: pd.Timestamp(end)]
        return df

    def list_tickers(self) -> list[str]:
        return list(self._lib.list_symbols())

    def close(self) -> None:
        return None
