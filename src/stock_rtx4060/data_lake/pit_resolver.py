"""Point-in-time read facade. ``read(...)`` is the only PIT API consumers should use."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .audit_provenance import log_pit_read
from .store import PITStore, get_default_store


def read(
    ticker: str,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    *,
    as_of: str | datetime | None = None,
    store: PITStore | None = None,
) -> pd.DataFrame:
    """Return PIT-correct OHLCV slice for ``ticker``.

    All rows returned are guaranteed to have ``_ingested_at <= as_of``. When
    ``as_of`` is None, the latest data wins (regular non-PIT read).
    """
    store = store or get_default_store()
    df = store.read(ticker, start=start, end=end, as_of=as_of)
    log_pit_read(ticker=ticker, as_of=as_of, rows=len(df), backend=type(store).__name__)
    return df


def has_data(ticker: str, *, store: PITStore | None = None) -> bool:
    store = store or get_default_store()
    return ticker in store.list_tickers()
