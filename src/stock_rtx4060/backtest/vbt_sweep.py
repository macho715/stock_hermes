"""Vectorbt-accelerated parameter sweep with pandas fallback.

Implements a grid runner for moving-average / stop-loss style strategies on
panel data (one column per ticker).  When ``vectorbt`` is installed the
Numba-accelerated ``Portfolio.from_signals`` engine is used; otherwise the
function falls back to a pure-pandas equivalent so tests pass and developers
without the optional dep can still iterate.

The top 10 parameter combinations by Sharpe are logged to MLflow via
:class:`stock_rtx4060.observability.MLflowSession`.
"""

from __future__ import annotations

import itertools
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd

from ..observability import MLflowSession, log_metrics, log_params

try:  # vectorbt is optional.  When missing we silently fall back.
    import vectorbt as vbt  # type: ignore[import-not-found]

    _HAS_VBT = True
except Exception:  # pragma: no cover - tested only when vbt installed
    vbt = None  # type: ignore[assignment]
    _HAS_VBT = False


_DEFAULT_GRID_KEYS = ("ma_window", "stop_pct")


def _coerce_prices(prices: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(prices, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame")
    if prices.shape[1] == 0:
        raise ValueError("prices has no columns")
    df = prices.astype(float).ffill().dropna(how="all")
    if df.empty:
        raise ValueError("prices empty after ffill/dropna")
    return df


def _expand_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not grid:
        raise ValueError("grid must contain at least one parameter")
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*values)]


def _max_drawdown(equity: np.ndarray) -> float:
    if equity.size == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    return float(abs(dd.min()))


def _annualized_sharpe(returns: np.ndarray) -> float:
    if returns.size == 0:
        return 0.0
    std = float(np.std(returns, ddof=0))
    if std <= 0.0:
        return 0.0
    return float(np.mean(returns) / std * sqrt(252.0))


def _pandas_run_one(
    prices: pd.DataFrame,
    *,
    ma_window: int,
    stop_pct: float,
    fees: float,
    slippage: float,
) -> dict[str, float]:
    """Equal-weight long-only MA-crossover with hard stop-loss; pandas only.

    Each ticker is sized at ``1 / n_tickers`` of capital when its signal is
    on.  The strategy enters when ``price > MA(window)`` and exits when it
    breaks back below the MA or hits the stop.
    """
    p = prices.copy()
    n_tickers = p.shape[1]
    ma = p.rolling(window=int(ma_window), min_periods=int(ma_window)).mean()
    long_signal = (p > ma).astype(float)

    n_trades = 0
    holdings = np.zeros(n_tickers, dtype=float)
    entry_price = np.full(n_tickers, np.nan)
    cash = 1.0
    weights = np.full(n_tickers, 1.0 / n_tickers)
    prev_holding = np.zeros(n_tickers, dtype=bool)
    equity = []
    prices_arr = p.to_numpy()
    sig_arr = long_signal.fillna(0.0).to_numpy()

    for t in range(len(p)):
        px = prices_arr[t]
        # Mark-to-market value of holdings using current prices.
        position_value = float(np.nansum(holdings * px))
        nav = cash + position_value

        # Determine target on/off vector (long_signal active and not stopped).
        wanted = sig_arr[t] > 0.5
        # Stop-loss check: drop tickers whose drawdown exceeds stop_pct.
        held = ~np.isnan(entry_price)
        if held.any():
            dd = (px - entry_price) / np.where(entry_price > 0, entry_price, 1.0)
            stop_hit = held & (dd <= -float(stop_pct))
            wanted = wanted & ~stop_hit

        # Rebalance to target weights when the on/off vector changed.
        if not np.array_equal(wanted, prev_holding):
            # Liquidate everything first, account for fees + slippage.
            if held.any():
                gross = float(np.sum(holdings * px))
                cash += gross * (1.0 - float(fees) - float(slippage))
                # Count trades whenever we drop a position.
                n_trades += int(np.sum(prev_holding & ~wanted))
                holdings[:] = 0.0
                entry_price[:] = np.nan
            # Allocate to wanted tickers.
            n_long = int(wanted.sum())
            if n_long > 0:
                alloc = cash / n_long
                buy_cost = 1.0 + float(fees) + float(slippage)
                for j in np.where(wanted)[0]:
                    if px[j] <= 0 or not np.isfinite(px[j]):
                        continue
                    qty = alloc / (px[j] * buy_cost)
                    holdings[j] = qty
                    entry_price[j] = px[j] * buy_cost
                    n_trades += 1
                cash = 0.0
            prev_holding = wanted.copy()

        # Recompute NAV after rebalance.
        nav = cash + float(np.nansum(holdings * px))
        equity.append(nav)

    equity_arr = np.asarray(equity, dtype=float)
    returns = np.diff(equity_arr) / np.where(equity_arr[:-1] > 0, equity_arr[:-1], 1.0)
    total_return = float(equity_arr[-1] - 1.0) if equity_arr.size else 0.0
    return {
        "total_return": total_return,
        "sharpe": _annualized_sharpe(returns),
        "max_dd": _max_drawdown(equity_arr),
        "n_trades": float(n_trades),
        "engine": "pandas",
        # weights and nav are unused; kept for future enrichment
        **{"_weights_used": float(weights.sum())},
    }


