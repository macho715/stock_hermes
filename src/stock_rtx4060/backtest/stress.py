"""Pre-canned historical stress scenarios and cost stress engine.

Replays a strategy's daily return series across a fixed window of dates
(GFC, COVID crash, 2022 rate-shock).  Returns standard risk metrics.

Also provides :func:`run_cost_stress` which re-runs a backtest at 1×/2×/3×
transaction cost and slippage to verify alpha survives realistic adverse
fee environments (v5.1 spec §5).
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


def run_cost_stress(
    backtester_cls: type,
    prices: pd.Series | list[float],
    signals: pd.Series | list[float],
    base_config: object,
    *,
    multipliers: tuple[int, ...] = (1, 2, 3),
) -> dict[str, object]:
    """Re-run backtest at 1x/2x/3x transaction cost and slippage.

    Parameters
    ----------
    backtester_cls:
        The ``Backtester`` class (passed to avoid circular import).
    prices, signals:
        Same inputs passed to ``Backtester.run()``.
    base_config:
        ``BacktestConfig`` dataclass instance with base cost/slippage.
    multipliers:
        Cost multipliers to evaluate.  Default ``(1, 2, 3)``.

    Returns
    -------
    Dict with keys:

    - ``"scenarios"``: per-multiplier results (total_return_pct, sharpe, n_trades)
    - ``"alpha_after_1x_cost"``, ``"alpha_after_2x_cost"``, ``"alpha_after_3x_cost"``
    - ``"cost_stress_status"``: ``"PASS"`` if 1x alpha > 0 and 3x alpha >= 0,
      else ``"AMBER"``

    The PASS condition follows v5.1 spec §5:
      alpha_after_1x_cost > 0  AND  alpha_after_3x_cost >= 0
    """
    import dataclasses

    scenarios: dict[str, dict] = {}
    for mult in multipliers:
        cfg_scaled = dataclasses.replace(
            base_config,
            transaction_cost=base_config.transaction_cost * mult,
            slippage=base_config.slippage * mult,
        )
        bt = backtester_cls(cfg_scaled).run(prices, signals)
        alpha = float(bt.get("total_return_pct", 0.0))
        scenarios[f"{mult}x"] = {
            "multiplier": mult,
            "transaction_cost": cfg_scaled.transaction_cost,
            "slippage": cfg_scaled.slippage,
            "total_return_pct": alpha,
            "sharpe_ratio": bt.get("sharpe_ratio"),
            "n_trades": bt.get("n_trades", 0),
        }

    alpha_1x = float(scenarios.get("1x", {}).get("total_return_pct", 0.0))
    alpha_3x = float(scenarios.get("3x", {}).get("total_return_pct", 0.0))
    status = "PASS" if alpha_1x > 0 and alpha_3x >= 0 else "AMBER"

    result: dict[str, object] = {
        "scenarios": scenarios,
        "cost_stress_status": status,
    }
    for mult in multipliers:
        result[f"alpha_after_{mult}x_cost"] = scenarios.get(f"{mult}x", {}).get("total_return_pct")
    return result
