"""Technical-analysis factors that wrap ``feature_engine.TechnicalIndicators``.

All implementations defer the actual numerical work to the existing battle-
tested ``TechnicalIndicators`` class — this keeps maths in exactly one place
and lets these factors inherit the leak-safe shifting that the legacy feature
engine already enforces.
"""

from __future__ import annotations

import pandas as pd

from ..feature_engine import TechnicalIndicators
from .base import Factor, FactorMeta, is_panel, slice_as_of


def _ohlcv_for_ticker(panel: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Slice a wide MultiIndex panel down to a single-ticker OHLCV frame."""
    cols = panel.xs(ticker, axis=1, level=0)
    return cols.copy()


class _TechnicalFactor(Factor):
    """Shared dispatch logic for indicators that wrap TechnicalIndicators."""

    _factor_abstract = True

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:  # pragma: no cover - abstract
        raise NotImplementedError

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        panel = slice_as_of(panel, as_of)
        if not is_panel(panel):
            return self._compute_single(panel).rename(self.meta.name)
        # Wide MultiIndex panel: iterate per ticker, stack the results.
        tickers = sorted({c[0] for c in panel.columns})
        frames: list[pd.Series] = []
        for tk in tickers:
            sub = _ohlcv_for_ticker(panel, tk)
            try:
                series = self._compute_single(sub)
            except Exception:  # pragma: no cover - per-ticker resilience
                continue
            series = series.rename(self.meta.name)
            frames.append(pd.concat({tk: series}, names=["ticker"]))
        if not frames:
            return pd.Series(dtype=float, name=self.meta.name)
        out = pd.concat(frames)
        # Reorder index as (date, ticker) for downstream join semantics.
        return out.swaplevel(0, 1).sort_index()


class RSI14(_TechnicalFactor):
    """Relative Strength Index, 14-bar Wilder smoothing."""

    meta = FactorMeta(name="RSI14", category="technical", lookback=14, description="Wilder RSI(14)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        return TechnicalIndicators(df).rsi(14)


class MACDHistogram(_TechnicalFactor):
    """MACD histogram (12-26-9), normalized by close."""

    meta = FactorMeta(
        name="MACDHistogram", category="technical", lookback=35, description="MACD(12,26,9) histogram / close"
    )

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        ti = TechnicalIndicators(df)
        _, _, hist = ti.macd()
        return hist / ti.close.replace(0.0, float("nan"))


class BBPct(_TechnicalFactor):
    """Bollinger %B over 20 bars, width 2σ."""

    meta = FactorMeta(name="BBPct", category="technical", lookback=20, description="Bollinger %B(20, 2σ)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        _, _, _, _, pct_b = TechnicalIndicators(df).bollinger_bands(20, 2.0)
        return pct_b


class ADX14(_TechnicalFactor):
    """Average Directional Index, 14-bar."""

    meta = FactorMeta(name="ADX14", category="technical", lookback=14, description="Wilder ADX(14)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        return TechnicalIndicators(df).adx(14)


class CMF20(_TechnicalFactor):
    """Chaikin Money Flow, 20-bar."""

    meta = FactorMeta(name="CMF20", category="technical", lookback=20, description="Chaikin Money Flow(20)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        return TechnicalIndicators(df).chaikin_money_flow(20)


class VolumeRatio20(_TechnicalFactor):
    """Volume / 20-bar mean volume."""

    meta = FactorMeta(name="VolumeRatio20", category="technical", lookback=20, description="Volume / SMA20(volume)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        ti = TechnicalIndicators(df)
        return ti.volume / ti.volume.rolling(20, min_periods=20).mean()


class VortexDiff14(_TechnicalFactor):
    """Vortex VI+ minus VI-, 14-bar."""

    meta = FactorMeta(name="VortexDiff14", category="technical", lookback=14, description="VI+ - VI- (14)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        plus, minus = TechnicalIndicators(df).vortex_indicator(14)
        return plus - minus


class Return5d(_TechnicalFactor):
    """5-bar arithmetic return."""

    meta = FactorMeta(name="Return5d", category="technical", lookback=5, description="Close.pct_change(5)")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        return TechnicalIndicators(df).close.pct_change(5, fill_method=None)


class SMARatio20(_TechnicalFactor):
    """Close / SMA(20) - 1."""

    meta = FactorMeta(name="SMARatio20", category="technical", lookback=20, description="close / SMA20 - 1")

    def _compute_single(self, df: pd.DataFrame) -> pd.Series:
        ti = TechnicalIndicators(df)
        sma = ti.sma(20)
        return ti.close / sma - 1.0


TECHNICAL_FACTORS: list[Factor] = [
    RSI14(),
    MACDHistogram(),
    BBPct(),
    ADX14(),
    CMF20(),
    VolumeRatio20(),
    VortexDiff14(),
    Return5d(),
    SMARatio20(),
]
