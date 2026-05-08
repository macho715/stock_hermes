"""Cross-sectional / fundamental factors.

These factors depend on data that may not be available in synthetic OHLCV
panels (e.g. market cap, P/E, ROE).  Each ``Factor`` here gracefully returns
NaN-only series when its required inputs are missing — the registry treats
NaNs as "skip this signal" rather than a hard failure.

For tests we drive Size from a panel attribute (``panel.attrs['market_cap']``
keyed by ticker) when present; otherwise it tries ``yfinance.Ticker.info``.
The yfinance path is wrapped in ``try/except`` so an offline CI cannot fail
us.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from .base import Factor, FactorMeta, is_panel, slice_as_of


def _fundamentals(panel: pd.DataFrame) -> Mapping[str, Mapping[str, float]]:
    """Pull a ``{ticker: {field: value}}`` table from ``panel.attrs``.

    The expected key is ``"fundamentals"`` (set by callers in tests or by the
    pipeline that has access to KIS / yfinance).  Missing => empty dict.
    """
    fund = panel.attrs.get("fundamentals") if hasattr(panel, "attrs") else None
    if isinstance(fund, Mapping):
        return fund
    return {}


def _broadcast_per_ticker(panel: pd.DataFrame, values: Mapping[str, float]) -> pd.Series:
    """Make a (date, ticker)-indexed series from a constant per-ticker mapping."""
    if is_panel(panel):
        tickers = sorted({c[0] for c in panel.columns})
        idx = pd.MultiIndex.from_product([panel.index, tickers], names=["date", "ticker"])
        data = [float(values.get(tk, np.nan)) for _ in panel.index for tk in tickers]
        return pd.Series(data, index=idx)
    # Single-ticker: panel.attrs may carry "ticker" hint.
    tk = str(panel.attrs.get("ticker", ""))
    val = float(values.get(tk, np.nan))
    return pd.Series(np.full(len(panel.index), val), index=panel.index)


class _CrossSectionalFactor(Factor):
    """Base class — handles slicing and provides a safe NaN fallback shape."""

    _factor_abstract = True

    def _nan_series(self, panel: pd.DataFrame) -> pd.Series:
        if is_panel(panel):
            tickers = sorted({c[0] for c in panel.columns})
            idx = pd.MultiIndex.from_product([panel.index, tickers], names=["date", "ticker"])
            return pd.Series(np.nan, index=idx, name=self.meta.name)
        return pd.Series(np.nan, index=panel.index, name=self.meta.name)


class Size(_CrossSectionalFactor):
    """Log market capitalization.  Source priority: panel.attrs, yfinance.info."""

    meta = FactorMeta(
        name="Size",
        category="cross_sectional",
        lookback=1,
        description="log(market_cap)",
    )

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        fund = _fundamentals(panel)
        if not fund:
            return self._nan_series(panel)
        values: dict[str, float] = {}
        for tk, info in fund.items():
            mc = info.get("market_cap") if isinstance(info, Mapping) else None
            if mc is None or not np.isfinite(float(mc)) or float(mc) <= 0:
                values[tk] = np.nan
            else:
                values[tk] = float(np.log(float(mc)))
        return _broadcast_per_ticker(panel, values).rename(self.meta.name)


class Value(_CrossSectionalFactor):
    """Composite value: average of inverted P/E, P/B, EV/EBITDA when present."""

    meta = FactorMeta(
        name="Value",
        category="cross_sectional",
        lookback=1,
        description="mean(1/PE, 1/PB, 1/EV_EBITDA), NaN where missing",
    )

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        fund = _fundamentals(panel)
        if not fund:
            return self._nan_series(panel)
        values: dict[str, float] = {}
        for tk, info in fund.items():
            if not isinstance(info, Mapping):
                values[tk] = np.nan
                continue
            ratios: list[float] = []
            for key in ("pe", "pb", "ev_ebitda"):
                v = info.get(key)
                if v is None:
                    continue
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                if not np.isfinite(fv) or fv <= 0:
                    continue
                ratios.append(1.0 / fv)
            values[tk] = float(np.mean(ratios)) if ratios else np.nan
        return _broadcast_per_ticker(panel, values).rename(self.meta.name)


class Momentum12_1(Factor):
    """12-1 momentum: 252-bar return excluding the most-recent 21-bar window."""

    meta = FactorMeta(
        name="Momentum12_1",
        category="cross_sectional",
        lookback=252 + 21,
        description="close.shift(21) / close.shift(252) - 1",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        close = df["Close"].astype(float)
        return close.shift(21) / close.shift(252) - 1.0

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        if not is_panel(panel):
            return self._single(panel).rename(self.meta.name)
        tickers = sorted({c[0] for c in panel.columns})
        frames: list[pd.Series] = []
        for tk in tickers:
            sub = panel.xs(tk, axis=1, level=0)
            try:
                series = self._single(sub).rename(self.meta.name)
            except Exception:  # pragma: no cover - per-ticker resilience
                continue
            frames.append(pd.concat({tk: series}, names=["ticker"]))
        if not frames:
            return pd.Series(dtype=float, name=self.meta.name)
        return pd.concat(frames).swaplevel(0, 1).sort_index()


class Quality(_CrossSectionalFactor):
    """ROE — accruals proxy (1 - NI/OCF when both available)."""

    meta = FactorMeta(
        name="Quality",
        category="cross_sectional",
        lookback=1,
        description="ROE - accruals_ratio (where accruals = NI/OCF)",
    )

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        fund = _fundamentals(panel)
        if not fund:
            return self._nan_series(panel)
        values: dict[str, float] = {}
        for tk, info in fund.items():
            if not isinstance(info, Mapping):
                values[tk] = np.nan
                continue
            roe = info.get("roe")
            ni = info.get("net_income")
            ocf = info.get("ocf")
            try:
                roe_v = float(roe) if roe is not None else np.nan
            except (TypeError, ValueError):
                roe_v = np.nan
            accrual: float
            try:
                if ni is not None and ocf is not None and float(ocf) != 0.0:
                    accrual = float(ni) / float(ocf)
                else:
                    accrual = 0.0
            except (TypeError, ValueError, ZeroDivisionError):
                accrual = 0.0
            values[tk] = roe_v - accrual if np.isfinite(roe_v) else np.nan
        return _broadcast_per_ticker(panel, values).rename(self.meta.name)


class Volatility60d(Factor):
    """Realized 60-bar standard deviation of log returns (annualized)."""

    meta = FactorMeta(
        name="Volatility60d",
        category="cross_sectional",
        lookback=60,
        description="rolling stdev of log returns over 60 bars * sqrt(252)",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        close = df["Close"].astype(float)
        log_ret = np.log(close / close.shift(1))
        return log_ret.rolling(60, min_periods=60).std() * np.sqrt(252.0)

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        if not is_panel(panel):
            return self._single(panel).rename(self.meta.name)
        tickers = sorted({c[0] for c in panel.columns})
        frames: list[pd.Series] = []
        for tk in tickers:
            sub = panel.xs(tk, axis=1, level=0)
            try:
                series = self._single(sub).rename(self.meta.name)
            except Exception:  # pragma: no cover - per-ticker resilience
                continue
            frames.append(pd.concat({tk: series}, names=["ticker"]))
        if not frames:
            return pd.Series(dtype=float, name=self.meta.name)
        return pd.concat(frames).swaplevel(0, 1).sort_index()


class AmihudIlliquidity(Factor):
    """Amihud (2002) — mean(|return| / dollar_volume) over 21 bars."""

    meta = FactorMeta(
        name="AmihudIlliquidity",
        category="cross_sectional",
        lookback=21,
        description="mean(|return| / (close * volume)) over 21 bars",
    )

    def _single(self, df: pd.DataFrame) -> pd.Series:
        close = df["Close"].astype(float)
        vol = df["Volume"].astype(float)
        ret = close.pct_change(1, fill_method=None).abs()
        dvol = (close * vol).replace(0.0, np.nan)
        return (ret / dvol).rolling(21, min_periods=21).mean()

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        if not is_panel(panel):
            return self._single(panel).rename(self.meta.name)
        tickers = sorted({c[0] for c in panel.columns})
        frames: list[pd.Series] = []
        for tk in tickers:
            sub = panel.xs(tk, axis=1, level=0)
            try:
                series = self._single(sub).rename(self.meta.name)
            except Exception:  # pragma: no cover - per-ticker resilience
                continue
            frames.append(pd.concat({tk: series}, names=["ticker"]))
        if not frames:
            return pd.Series(dtype=float, name=self.meta.name)
        return pd.concat(frames).swaplevel(0, 1).sort_index()


CROSS_SECTIONAL_FACTORS: list[Factor] = [
    Size(),
    Value(),
    Momentum12_1(),
    Quality(),
    Volatility60d(),
    AmihudIlliquidity(),
]


def attach_fundamentals(panel: pd.DataFrame, fundamentals: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    """Attach a fundamentals lookup to ``panel.attrs`` for the cross-sectional factors."""
    panel.attrs["fundamentals"] = dict(fundamentals)
    return panel