def _vbt_run_one(
    prices: pd.DataFrame,
    *,
    ma_window: int,
    stop_pct: float,
    fees: float,
    slippage: float,
) -> dict[str, float]:  # pragma: no cover - exercised only when vbt installed
    fast_ma = vbt.MA.run(prices, window=int(ma_window))
    entries = prices > fast_ma.ma
    exits = prices < fast_ma.ma
    pf = vbt.Portfolio.from_signals(
        prices,
        entries.fillna(False),
        exits.fillna(False),
        fees=float(fees),
        slippage=float(slippage),
        sl_stop=float(stop_pct),
        freq="1D",
    )
    total_return = float(np.nanmean(pf.total_return().to_numpy()))
    sharpe = float(np.nanmean(pf.sharpe_ratio().to_numpy()))
    max_dd = float(np.nanmax(np.abs(pf.max_drawdown().to_numpy())))
    n_trades = float(np.nansum(pf.trades.count().to_numpy()))
    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "n_trades": n_trades,
        "engine": "vectorbt",
    }


def run_vbt_sweep(
    prices: pd.DataFrame,
    *,
    grid: dict[str, list[Any]],
    fees: float = 0.001,
    slippage: float = 0.0005,
    experiment: str = "vbt_sweep",
) -> pd.DataFrame:
    """Run a parameter-grid sweep and log the top 10 by Sharpe to MLflow.

    Parameters
    ----------
    prices:
        Wide DataFrame of close prices; columns are ticker symbols.
    grid:
        Mapping ``param_name -> list of values``.  Recognised parameters
        are ``ma_window`` (int) and ``stop_pct`` (float).  Other keys are
        accepted, recorded, but ignored by the runner so the API remains
        forward-compatible.
    fees, slippage:
        Per-trade transaction cost and slippage (fractions of notional).
    experiment:
        MLflow experiment name.

    Returns
    -------
    DataFrame: one row per parameter combination, columns include the grid
    parameters plus ``total_return``, ``sharpe``, ``max_dd``, ``n_trades``,
    and ``engine``.

    Notes
    -----
    When ``vectorbt`` is unavailable the runner falls back to a pure-pandas
    equal-weight MA-crossover with hard stop-loss.  Results between the two
    paths will not match exactly; the fallback is for portability and tests.
    """
    p = _coerce_prices(prices)
    combos = _expand_grid(grid)

    rows: list[dict[str, Any]] = []
    for params in combos:
        ma_window = int(params.get("ma_window", 20))
        stop_pct = float(params.get("stop_pct", 0.05))
        if _HAS_VBT:
            metrics = _vbt_run_one(p, ma_window=ma_window, stop_pct=stop_pct, fees=fees, slippage=slippage)
        else:
            metrics = _pandas_run_one(p, ma_window=ma_window, stop_pct=stop_pct, fees=fees, slippage=slippage)
        rows.append({**params, **metrics})

    df = pd.DataFrame(rows)
    # Replace NaN sharpe with -inf so the top-10 selection is well-defined.
    df["sharpe"] = df["sharpe"].replace([np.inf, -np.inf], np.nan).fillna(-np.inf)

    # MLflow logging — top-10 only, one nested run per combo.
    top10 = df.sort_values("sharpe", ascending=False).head(10)
    with MLflowSession(experiment, run_name="vbt_sweep_top10") as run:  # noqa: F841
        log_params({"engine": "vectorbt" if _HAS_VBT else "pandas", "n_combos": len(df)})
        for i, row in enumerate(top10.itertuples(index=False)):
            row_dict = row._asdict()
            log_metrics(
                {
                    f"top{i + 1}_sharpe": float(row_dict.get("sharpe", 0.0)),
                    f"top{i + 1}_total_return": float(row_dict.get("total_return", 0.0)),
                    f"top{i + 1}_max_dd": float(row_dict.get("max_dd", 0.0)),
                    f"top{i + 1}_n_trades": float(row_dict.get("n_trades", 0.0)),
                }
            )
    # Restore -inf to NaN for downstream readability.
    df["sharpe"] = df["sharpe"].replace(-np.inf, np.nan)
    return df
