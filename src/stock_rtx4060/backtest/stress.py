"""Pre-canned historical stress scenarios.

Replays a strategy's daily return series across a fixed window of dates
(GFC, COVID crash, 2022 rate-shock).  Returns standard risk metrics.
"""

from __future__ import annotations

from math import sqrt

import pandas as pd

# Public scenario registry.  Each entry is (start, end) inclusive.
SCENARIOS: dict[str, tuple[str, str]] = {
    "gfc_2008": ("2008-09-01", "2009-03-31"),
    "covid_2020": ("2020-02-15", "2020-04-15"),
    "rates_2022": ("2022-01-01", "2022-10-15"),
}


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(abs(dd.min()))


def _annualized_sharpe(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    std = float(returns.std(ddof=0))
    if std <= 0.0:
        return 0.0
    return float(returns.mean() / std * sqrt(252.0))


def run_replay(
    strategy_returns: pd.Series,
    *,
    scenario: str,
) -> dict[str, float]:
    """Slice ``strategy_returns`` to ``SCENARIOS[scenario]`` and report metrics.

    Parameters
    ----------
    strategy_returns:
        Daily simple returns indexed by ``DatetimeIndex`` (or anything that
        ``pd.to_datetime`` can coerce).
    scenario:
        One of :data:`SCENARIOS`.

    Returns
    -------
    dict with keys ``period_return``, ``max_dd``, ``sharpe``, ``worst_day``,
    ``n_days``.  All floats; ``n_days`` is integer-valued.
    """
    if scenario not in SCENARIOS:
        raise KeyError(f"unknown scenario {scenario!r}; choose from {sorted(SCENARIOS)}")
    if not isinstance(strategy_returns, pd.Series):
        raise TypeError("strategy_returns must be a pandas Series")

    series = strategy_returns.copy()
    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)
    start, end = SCENARIOS[scenario]
    window = series.loc[start:end].dropna()

    n_days = int(len(window))
    if n_days == 0:
        return {
            "period_return": 0.0,
            "max_dd": 0.0,
            "sharpe": 0.0,
            "worst_day": 0.0,
            "n_days": 0,
        }
    equity = (1.0 + window).cumprod()
    period_return = float(equity.iloc[-1] - 1.0)
    max_dd = _max_drawdown(equity)
    sharpe = _annualized_sharpe(window)
    worst_day = float(window.min()) if not window.empty else 0.0
    return {
        "period_return": period_return,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "worst_day": worst_day,
        "n_days": n_days,
    }
