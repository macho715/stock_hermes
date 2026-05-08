"""Canonical (date, type, ratio, cash) action records sourced from yfinance/pykrx."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

ActionType = Literal["split", "dividend"]


@dataclass(frozen=True)
class CorpAction:
    """Canonical corporate action record.

    For splits, ``ratio`` is the new/old share ratio (2.0 = 2-for-1).
    For dividends, ``cash_amount`` is per-share currency value, ``ratio=None``.
    """

    date: pd.Timestamp
    type: ActionType
    ratio: float | None = None
    cash_amount: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "date": self.date.isoformat(),
            "type": self.type,
            "ratio": self.ratio,
            "cash_amount": self.cash_amount,
        }


def fetch_yf_actions(ticker: str) -> list[CorpAction]:
    """Fetch yfinance ``Ticker.actions`` and normalize to ``CorpAction``s.

    Returns empty list when network/dep is unavailable. Caller decides retry.
    """
    try:
        import yfinance as yf

        df = yf.Ticker(ticker).actions
    except Exception:
        return []
    if df is None or df.empty:
        return []
    out: list[CorpAction] = []
    for ts, row in df.iterrows():
        date_ts = pd.Timestamp(ts)
        div = float(row.get("Dividends", 0.0) or 0.0)
        split = float(row.get("Stock Splits", 0.0) or 0.0)
        if split and split != 0:
            out.append(CorpAction(date=date_ts, type="split", ratio=split))
        if div and div != 0:
            out.append(CorpAction(date=date_ts, type="dividend", cash_amount=div))
    return out


def fetch_pykrx_actions(ticker: str, start: str, end: str) -> list[CorpAction]:
    """Fetch KRX dividends/splits via pykrx.

    pykrx surfaces dividends through ``stock.get_market_fundamental_by_date``
    (DPS column) and split announcements via news APIs not all environments
    have. When unavailable returns empty list.
    """
    try:
        from pykrx import stock as pkx
    except Exception:
        return []
    try:
        df = pkx.get_market_fundamental_by_date(start, end, ticker)
    except Exception:
        return []
    if df is None or df.empty or "DPS" not in df.columns:
        return []
    out: list[CorpAction] = []
    prev = 0.0
    for ts, row in df.iterrows():
        dps = float(row.get("DPS", 0.0) or 0.0)
        if dps and dps != prev:
            out.append(CorpAction(date=pd.Timestamp(ts), type="dividend", cash_amount=dps - prev))
            prev = dps
    return out
