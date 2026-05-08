"""Back-adjust OHLCV with split + dividend factors. Idempotent."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .splits_dividends import CorpAction


def build_adjustment_factor(
    closes: pd.Series,
    actions: Iterable[CorpAction],
    *,
    use_dividends: bool = True,
) -> pd.Series:
    """Compute multiplicative back-adjustment factor aligned to ``closes`` index.

    Earlier prices get multiplied DOWN by splits and dividends so that returns
    computed on adjusted OHLCV are total-return correct. Returns a pd.Series
    of factors indexed identically to ``closes`` (1.0 on/after the latest
    action; lower for earlier dates).
    """
    if closes.empty:
        return pd.Series(dtype="float64")
    idx = closes.index
    factor = pd.Series(1.0, index=idx, dtype="float64")
    sorted_actions = sorted(actions, key=lambda a: a.date)
    for action in sorted_actions:
        before_mask = idx < action.date
        if not before_mask.any():
            continue
        if action.type == "split" and action.ratio:
            factor.loc[before_mask] *= 1.0 / float(action.ratio)
        elif action.type == "dividend" and use_dividends and action.cash_amount:
            close_at_action_idx = idx.searchsorted(action.date) - 1
            if close_at_action_idx < 0:
                continue
            close_at_action = float(closes.iloc[close_at_action_idx])
            if close_at_action > 0:
                mult = 1.0 - (float(action.cash_amount) / close_at_action)
                if mult > 0:
                    factor.loc[before_mask] *= mult
    return factor


def adjust_ohlcv(frame: pd.DataFrame, actions: Iterable[CorpAction]) -> pd.DataFrame:
    """Return a back-adjusted copy of ``frame`` with ``adj_*`` columns added.

    Original raw OHLCV columns are preserved unchanged.
    """
    if frame.empty:
        return frame.copy()
    closes = frame["Close"].astype(float)
    factor = build_adjustment_factor(closes, actions)
    out = frame.copy()
    for col in ("Open", "High", "Low", "Close"):
        if col in out.columns:
            out[f"adj_{col.lower()}"] = out[col].astype(float) * factor
    if "Volume" in out.columns:
        out["adj_volume"] = out["Volume"].astype(float) / np.where(factor > 0, factor, 1.0)
    return out
