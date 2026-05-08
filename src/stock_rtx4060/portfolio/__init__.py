"""Phase-4 portfolio optimisation package.

Exports the user-facing API only.  Optional dependencies (``skfolio``,
``PyPortfolioOpt``, ``cvxpy``) are loaded lazily inside :mod:`optimizer` so
importing this package never raises when those libraries are missing.
"""

from __future__ import annotations

from .costs import TransactionCosts, apply_turnover_penalty
from .optimizer import Method, optimize
from .rebalance import TradeOrder, compute_target_weights
from .views import LLMViews, ViewItem, to_black_litterman_inputs

__all__ = [
    "LLMViews",
    "Method",
    "TradeOrder",
    "TransactionCosts",
    "ViewItem",
    "apply_turnover_penalty",
    "compute_target_weights",
    "optimize",
    "to_black_litterman_inputs",
]
