"""OpenBB macroeconomic data ingestor.

Fetches MMA (macroeconomic analytics) data from OpenBB and writes into
the PIT lake. Graceful degradation: if OpenBB is unavailable, logs a
warning and returns 0 without crashing the main trading path.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _openbb_available() -> bool:
    """Check whether the ``openbb`` package is importable."""
    try:
        import openbb  # noqa: F401
        return True
    except ImportError:
        return False


def ingest_openbb_macro(
    *,
    tickers: list[str] | None = None,
    store=None,
) -> int:
    """Fetch macro data via OpenBB and write to the PIT lake.

    Parameters
    ----------
    tickers :
        FRED indicator codes to fetch (default: ``["T10Y2Y", "VIXCLS", "DTWEXBGS"]``).
    store :
        PIT store instance. If ``None`` the default store is used.

    Returns
    -------
    int
        Number of rows written (0 if OpenBB is unavailable or no data returned).

    Design principles
    ----------------
    - Graceful degradation: OpenBB unavailable → warning log + return 0.
    - No hard dependency on OpenBB in the main trading path.
    """
    if not _openbb_available():
        logger.warning("openbb not installed — skipping macro data ingest")
        return 0

    try:
        from openbb import OpenBB
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("openbb import failed: %s", exc)
        return 0

    obb = OpenBB()
    tickers = tickers or ["T10Y2Y", "VIXCLS", "DTWEXBGS"]

    try:
        result = obb.economy.index(symbols=tickers)
    except Exception as exc:  # pragma: no cover — network errors
        logger.warning("obb.economy.index fetch failed: %s", exc)
        return 0

    if result is None:
        return 0

    try:
        import pandas as pd

        df = result.to_pandas()
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            return 0
    except Exception as exc:  # pragma: no cover — conversion errors
        logger.warning("openbb result to_pandas failed: %s", exc)
        return 0

    if store is None:
        logger.warning("no PIT store provided — skipping write")
        return 0

    try:
        written = store.write("OPENBB_MACRO", df, source="openbb")
        return written
    except Exception as exc:  # pragma: no cover — write errors
        logger.warning("PIT store write failed: %s", exc)
        return 0


__all__ = ["ingest_openbb_macro"]
