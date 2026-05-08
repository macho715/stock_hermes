"""WorldQuant 101 Formulaic Alphas — pandas/numpy implementations.

Reference
---------
Kakushadze, Z. (2016). *101 Formulaic Alphas*.
Wilmott Magazine, 2016, 72-81.  arXiv:1601.00991.

Notation used in this module follows the paper:

* ``returns``: daily simple return ``close / delay(close, 1) - 1``.
* ``rank(x)``: cross-sectional rank, normalized to [0, 1] (per date).  When
  the input panel only has a single ticker, cross-sectional ranking is
  undefined and we substitute the standardized rank within a 252-day rolling
  window — this preserves the spirit (relative ordering) without a panel.
* ``delay(x, d)``: ``x.shift(d)``.
* ``ts_rank(x, d)``: rank of the most recent value within the last ``d``
  observations (1..d).
* ``ts_max(x, d)`` / ``ts_min(x, d)`` / ``sum(x, d)`` / ``stddev(x, d)``:
  standard rolling-window operators with ``min_periods=d``.

Alphas implemented in this first pass:

* Alpha #1   — ``rank(ts_argmax(SignedPower(ret<0 ? stddev(ret,20) : close, 2.), 5)) - 0.5``
* Alpha #3   — ``-1 * correlation(rank(open), rank(volume), 10)``
* Alpha #6   — ``-1 * correlation(open, volume, 10)``
* Alpha #12  — ``sign(delta(volume, 1)) * (-1 * delta(close, 1))``
* Alpha #41  — ``((high * low)^0.5) - vwap``
* Alpha #54  — ``(-1 * ((low - close) * (open^5))) / ((low - high) * (close^5))``
* Alpha #101 — ``(close - open) / ((high - low) + 0.001)``
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Factor, FactorMeta, is_panel, slice_as_of

# ---------------------------------------------------------------------------
# Helper operators


def _rank(series: pd.Series, window: int = 252) -> pd.Series:
    """Approximation of a cross-sectional rank for single-ticker context.

    For a wide panel, callers should rank along the cross-section themselves.
    Here we use a rolling-window time-series rank normalized to [0, 1] which
    behaves well as an alpha building block on a single instrument.
    """
    return series.rolling(window=window, min_periods=10).apply(
        lambda arr: float(pd.Series(arr).rank(pct=True).iloc[-1]), raw=False
    )


def _ts_argmax(series: pd.Series, d: int) -> pd.Series:
    return series.rolling(d, min_periods=d).apply(lambda arr: float(np.argmax(arr)), raw=True)


def _signed_power(x: pd.Series, p: float) -> pd.Series:
    return np.sign(x) * (np.abs(x) ** p)


def _stddev(x: pd.Series, d: int) -> pd.Series:
    return x.rolling(d, min_periods=d).std()


def _correlation(x: pd.Series, y: pd.Series, d: int) -> pd.Series:
    return x.rolling(d, min_periods=d).corr(y)


def _delta(x: pd.Series, d: int) -> pd.Series:
    return x.diff(d)


def _vwap_proxy(df: pd.DataFrame) -> pd.Series:
    """A rolling 5-bar VWAP proxy when intraday VWAP isn't available."""
    typical = (df["High"] + df["Low"] + df["Close"]) / 3.0
    pv = typical * df["Volume"]
    win = 5
    return pv.rolling(win, min_periods=win).sum() / df["Volume"].rolling(win, min_periods=win).sum()


# ---------------------------------------------------------------------------
# Single-ticker computations (each Alpha returns a Series for the input frame)


def _alpha001_single(df: pd.DataFrame) -> pd.Series:
    close = df["Close"].astype(float)
    ret = close.pct_change(1, fill_method=None)
    cond = ret < 0.0
    base = pd.Series(np.where(cond, _stddev(ret, 20), close), index=df.index)
    sp = _signed_power(base, 2.0)
    arg = _ts_argmax(sp, 5)
    return _rank(arg) - 0.5


def _alpha003_single(df: pd.DataFrame) -> pd.Series:
    open_r = _rank(df["Open"].astype(float))
    vol_r = _rank(df["Volume"].astype(float))
    return -1.0 * _correlation(open_r, vol_r, 10)


def _alpha006_single(df: pd.DataFrame) -> pd.Series:
    return -1.0 * _correlation(df["Open"].astype(float), df["Volume"].astype(float), 10)


def _alpha012_single(df: pd.DataFrame) -> pd.Series:
    sign_dv = np.sign(_delta(df["Volume"].astype(float), 1))
    return sign_dv * (-1.0 * _delta(df["Close"].astype(float), 1))


def _alpha041_single(df: pd.DataFrame) -> pd.Series:
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    return np.sqrt(high * low) - _vwap_proxy(df)


def _alpha054_single(df: pd.DataFrame) -> pd.Series:
    open_ = df["Open"].astype(float)
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    num = -1.0 * (low - close) * (open_**5)
    den = (low - high) * (close**5)
    return num / den.replace(0.0, np.nan)


def _alpha101_single(df: pd.DataFrame) -> pd.Series:
    open_ = df["Open"].astype(float)
    close = df["Close"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    return (close - open_) / ((high - low) + 0.001)


# ---------------------------------------------------------------------------
# Factor classes


class _AlphaFactor(Factor):
    """Shared dispatch for Alpha101 factors.  Subclasses provide ``_single``."""

    _factor_abstract = True

    def _single(self, df: pd.DataFrame) -> pd.Series:  # pragma: no cover - abstract
        raise NotImplementedError

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        if not is_panel(panel):
            return self._single(panel).rename(self.meta.name)
        tickers = sorted({c[0] for c in panel.columns})
        out: list[pd.Series] = []
        for tk in tickers:
            sub = panel.xs(tk, axis=1, level=0)
            try:
                series = self._single(sub).rename(self.meta.name)
            except Exception:  # pragma: no cover - per-ticker resilience
                continue
            out.append(pd.concat({tk: series}, names=["ticker"]))
        if not out:
            return pd.Series(dtype=float, name=self.meta.name)
        return pd.concat(out).swaplevel(0, 1).sort_index()


class Alpha001(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha001",
        category="alpha101",
        lookback=30,
        description="rank(ts_argmax(SignedPower(ret<0?stddev(ret,20):close,2.),5))-0.5",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha001_single(df)


class Alpha003(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha003",
        category="alpha101",
        lookback=20,
        description="-1 * correlation(rank(open), rank(volume), 10)",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha003_single(df)


class Alpha006(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha006",
        category="alpha101",
        lookback=10,
        description="-1 * correlation(open, volume, 10)",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha006_single(df)


class Alpha012(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha012",
        category="alpha101",
        lookback=2,
        description="sign(delta(volume,1)) * (-1 * delta(close,1))",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha012_single(df)


class Alpha041(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha041",
        category="alpha101",
        lookback=5,
        description="sqrt(high*low) - vwap5",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha041_single(df)


class Alpha054(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha054",
        category="alpha101",
        lookback=1,
        description="-1 * ((low - close) * open^5) / ((low - high) * close^5)",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha054_single(df)


class Alpha101(_AlphaFactor):
    meta = FactorMeta(
        name="Alpha101",
        category="alpha101",
        lookback=1,
        description="(close - open) / (high - low + 0.001)",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        return _alpha101_single(df)


ALPHA101_FACTORS: list[Factor] = [
    Alpha001(),
    Alpha003(),
    Alpha006(),
    Alpha012(),
    Alpha041(),
    Alpha054(),
    Alpha101(),
]
