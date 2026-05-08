"""Black-Litterman view translation from LLM advisory scores.

Mapping rule
------------
Each ``ViewItem`` carries an ``advisory_score`` in ``[-1, +1]`` and a
``confidence`` in ``[0, 1]``.  We turn it into an *absolute* Black-Litterman
view on the ticker's expected excess return as follows::

    Q[i]        = advisory_score[i] * absolute_view_max
    Omega[i, i] = (1 - confidence[i]) * |Q[i]|^2 + 1e-8
    P[i, j]     = 1 if j == ticker[i] else 0

A confidence of ``1.0`` produces a tight ``Omega`` (only the floor 1e-8) which
nails the posterior toward the view; a confidence of ``0.0`` produces a wide
``Omega`` so the posterior follows the prior.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ..advisors.base import AdvisoryOutput


@dataclass
class ViewItem:
    ticker: str
    advisory_score: float  # in [-1, +1]
    confidence: float  # in [0, 1]


@dataclass
class LLMViews:
    """A list of LLM-derived advisory views, one per ticker."""

    items: list[ViewItem] = field(default_factory=list)

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def tickers(self) -> list[str]:
        return [v.ticker for v in self.items]

    @classmethod
    def from_advisory_outputs(cls, outputs: Iterable[AdvisoryOutput]) -> LLMViews:
        """Build an :class:`LLMViews` from advisor outputs.

        Each :class:`AdvisoryOutput` becomes a :class:`ViewItem` with the
        same ticker, ``advisory_score = output.score`` and
        ``confidence = output.confidence``.
        """
        items: list[ViewItem] = []
        for out in outputs:
            items.append(
                ViewItem(
                    ticker=str(getattr(out, "ticker", "")),
                    advisory_score=float(getattr(out, "score", 0.0)),
                    confidence=float(getattr(out, "confidence", 0.0)),
                )
            )
        return cls(items=items)


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def to_black_litterman_inputs(
    views: LLMViews,
    prior_returns: pd.Series,
    *,
    absolute_view_max: float = 0.05,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Translate LLM advisory views into Black-Litterman ``(P, Q, Omega)`` arrays.

    Parameters
    ----------
    views:
        An :class:`LLMViews` instance.  Tickers absent from ``prior_returns``
        are silently dropped (they have no asset slot in the prior universe).
    prior_returns:
        The prior expected-returns vector indexed by ticker.  Used only for
        index alignment — values are not consumed.
    absolute_view_max:
        Clipping bound on the absolute return view, in decimal form
        (``0.05`` ⇒ ±5% absolute).
    """
    if absolute_view_max <= 0:
        raise ValueError("absolute_view_max must be positive")

    n_assets = len(prior_returns)
    valid_views = [v for v in views.items if v.ticker in prior_returns.index]

    p = np.zeros((len(valid_views), n_assets), dtype=float)
    q = np.zeros(len(valid_views), dtype=float)
    omega_diag = np.zeros(len(valid_views), dtype=float)

    ticker_to_idx = {ticker: i for i, ticker in enumerate(prior_returns.index)}
    for row, view in enumerate(valid_views):
        score = _clip(view.advisory_score, -1.0, 1.0)
        confidence = _clip(view.confidence, 0.0, 1.0)
        col = ticker_to_idx[view.ticker]
        p[row, col] = 1.0
        q[row] = score * absolute_view_max
        omega_diag[row] = (1.0 - confidence) * (q[row] ** 2) + 1e-8

    omega = np.diag(omega_diag) if len(valid_views) else np.zeros((0, 0))
    return p, q, omega
