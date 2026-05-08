"""
Risk-first event backtester with fractional Kelly and fixed-risk sizing.

This module intentionally remains broker-free.  It simulates market orders from
model probabilities, transaction costs, slippage, stop loss, take profit, and a
monthly Track-S loss stop.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Literal

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost: float = 0.001
    slippage: float = 0.0005
    max_position_pct: float = 0.25
    min_position_pct: float = 0.02
    kelly_fraction: float = 0.25
    risk_per_trade_pct: float = 0.0075
    max_monthly_loss_pct: float = 0.05
    monthly_stop_pct: float | None = None
    threshold_buy: float = 0.56
    threshold_sell: float = 0.45
    stop_loss_pct: float = 0.04
    take_profit_pct: float = 0.10
    allow_fractional_shares: bool = True
    min_trade_value: float = 100.0
    sizing: Literal["kelly", "hrp", "mv_cvar", "risk_budgeting"] = "kelly"
    sizing_lookback: int = 252
    # Phase-5 advanced statistics (off by default — preserves all existing tests).
    compute_advanced_stats: bool = False
    advanced_stats_n_trials: int = 1
    advanced_stats_mc_paths: int = 1_000
    advanced_stats_mc_block: int = 20
    advanced_stats_seed: int | None = 7

    def __post_init__(self) -> None:
        if self.monthly_stop_pct is not None:
            self.max_monthly_loss_pct = abs(float(self.monthly_stop_pct))


@dataclass
class Trade:
    entry_idx: int
    exit_idx: int | None
    entry_price: float
    exit_price: float | None
    quantity: float
    entry_value: float
    exit_value: float | None
    pnl: float | None
    pnl_pct: float | None
    exit_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_idx": self.entry_idx,
            "exit_idx": self.exit_idx,
            "entry_price": round(self.entry_price, 6),
            "exit_price": None if self.exit_price is None else round(self.exit_price, 6),
            "quantity": round(self.quantity, 6),
            "entry_value": round(self.entry_value, 2),
            "exit_value": None if self.exit_value is None else round(self.exit_value, 2),
            "pnl": None if self.pnl is None else round(self.pnl, 2),
            "pnl_pct": None if self.pnl_pct is None else round(self.pnl_pct * 100.0, 2),
            "exit_reason": self.exit_reason,
        }


class BacktestResult(dict):
    """Dictionary result with attribute and ``to_dict`` compatibility."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return dict(self)


class KellyCriterion:
    """Bayesian-smoothed fractional Kelly position fraction."""

    def __init__(self, fraction: float = 0.25, prior_wins: float = 2.0, prior_losses: float = 2.0):
        if fraction <= 0:
            raise ValueError("fraction must be positive")
        self.fraction = fraction
        self.prior_wins = prior_wins
        self.prior_losses = prior_losses
        self._wins: list[float] = []
        self._losses: list[float] = []

    def update(self, pnl_pct: float) -> None:
        if pnl_pct > 0:
            self._wins.append(float(pnl_pct))
        elif pnl_pct < 0:
            self._losses.append(abs(float(pnl_pct)))

    def kelly_pct(self) -> float:
        n_wins = len(self._wins)
        n_losses = len(self._losses)
        if n_wins + n_losses < 8:
            return 0.10

        win_rate = (n_wins + self.prior_wins) / (n_wins + n_losses + self.prior_wins + self.prior_losses)
        avg_win = float(np.mean(self._wins)) if self._wins else 0.01
        avg_loss = float(np.mean(self._losses)) if self._losses else 0.01
        if avg_loss <= 0 or avg_win <= 0:
            return 0.01

        odds = avg_win / avg_loss
        raw = win_rate - (1.0 - win_rate) / odds
        return max(0.01, min(self.fraction * raw, 0.25))


def _as_float_series(values: pd.Series | np.ndarray | list[float], name: str) -> pd.Series:
    series = pd.Series(values, copy=True) if not isinstance(values, pd.Series) else values.copy()
    series = pd.to_numeric(series, errors="coerce").astype(float)
    if series.isna().any():
        raise ValueError(f"{name} contains NaN or non-numeric values")
    return series


