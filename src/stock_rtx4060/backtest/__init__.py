"""Phase-5 backtest / risk hardening package.

Exposes Numba-accelerated parameter sweeps (vectorbt when present, pandas
fallback otherwise), Monte-Carlo block bootstraps, López de Prado statistical
tests, factor / Brinson risk attribution, and pre-canned stress replays.

All optional dependencies (vectorbt, statsmodels, arch) are guarded — pure
NumPy/SciPy paths must work when they are missing.
"""

from __future__ import annotations

from .mc_bootstrap import block_bootstrap, drawdown_bounds
from .msprt_monitor import MSPRTMonitor, msprt_log_likelihood_ratio
from .risk_attribution import brinson_attribution, factor_exposure_regression
from .stat_tests import deflated_sharpe, min_track_record_length, probabilistic_sharpe
from .stress import SCENARIOS, run_replay
from .vbt_sweep import run_vbt_sweep

__all__ = [
    "MSPRTMonitor",
    "SCENARIOS",
    "block_bootstrap",
    "brinson_attribution",
    "deflated_sharpe",
    "drawdown_bounds",
    "factor_exposure_regression",
    "min_track_record_length",
    "msprt_log_likelihood_ratio",
    "probabilistic_sharpe",
    "run_replay",
    "run_vbt_sweep",
]
