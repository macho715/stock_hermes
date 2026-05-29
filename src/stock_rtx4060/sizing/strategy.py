"""Unified conformal sizing strategies for report-only recommendations.

All strategies emit a multiplier in ``[0, 1]``.  The recommendation engine uses
that value as a downgrade-only rank gate; it never creates broker orders.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

CRISIS = "CRISIS"


@dataclass(frozen=True)
class HorizonScore:
    """One signed model edge for one forecast horizon."""

    horizon: str
    score: float


@dataclass(frozen=True)
class CalibBook:
    """Past out-of-fold residuals grouped globally and by regime."""

    by_regime: dict[str, dict[str, np.ndarray]]
    global_pool: dict[str, np.ndarray]


@dataclass
class SizingResult:
    size_mult: float
    conf: float
    agreement: float
    gate: float
    strategy_used: str = ""
    per_horizon: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)
    coverage_target: float = 0.0
    screening_output_only: bool = True


def _conformal_q(residuals: np.ndarray, alpha: float) -> float:
    """Split-conformal absolute-residual quantile."""

    n = residuals.size
    if n == 0:
        return float("inf")
    level = min(1.0, np.ceil((n + 1) * (1.0 - alpha)) / n)
    return float(np.quantile(np.abs(residuals), level))


def _score_one(score: float, q: float) -> tuple[float, dict]:
    lo, hi = score - q, score + q
    contains_zero = lo <= 0.0 <= hi
    denom = abs(score) if abs(score) > 1e-9 else 1e-9
    term = 0.0 if contains_zero else max(0.0, 1.0 - (hi - lo) / (2.0 * denom))
    return term, {
        "q": q,
        "lo": lo,
        "hi": hi,
        "contains_zero": contains_zero,
        "conf": term,
    }


class SizingStrategy(ABC):
    """Common runtime interface for CMRS variants."""

    name = "base"

    @abstractmethod
    def size(
        self,
        hs: list[HorizonScore],
        book: CalibBook,
        regime: str,
        regime_probs: dict[str, float],
        alpha: float = 0.1,
    ) -> SizingResult:
        """Return a report-only downgrade multiplier."""


class GlobalCMRS(SizingStrategy):
    """Global residual pool with a strong crisis gate."""

    name = "global"

    def size(self, hs, book, regime, regime_probs, alpha=0.1):
        if not hs:
            return SizingResult(0.0, 0.0, 0.0, 0.0, self.name)
        terms, signs, per_h, src = [], [], {}, {}
        for h in hs:
            q = _conformal_q(book.global_pool.get(h.horizon, np.array([])), alpha)
            term, info = _score_one(h.score, q)
            terms.append(term)
            signs.append(np.sign(h.score))
            per_h[h.horizon] = info
            src[h.horizon] = "global"
        conf = float(np.prod(terms))
        agree = float(abs(np.mean(signs)))
        gate = float(max(0.0, 1.0 - regime_probs.get(CRISIS, 0.0)))
        return SizingResult(
            float(np.clip(conf * agree * gate, 0.0, 1.0)),
            conf,
            agree,
            gate,
            self.name,
            per_h,
            src,
            1.0 - alpha,
        )


class MondrianCMRS(SizingStrategy):
    """Regime-conditional residual buckets with global fallback."""

    name = "mondrian"

    def __init__(self, n_min: int = 30):
        self.n_min = n_min

    def size(self, hs, book, regime, regime_probs, alpha=0.1):
        if not hs:
            return SizingResult(0.0, 0.0, 0.0, 0.0, self.name)
        rbook = book.by_regime.get(regime, {})
        terms, signs, per_h, src = [], [], {}, {}
        for h in hs:
            bucket = rbook.get(h.horizon, np.array([]))
            if bucket.size >= self.n_min:
                q, source = _conformal_q(bucket, alpha), "mondrian"
            else:
                q, source = _conformal_q(book.global_pool.get(h.horizon, np.array([])), alpha), "fallback_global"
            term, info = _score_one(h.score, q)
            terms.append(term)
            signs.append(np.sign(h.score))
            per_h[h.horizon] = info
            src[h.horizon] = source
        conf = float(np.prod(terms))
        agree = float(abs(np.mean(signs)))
        gate = float(max(0.0, 1.0 - 0.5 * regime_probs.get(CRISIS, 0.0)))
        return SizingResult(
            float(np.clip(conf * agree * gate, 0.0, 1.0)),
            conf,
            agree,
            gate,
            self.name,
            per_h,
            src,
            1.0 - alpha,
        )


class AutoSizingRouter(SizingStrategy):
    """Choose Mondrian only when every current horizon bucket is sufficiently full."""

    name = "auto"

    def __init__(self, n_min: int = 30):
        self.n_min = n_min
        self._global = GlobalCMRS()
        self._mondrian = MondrianCMRS(n_min)

    def size(self, hs, book, regime, regime_probs, alpha=0.1):
        rbook = book.by_regime.get(regime, {})
        enough = bool(hs) and all(
            rbook.get(h.horizon, np.array([])).size >= self.n_min for h in hs
        )
        chosen = self._mondrian if enough else self._global
        result = chosen.size(hs, book, regime, regime_probs, alpha)
        result.strategy_used = f"auto->{chosen.name}"
        return result


def make_sizer(kind: str = "auto", n_min: int = 30) -> SizingStrategy:
    table: dict[str, SizingStrategy] = {
        "global": GlobalCMRS(),
        "mondrian": MondrianCMRS(n_min),
        "auto": AutoSizingRouter(n_min),
    }
    if kind not in table:
        raise ValueError(f"unknown sizing kind: {kind!r} (use {sorted(table)})")
    return table[kind]


@dataclass
class CoverageGateResult:
    empirical: float
    claimed: float
    status: str
    n: int = 0
    screening_output_only: bool = True


def coverage_honesty_gate(
    realized_hits: np.ndarray,
    alpha: float = 0.1,
    tol: float = 0.05,
) -> CoverageGateResult:
    """Compare realized conformal interval hits against the claimed coverage."""

    claimed = 1.0 - alpha
    n = int(realized_hits.size)
    emp = float(np.mean(realized_hits)) if n else 0.0
    if emp >= claimed - tol:
        status = "PASS"
    elif emp >= claimed - 2.0 * tol:
        status = "AMBER"
    else:
        status = "ZERO"
    return CoverageGateResult(emp, claimed, status, n)