class Backtester:
    """Long-only probability-threshold backtester.

    Position size is the minimum of:
    - fractional Kelly capital budget;
    - fixed risk budget divided by stop distance;
    - max position value cap.
    """

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()
        self.kelly = KellyCriterion(self.config.kelly_fraction)

    def run(self, prices: pd.Series | np.ndarray | list[float], signals: pd.Series | np.ndarray | list[float]) -> dict[str, Any]:
        cfg = self.config
        price_s = _as_float_series(prices, "prices")
        signal_s = _as_float_series(signals, "signals")
        if len(price_s) != len(signal_s):
            raise ValueError("prices and signals must have the same length")
        if len(price_s) < 2:
            raise ValueError("at least two prices are required")
        if (price_s <= 0).any():
            raise ValueError("all prices must be positive")

        original_index = price_s.index
        prices_arr = price_s.reset_index(drop=True)
        signals_arr = signal_s.reset_index(drop=True).clip(0.0, 1.0)
        # Pre-compute single-asset returns for rolling-window optimiser sizing.
        returns_arr = price_s.pct_change().fillna(0.0).reset_index(drop=True)

        cash = float(cfg.initial_capital)
        quantity = 0.0
        entry_price = 0.0
        entry_value = 0.0
        entry_idx: int | None = None
        month_start_equity = cash
        active_month = self._month_key(original_index[0])
        monthly_stopped = False
        monthly_stop_ever = False
        trades: list[Trade] = []
        equity_curve: list[float] = []
        exposure_count = 0

        def mark_to_market(px: float) -> float:
            return cash + quantity * px

        for i, (price, signal) in enumerate(zip(prices_arr, signals_arr, strict=True)):
            month_key = self._month_key(original_index[i])
            if month_key != active_month:
                active_month = month_key
                month_start_equity = mark_to_market(float(price))
                monthly_stopped = False

            price = float(price)
            signal = float(signal)

            # Exit first.  Stop is checked before take-profit when both could occur.
            if quantity > 0:
                exposure_count += 1
                pnl_pct_mark = (price - entry_price) / entry_price
                exit_reason: str | None = None
                if pnl_pct_mark <= -cfg.stop_loss_pct:
                    exit_reason = "STOP_LOSS"
                elif pnl_pct_mark >= cfg.take_profit_pct:
                    exit_reason = "TAKE_PROFIT"
                elif signal <= cfg.threshold_sell:
                    exit_reason = "SIGNAL_REVERSAL"

                if exit_reason:
                    sell_fill = price * (1.0 - cfg.slippage)
                    gross = quantity * sell_fill
                    fee = gross * cfg.transaction_cost
                    exit_value = gross - fee
                    cash += exit_value
                    pnl = exit_value - entry_value
                    pnl_pct = pnl / entry_value if entry_value else 0.0
                    self.kelly.update(pnl_pct)
                    trades.append(
                        Trade(
                            entry_idx=entry_idx if entry_idx is not None else i,
                            exit_idx=i,
                            entry_price=entry_price,
                            exit_price=sell_fill,
                            quantity=quantity,
                            entry_value=entry_value,
                            exit_value=exit_value,
                            pnl=pnl,
                            pnl_pct=pnl_pct,
                            exit_reason=exit_reason,
                        )
                    )
                    quantity = 0.0
                    entry_price = 0.0
                    entry_value = 0.0
                    entry_idx = None

            equity = mark_to_market(price)
            if month_start_equity > 0 and (equity / month_start_equity - 1.0) <= -cfg.max_monthly_loss_pct:
                monthly_stopped = True
                monthly_stop_ever = True

            # Entry after exits and monthly stop gate.
            if quantity == 0 and not monthly_stopped and signal >= cfg.threshold_buy:
                buy_fill = price * (1.0 + cfg.slippage)
                if cfg.sizing == "kelly":
                    kelly_pct = max(cfg.min_position_pct, min(self.kelly.kelly_pct(), cfg.max_position_pct))
                else:
                    kelly_pct = self._optimizer_position_pct(returns_arr, i, cfg)
                max_by_cap = cash * kelly_pct / (buy_fill * (1.0 + cfg.transaction_cost))
                max_by_position = cfg.initial_capital * cfg.max_position_pct / buy_fill
                stop_distance = max(buy_fill * cfg.stop_loss_pct, 1e-12)
                max_by_risk = equity * cfg.risk_per_trade_pct / stop_distance
                desired_quantity = min(max_by_cap, max_by_position, max_by_risk)
                if not cfg.allow_fractional_shares:
                    desired_quantity = float(np.floor(desired_quantity))
                gross = desired_quantity * buy_fill
                fee = gross * cfg.transaction_cost
                total_cost = gross + fee
                if desired_quantity > 0 and total_cost >= cfg.min_trade_value and total_cost <= cash:
                    cash -= total_cost
                    quantity = desired_quantity
                    entry_price = buy_fill
                    entry_value = total_cost
                    entry_idx = i

            equity_curve.append(mark_to_market(price))

        # Final liquidation for accurate final capital and trade accounting.
        if quantity > 0:
            final_i = len(prices_arr) - 1
            final_price = float(prices_arr.iloc[-1]) * (1.0 - cfg.slippage)
            gross = quantity * final_price
            fee = gross * cfg.transaction_cost
            exit_value = gross - fee
            cash += exit_value
            pnl = exit_value - entry_value
            pnl_pct = pnl / entry_value if entry_value else 0.0
            self.kelly.update(pnl_pct)
            trades.append(
                Trade(
                    entry_idx=entry_idx if entry_idx is not None else final_i,
                    exit_idx=final_i,
                    entry_price=entry_price,
                    exit_price=final_price,
                    quantity=quantity,
                    entry_value=entry_value,
                    exit_value=exit_value,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    exit_reason="FINAL_LIQUIDATION",
                )
            )
            equity_curve[-1] = cash

        equity_s = pd.Series(equity_curve, index=original_index[: len(equity_curve)], dtype=float)
        returns = equity_s.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
        total_return = cash / cfg.initial_capital - 1.0
        mdd = self._max_drawdown(equity_s)
        sharpe = self._annualized_sharpe(returns)
        sortino = self._annualized_sortino(returns)
        calmar = (total_return / mdd) if mdd > 0 else 0.0
        completed = [t for t in trades if t.pnl is not None]
        wins = [t for t in completed if (t.pnl or 0.0) > 0]
        losses = [t for t in completed if (t.pnl or 0.0) < 0]
        gross_profit = sum(t.pnl or 0.0 for t in wins)
        gross_loss = abs(sum(t.pnl or 0.0 for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
        avg_pnl_pct = float(np.mean([t.pnl_pct for t in completed if t.pnl_pct is not None])) if completed else 0.0

        win_rate = round((len(wins) / len(completed) * 100.0) if completed else 0.0, 2)
        deflated_sr, psr_vs_zero, mc_dd_p95 = self._maybe_advanced_stats(returns, sharpe)
        result = BacktestResult({
            "total_return_pct": round(total_return * 100.0, 2),
            "annualized_return_pct": round(((1.0 + total_return) ** (252 / max(1, len(prices_arr))) - 1.0) * 100.0, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "calmar_ratio": round(calmar, 3),
            "max_drawdown_pct": round(mdd * 100.0, 2),
            "win_rate": win_rate,
            "win_rate_pct": win_rate,
            "n_trades": len(completed),
            "profit_factor": round(profit_factor, 3) if np.isfinite(profit_factor) else "inf",
            "expectancy_pct": round(avg_pnl_pct * 100.0, 3),
            "exposure_pct": round(exposure_count / len(prices_arr) * 100.0, 2),
            "final_capital": round(cash, 2),
            "monthly_stop_triggered": monthly_stop_ever,
            "portfolio_values": [round(float(x), 4) for x in equity_s.tolist()],
            "trades": [t.to_dict() for t in completed],
            # Phase-5 advanced stats — None unless `compute_advanced_stats=True`.
            "deflated_sharpe": deflated_sr,
            "psr_vs_zero": psr_vs_zero,
            "mc_drawdown_p95": mc_dd_p95,
        })
        return result

    def _maybe_advanced_stats(
        self, returns: pd.Series, sharpe: float
    ) -> tuple[float | None, float | None, float | None]:
        """Compute Phase-5 advanced statistics when enabled.

        Returns ``(deflated_sharpe, psr_vs_zero, mc_drawdown_p95)`` — all
        ``None`` when the feature flag is off, preserving the legacy schema.
        """
        cfg = self.config
        if not getattr(cfg, "compute_advanced_stats", False):
            return None, None, None
        try:
            from .backtest.mc_bootstrap import drawdown_bounds
            from .backtest.stat_tests import deflated_sharpe, probabilistic_sharpe
        except Exception:  # pragma: no cover - defensive
            return None, None, None
        clean = returns.replace([np.inf, -np.inf], np.nan).dropna()
        n_obs = int(len(clean))
        if n_obs < 5:
            return None, None, None
        # SR is annualized in `sharpe`; convert back to per-period for PSR/DSR.
        sr_per_period = sharpe / sqrt(252.0) if sharpe else 0.0
        try:
            skew_val = float(clean.skew()) if n_obs >= 3 else 0.0
            kurt_val = float(clean.kurt() + 3.0) if n_obs >= 4 else 3.0
            psr = float(probabilistic_sharpe(sr_per_period, 0.0, n_obs=n_obs, skew=skew_val, kurt=kurt_val))
            dsr = float(
                deflated_sharpe(
                    sr_per_period,
                    n_trials=int(getattr(cfg, "advanced_stats_n_trials", 1)),
                    skew=skew_val,
                    kurt=kurt_val,
                    n_obs=n_obs,
                )
            )
        except Exception:  # pragma: no cover - defensive
            psr = None
            dsr = None
        try:
            bounds = drawdown_bounds(
                clean,
                block_size=int(getattr(cfg, "advanced_stats_mc_block", 20)),
                n_paths=int(getattr(cfg, "advanced_stats_mc_paths", 1_000)),
                seed=getattr(cfg, "advanced_stats_seed", None),
            )
            mc_p95 = float(bounds["p95_max_dd"])
        except Exception:  # pragma: no cover - defensive
            mc_p95 = None
        return dsr, psr, mc_p95

    def _optimizer_position_pct(self, returns_arr: pd.Series, i: int, cfg: BacktestConfig) -> float:
        """Compute a single-asset position fraction using the portfolio optimiser.

        For a single-name backtester the optimiser is degenerate (one ticker), so
        we use a synthetic two-asset universe (the asset itself and a flat
        cash-like leg) to obtain a meaningful target weight, then bound it by
        ``[min_position_pct, max_position_pct]``.  On any failure we fall back
        to fractional-Kelly sizing — preserving the existing behaviour.
        """
        try:
            from .portfolio.optimizer import optimize  # local import — optional dep
        except Exception:
            return max(cfg.min_position_pct, min(self.kelly.kelly_pct(), cfg.max_position_pct))

        lookback = max(20, int(cfg.sizing_lookback))
        start = max(0, i - lookback)
        window = returns_arr.iloc[start:i]
        if len(window) < 20:
            return max(cfg.min_position_pct, min(self.kelly.kelly_pct(), cfg.max_position_pct))

        # Build a 2-asset frame: the asset's returns and a constant 0% "cash" leg.
        # The optimiser allocates risk between the two; the asset weight becomes
        # our target position fraction.
        df = pd.DataFrame({"asset": window.values, "cash": np.zeros(len(window))})
        # Add tiny noise to cash to avoid singular covariance.
        df["cash"] = 1e-8 * np.random.default_rng(0).standard_normal(len(window))
        try:
            weights = optimize(
                df,
                method=cfg.sizing,
                max_weight=cfg.max_position_pct,
                min_weight=0.0,
                seed=42,
            )
        except Exception:
            return max(cfg.min_position_pct, min(self.kelly.kelly_pct(), cfg.max_position_pct))
        if weights is None or weights.empty or "asset" not in weights.index:
            return max(cfg.min_position_pct, min(self.kelly.kelly_pct(), cfg.max_position_pct))
        target = float(weights.loc["asset"])
        return max(cfg.min_position_pct, min(target, cfg.max_position_pct))

    @staticmethod
    def _month_key(value: Any) -> str:
        try:
            ts = pd.Timestamp(value)
            if pd.isna(ts):
                return "na"
            return f"{ts.year:04d}-{ts.month:02d}"
        except Exception:
            return "na"

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        peak = equity.cummax()
        dd = equity / peak - 1.0
        return abs(float(dd.min())) if len(dd) else 0.0

    @staticmethod
    def _annualized_sharpe(returns: pd.Series) -> float:
        std = float(returns.std(ddof=0)) if len(returns) else 0.0
        if std <= 0:
            return 0.0
        return float(returns.mean() / std * sqrt(252.0))

    @staticmethod
    def _annualized_sortino(returns: pd.Series) -> float:
        downside = returns[returns < 0.0]
        downside_std = float(downside.std(ddof=0)) if len(downside) else 0.0
        if downside_std <= 0:
            return 0.0
        return float(returns.mean() / downside_std * sqrt(252.0))
