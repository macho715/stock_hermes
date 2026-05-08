"""Transaction-cost model and turnover penalty for Phase-4 portfolio optimisation.

The cost model intentionally separates *commission* and *spread* (both quoted in
basis points per side) so that exchange-specific commission tiers can be plugged
in without disturbing the spread model.  ``impact_lambda`` hooks a square-root
market-impact term but we keep it at zero by default — Phase 4 only ships the
linear cost terms.

The turnover-penalty helper is a pragmatic shrinkage step:  if the round-trip
cost of moving from ``weights_prev`` to ``weights_new`` exceeds the alpha we
expect to capture, we pull the new weights toward the previous weights along
the line segment between them.  The shrinkage factor is the closed-form
minimiser of ``||w - w_target||_2 + lambda * sum(|w - w_prev|) * cost``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TransactionCosts:
    """Linear transaction cost model in basis points (per side)."""

    commission_bps: float = 5.0
    spread_bps: float = 10.0
    impact_lambda: float = 0.0  # square-root impact coefficient — 0 disables impact

    @property
    def linear_bps_per_side(self) -> float:
        """Total linear cost in bps for one side of a trade (commission + half-spread*2)."""
        return float(self.commission_bps) + float(self.spread_bps)

    @property
    def linear_fraction_per_side(self) -> float:
        """Same as :pyattr:`linear_bps_per_side` but expressed as a unit fraction."""
        return self.linear_bps_per_side / 10_000.0


def _align(weights_prev: pd.Series, weights_new: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Align two weight series on the union of their tickers, filling missing with 0."""
    universe = weights_prev.index.union(weights_new.index)
    prev = weights_prev.reindex(universe, fill_value=0.0).astype(float)
    new = weights_new.reindex(universe, fill_value=0.0).astype(float)
    return prev, new


def turnover(weights_prev: pd.Series, weights_new: pd.Series) -> float:
    """L1 turnover (one-sided) between two weight vectors."""
    prev, new = _align(weights_prev, weights_new)
    return float(np.abs(new.values - prev.values).sum())


def cost_estimate(weights_prev: pd.Series, weights_new: pd.Series, costs: TransactionCosts) -> float:
    """Linear cost estimate for moving from ``weights_prev`` to ``weights_new`` (fraction)."""
    return float(turnover(weights_prev, weights_new) * costs.linear_fraction_per_side)


def apply_turnover_penalty(
    weights_prev: pd.Series,
    weights_new: pd.Series,
    costs: TransactionCosts,
    *,
    lambda_turnover: float = 1.0,
) -> pd.Series:
    """Shrink ``weights_new`` toward ``weights_prev`` proportionally to estimated cost.

    The optimisation problem we solve is

        minimise   ||w - weights_new||_2^2  +  lambda * cost(w, weights_prev)

    where ``cost`` is the linear transaction-cost estimate.  Along the segment
    between ``weights_prev`` and ``weights_new`` this admits a closed-form
    shrinkage parameter ``alpha`` in [0, 1] such that ``w = (1 - alpha) * prev +
    alpha * new``.  ``alpha = 0`` means "stay put" and ``alpha = 1`` means "go
    fully to the new target".

    With ``lambda_turnover == 0`` the function returns ``weights_new`` unchanged.
    With very large ``lambda_turnover`` the function returns ``weights_prev``.
    """
    if lambda_turnover < 0:
        raise ValueError("lambda_turnover must be non-negative")

    prev, new = _align(weights_prev, weights_new)
    delta = new.values - prev.values
    delta_norm_sq = float(np.dot(delta, delta))
    if delta_norm_sq <= 0.0:
        return new.copy()

    if lambda_turnover == 0.0:
        return new.copy()

    cost_per_full_move = float(np.abs(delta).sum() * costs.linear_fraction_per_side)
    # The unconstrained minimiser of ||(1-a)prev+a*new - new||^2 + lam*a*cost
    # along the segment is a* = max(0, 1 - lam*cost / (2 * ||delta||^2)).
    alpha = 1.0 - (lambda_turnover * cost_per_full_move) / (2.0 * delta_norm_sq)
    alpha = max(0.0, min(1.0, alpha))
    blended = (1.0 - alpha) * prev.values + alpha * new.values
    return pd.Series(blended, index=new.index, name=weights_new.name)
