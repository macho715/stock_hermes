"""Translate a target-weight vector into a list of :class:`TradeOrder`.

This is the bridge between the optimisation layer (which yields a target
weight vector summing to 1) and the execution layer (which needs concrete
buy/sell orders denominated in dollars).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .costs import TransactionCosts


@dataclass
class TradeOrder:
    ticker: str
    side: Literal["BUY", "SELL"]
    quantity: float
    target_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "side": self.side,
            "quantity": round(float(self.quantity), 6),
            "target_value": round(float(self.target_value), 2),
        }


def compute_target_weights(
    candidates: list[dict[str, Any]],
    current_positions: dict[str, float],
    portfolio_value: float,
    *,
    costs: TransactionCosts | None = None,
    min_trade_value: float = 100.0,
) -> list[TradeOrder]:
    """Compute the trades that move from ``current_positions`` to the candidates.

    Parameters
    ----------
    candidates:
        List of dicts with at least ``ticker`` and ``target_weight`` keys.
        Optional ``score`` and ``price`` keys are passed through.  The
        ``target_weight`` values are normalised internally so they need not sum
        exactly to 1.
    current_positions:
        Mapping of ticker to current dollar value held in the portfolio.
    portfolio_value:
        Total portfolio market value (cash + positions) used to translate
        weights to dollar targets.
    costs:
        Optional :class:`TransactionCosts`.  When provided we suppress trades
        whose absolute dollar move is below the cost-adjusted threshold.
    min_trade_value:
        Minimum absolute dollar value below which a trade is dropped.
    """
    if portfolio_value <= 0:
        return []

    # Build target dollar map (normalised weights)
    raw_weight_total = sum(max(0.0, float(c.get("target_weight", 0.0))) for c in candidates)
    target_value: dict[str, float] = {}
    if raw_weight_total > 0:
        for c in candidates:
            ticker = str(c["ticker"])
            w = max(0.0, float(c.get("target_weight", 0.0))) / raw_weight_total
            target_value[ticker] = w * float(portfolio_value)

    # Establish full universe so that names that are currently held but no
    # longer in candidates get a SELL to zero.
    universe: set[str] = set(target_value.keys()) | set(current_positions.keys())

    cost_floor = float(min_trade_value)
    if costs is not None:
        # Add commission/spread floor: do not bother trading if the cost would
        # be a meaningful fraction of the move.
        cost_floor = max(cost_floor, costs.linear_fraction_per_side * float(portfolio_value) * 0.5)

    orders: list[TradeOrder] = []
    for ticker in sorted(universe):
        current = float(current_positions.get(ticker, 0.0))
        target = float(target_value.get(ticker, 0.0))
        delta = target - current
        if abs(delta) < cost_floor:
            continue
        # Use price from candidate if present, else assume $1 per "share" so
        # quantity is in dollars.  (The dashboard layer can convert later.)
        price = 0.0
        for c in candidates:
            if str(c.get("ticker")) == ticker:
                price = float(c.get("price", 0.0))
                break
        if price > 0:
            qty = abs(delta) / price
        else:
            qty = abs(delta)
        side: Literal["BUY", "SELL"] = "BUY" if delta > 0 else "SELL"
        orders.append(TradeOrder(ticker=ticker, side=side, quantity=qty, target_value=target))
    return orders
