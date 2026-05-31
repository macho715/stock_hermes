"""Thin wrapper around quant1901_executor for integration into stock_rtx4060.

Strategy A: import-based wrapper — adds the bundle to sys.path and delegates
all signal/backtest logic to quant1901_executor without copying code.

Usage::

    from stock_rtx4060.strategies.quant1901_strategy import Quant1901Strategy
    strategy = Quant1901Strategy()
    result = strategy.run(ohlcv_df)   # returns metrics dict
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Bundle path resolution — works whether the repo root is on sys.path or not
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
# src/stock_rtx4060/strategies/quant1901_strategy.py → repo root is 3 levels up
_REPO_ROOT = _THIS_FILE.parents[3]
BUNDLE_PATH = str(_REPO_ROOT / "quant1901_executable_bundle")

if BUNDLE_PATH not in sys.path:
    sys.path.insert(0, BUNDLE_PATH)

# ---------------------------------------------------------------------------
# Lazy imports — only resolve after sys.path is patched
# ---------------------------------------------------------------------------
from quant1901_executor import (  # noqa: E402  (must come after sys.path patch)
    RiskLimits,
    StrategyConfig,
    build_signal_frame,
    make_synthetic_ohlcv,
    run_backtest,
)

__all__ = [
    "Quant1901Strategy",
    "BUNDLE_PATH",
    "StrategyConfig",
    "RiskLimits",
    "build_signal_frame",
    "run_backtest",
    "make_synthetic_ohlcv",
]

_OHLCV_RENAME = {
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "volume": "Volume",
}


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *df* with OHLCV columns in Title-Case.

    quant1901_executor expects 'Close', 'Open', etc.  This helper accepts
    both lowercase and title-case column names so callers don't need to
    worry about convention.
    """
    rename = {k: v for k, v in _OHLCV_RENAME.items() if k in df.columns}
    if rename:
        return df.rename(columns=rename)
    return df


class Quant1901Strategy:
    """Paper/backtest-only strategy wrapper around quant1901_executor.

    Parameters
    ----------
    config:
        StrategyConfig instance.  Defaults to quant1901_executor defaults.
    risk:
        RiskLimits instance.  Defaults to quant1901_executor defaults.
    """

    def __init__(
        self,
        config: StrategyConfig | None = None,
        risk: RiskLimits | None = None,
    ) -> None:
        self.config: StrategyConfig = config if config is not None else StrategyConfig()
        self.risk: RiskLimits = risk if risk is not None else RiskLimits()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, ohlcv_df: pd.DataFrame) -> dict[str, Any]:
        """Run backtest and return the metrics dict.

        Parameters
        ----------
        ohlcv_df:
            OHLCV DataFrame.  Column names may be lowercase or title-case.
            Index must be a DatetimeIndex (or castable to one).

        Returns
        -------
        dict
            Metrics dict from quant1901_executor.calculate_metrics, which
            always contains ``mode == 'paper_backtest_only'`` and
            ``execution_guard['live_orders_enabled'] == False``.
        """
        df = _normalize_ohlcv(ohlcv_df.copy())

        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        result = run_backtest(df, self.config, self.risk)
        return result.metrics

    def signal_frame(self, ohlcv_df: pd.DataFrame) -> pd.DataFrame:
        """Return the intermediate signal frame (for inspection / plotting)."""
        df = _normalize_ohlcv(ohlcv_df.copy())
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        return build_signal_frame(df, self.config)
