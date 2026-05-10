"""Alpaca historical bars → PIT lake ingestor (alpaca-py SDK)."""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from ..audit_provenance import log_pit_write
from ..store import PITStore, get_default_store


def ingest_alpaca(
    ticker: str,
    *,
    start: str | None = None,
    end: str | None = None,
    timeframe: str = "1Day",
    store: PITStore | None = None,
) -> int:
    """Ingest Alpaca historical equity bars into PIT lake.

    Requires ``ALPACA_API_KEY`` and ``ALPACA_SECRET_KEY`` env vars (paper or
    live). Defaults to last 5y when ``start`` is omitted.
    """
    api_key = os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY")
    if not api_key or not secret:
        return 0
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
    except ImportError:
        return 0
    end_dt = datetime.fromisoformat(end) if end else datetime.now(UTC)
    start_dt = datetime.fromisoformat(start) if start else end_dt - timedelta(days=365 * 5)
    tf_map = {
        "1Day": TimeFrame.Day,
        "1Hour": TimeFrame.Hour,
        "1Min": TimeFrame.Minute,
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
    }
    tf = tf_map.get(timeframe, TimeFrame.Day)
    client = StockHistoricalDataClient(api_key, secret)
    req = StockBarsRequest(symbol_or_symbols=ticker, timeframe=tf, start=start_dt, end=end_dt)
    bars = client.get_stock_bars(req)
    df = bars.df
    if df is None or df.empty:
        return 0
    if "symbol" in df.index.names:
        df = df.xs(ticker, level="symbol")
    df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    store = store or get_default_store()
    written = store.write(ticker, df, source="alpaca")
    log_pit_write(ticker=ticker, source="alpaca", rows=written, backend=type(store).__name__)
    return written
