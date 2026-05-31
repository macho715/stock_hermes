"""Quant1901 Trend Factor — wraps quant1901_executor raw_signal as a Factor.

This registers the quant1901 EMA-crossover + RSI + HTF-regime signal into
the stock_1901 FactorRegistry so it can participate in IC ranking,
correlation analysis, and compute_all() panel scans.

Key design decisions
--------------------
* category = "technical" (closest built-in category; raw_signal is a
  rule-based technical signal, not an alpha101/alpha158 formula)
* lookback = 60 (quant1901_executor enforces >= 60 rows; the default
  slow_window=50 + htf_regime warmup drives this)
* PIT guard: closed_bar_higher_timeframe_regime already shifts the HTF
  series by one bar before ffill, so no additional as_of slicing is needed
  beyond the standard slice_as_of() call in compute().
* OHLCV normalization: delegated to normalize_ohlcv() inside build_signal_frame.

Registration: import this module to auto-register via register_factor().
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from .base import Factor, FactorMeta
from .factor_zoo import register_factor

# ---------------------------------------------------------------------------
# Ensure quant1901_executor is importable.
# If the bundle is installed as a package this path insert is a no-op.
# ---------------------------------------------------------------------------
_BUNDLE = Path(__file__).resolve().parents[4] / "quant1901_executable_bundle"
if _BUNDLE.exists() and str(_BUNDLE) not in sys.path:
    sys.path.insert(0, str(_BUNDLE))


class Quant1901TrendFactor(Factor):
    """EMA-crossover + RSI + HTF-regime signal from quant1901_executor.

    Returns 1.0 (signal active) or 0.0 (no signal) per bar, aligned to the
    input panel's date index.  NaN rows (< lookback warmup) are propagated
    as 0.0 to keep the Series dense and IC-computable.
    """

    meta = FactorMeta(
        name="quant1901_trend",
        # NOTE — category="technical": IC ranking에는 참여하지만 compute_all()
        # cross-section z-score normalization은 제외된다.
        # cross-sectional normalization이 필요하면 "momentum"으로 변경하되
        # test_factor_zoo.py의 category assertion을 함께 업데이트해야 한다.
        category="technical",
        lookback=60,
        description=(
            "EMA crossover (fast/slow) AND RSI filter AND higher-timeframe regime gate. "
            "Source: quant1901_executor.build_signal_frame(). "
            "HTF bar-close shift prevents look-ahead on the regime column. "
            "Minimum 60 rows required (normalize_ohlcv guard); "
            "short panels < ~25 rows may produce all-bullish HTF regime (fallback)."
        ),
        source="manual",
    )

    def compute(self, panel: pd.DataFrame, as_of: pd.Timestamp | None = None) -> pd.Series:
        """Return raw_signal series (0.0 / 1.0) aligned to panel.index."""
        from .base import is_panel, slice_as_of

        if is_panel(panel):
            # Wide MultiIndex panel: compute per-ticker and stack.
            panel = slice_as_of(panel, as_of)
            tickers = panel.columns.get_level_values(0).unique()
            results = []
            for tkr in tickers:
                sub = panel[tkr].copy()
                s = self._compute_single(sub, as_of=None)  # already sliced
                s.name = tkr
                results.append(s)
            if not results:
                return pd.Series(dtype=float)
            combined = pd.concat(results, keys=tickers, names=["ticker", "date"])
            return combined.swaplevel().sort_index()

        panel = slice_as_of(panel, as_of)
        return self._compute_single(panel)

    def _compute_single(
        self,
        df: pd.DataFrame,
        as_of: pd.Timestamp | None = None,  # already applied upstream
    ) -> pd.Series:
        # Blocker 1 — PIT guard: panels shorter than lookback raise ValueError
        # inside normalize_ohlcv(). Return zeros instead of propagating.
        if len(df) < self.meta.lookback:
            return pd.Series(0.0, index=df.index, name=self.meta.name)

        # Blocker 2 — HTF warmup: fewer than ~25 rows (≈5 weekly bars) causes
        # closed_bar_higher_timeframe_regime() to fall back to all-1.0 (bullish).
        # Log a debug note so IC reviewers know the regime column is trivial.
        import logging as _logging

        _MIN_WEEKLY_BARS = 5
        if len(df) // 5 < _MIN_WEEKLY_BARS:
            _logging.getLogger(__name__).debug(
                "quant1901_trend: panel has ~%d weekly bars (< %d); "
                "htf_regime falls back to 1.0 (bullish) — IC may be inflated on short panels",
                max(1, len(df) // 5),
                _MIN_WEEKLY_BARS,
            )

        from quant1901_executor import StrategyConfig, build_signal_frame  # type: ignore[import]

        frame = build_signal_frame(df, StrategyConfig())
        signal: pd.Series = frame["raw_signal"].astype(float)
        # Ensure the output index is a plain DatetimeIndex (no tz).
        signal.index = pd.DatetimeIndex(signal.index).tz_localize(None)
        signal.name = self.meta.name
        return signal


# ---------------------------------------------------------------------------
# Auto-register on import — mirrors the pattern used by technical.py, etc.
# ---------------------------------------------------------------------------
quant1901_trend_factor: Quant1901TrendFactor = register_factor(Quant1901TrendFactor())
