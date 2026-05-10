"""yfinance → PIT lake ingestor. Reuses existing data_providers loader."""
from __future__ import annotations

from ..audit_provenance import log_pit_write
from ..store import PITStore, get_default_store


def ingest_yf(
    ticker: str,
    *,
    period: str = "5y",
    store: PITStore | None = None,
) -> int:
    """Fetch ``ticker`` OHLCV via yfinance and write into the PIT lake."""
    try:
        import yfinance as yf
    except ImportError:
        return 0
    df = yf.Ticker(ticker).history(period=period, auto_adjust=False)
    if df is None or df.empty:
        return 0
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    store = store or get_default_store()
    written = store.write(ticker, df, source="yfinance")
    log_pit_write(ticker=ticker, source="yfinance", rows=written, backend=type(store).__name__)
    return written
