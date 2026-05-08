"""Validation gate for newly-discovered factors.

A discovered factor is admitted to the registry only if it clears every gate:

* ``|IC|`` >= ``min_abs_ic``
* ``IR``  >= ``min_ir``  (computed from a rolling sequence of ICs)
* max correlation against any existing registered factor < ``max_corr_with_existing``
* rank-autocorr / decay implies a half-life >= ``min_half_life_days``

The validator is *pure* in the sense that it does not modify the registry —
callers decide whether to ``register`` based on the returned ``ValidationResult``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..analytics import compute_ic, compute_ir, rank_autocorr
from ..base import Factor
from ..factor_zoo import FactorRegistry


@dataclass
class ValidationResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    ic: float = float("nan")
    ir: float = float("nan")
    max_corr: float = float("nan")
    half_life: float = float("nan")


def _rolling_ic(factor_values: pd.Series, fwd_returns: pd.Series, window: int = 21) -> pd.Series:
    df = pd.concat([factor_values.rename("f"), fwd_returns.rename("r")], axis=1, join="inner").dropna()
    if df.empty:
        return pd.Series(dtype=float)
    ics: list[float] = []
    idx = df.index
    arr = df.values
    for i in range(window, len(df) + 1):
        chunk = arr[i - window : i]
        f = pd.Series(chunk[:, 0])
        r = pd.Series(chunk[:, 1])
        if f.std(ddof=0) == 0.0 or r.std(ddof=0) == 0.0:
            ics.append(float("nan"))
        else:
            ics.append(float(f.corr(r, method="spearman")))
    return pd.Series(ics, index=idx[window - 1 :])


def _half_life_from_autocorr(rho: float) -> float:
    """Half-life implied by an AR(1) coefficient."""
    if rho is None or not np.isfinite(rho) or rho <= 0.0 or rho >= 1.0:
        return float("nan")
    return float(np.log(0.5) / np.log(rho))


def validate_discovered_factor(
    factor: Factor,
    panel: pd.DataFrame,
    fwd_returns: pd.Series,
    *,
    min_abs_ic: float = 0.03,
    min_ir: float = 0.3,
    max_corr_with_existing: float = 0.7,
    min_half_life_days: int = 3,
) -> ValidationResult:
    """Check whether ``factor`` clears the discovery gates."""
    reasons: list[str] = []

    # 1. IC
    fv = factor.compute(panel).rename(factor.name)
    ic = compute_ic(fv, fwd_returns)
    if not np.isfinite(ic) or abs(ic) < min_abs_ic:
        reasons.append(f"IC {ic:.4f} below threshold {min_abs_ic}")

    # 2. IR via rolling IC
    ric = _rolling_ic(fv, fwd_returns, window=21)
    ir = compute_ir(ric)
    if not np.isfinite(ir) or ir < min_ir:
        reasons.append(f"IR {ir:.4f} below threshold {min_ir}")

    # 3. Correlation with existing factors
    reg = FactorRegistry()
    max_corr = 0.0
    for other_name in reg.list():
        if other_name == factor.name:
            continue
        try:
            other = reg.get(other_name).compute(panel)
        except Exception:  # pragma: no cover - skip broken siblings
            continue
        try:
            joined = pd.concat([fv, other.rename(other_name)], axis=1, join="inner").dropna()
            if len(joined) < 5:
                continue
            corr = float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))
        except Exception:  # pragma: no cover
            continue
        if np.isfinite(corr) and abs(corr) > max_corr:
            max_corr = abs(corr)
    if max_corr >= max_corr_with_existing:
        reasons.append(f"Max abs correlation {max_corr:.3f} >= {max_corr_with_existing}")

    # 4. Half-life via rank autocorr
    rho = rank_autocorr(fv, lag=1)
    hl = _half_life_from_autocorr(rho)
    if not np.isfinite(hl) or hl < min_half_life_days:
        reasons.append(f"Implied half-life {hl:.2f}d below {min_half_life_days}d")

    passed = len(reasons) == 0
    return ValidationResult(passed=passed, reasons=reasons, ic=ic, ir=ir, max_corr=max_corr, half_life=hl)
