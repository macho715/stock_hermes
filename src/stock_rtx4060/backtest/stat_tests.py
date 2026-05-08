"""López de Prado statistical tests for backtest credibility.

Reference: López de Prado, *Advances in Financial Machine Learning* (2018),
Chapter 14 — "Backtest Statistics".

All formulas use NumPy / SciPy only.  ``scipy`` is already a hard dependency
for this project, but we still gate the import to keep the module robust.
"""

from __future__ import annotations

import math

try:  # SciPy is in requirements.in; gate the import for safety.
    from scipy.special import ndtri  # inverse normal CDF
    from scipy.stats import norm

    _HAS_SCIPY = True
except Exception:  # pragma: no cover - SciPy is a hard dep, but stay defensive.
    norm = None  # type: ignore[assignment]
    ndtri = None  # type: ignore[assignment]
    _HAS_SCIPY = False


# --- helpers ----------------------------------------------------------------


def _normal_cdf(x: float) -> float:
    if _HAS_SCIPY:
        return float(norm.cdf(x))
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))  # pragma: no cover


def _normal_ppf(p: float) -> float:
    if _HAS_SCIPY:
        return float(ndtri(p))
    # Defensive fallback when SciPy is unavailable; rational approximation
    # accurate to ~1e-7.  Not exercised in CI but kept for portability.
    if p <= 0.0 or p >= 1.0:  # pragma: no cover
        raise ValueError("p must be in (0, 1)")
    a = [  # pragma: no cover
        -3.969683028665376e1,
        2.209460984245205e2,
        -2.759285104469687e2,
        1.383577518672690e2,
        -3.066479806614716e1,
        2.506628277459239,
    ]
    b = [  # pragma: no cover
        -5.447609879822406e1,
        1.615858368580409e2,
        -1.556989798598866e2,
        6.680131188771972e1,
        -1.328068155288572e1,
    ]
    c = [  # pragma: no cover
        -7.784894002430293e-3,
        -3.223964580411365e-1,
        -2.400758277161838,
        -2.549732539343734,
        4.374664141464968,
        2.938163982698783,
    ]
    p_low = 0.02425  # pragma: no cover
    p_high = 1.0 - p_low  # pragma: no cover
    if p < p_low:  # pragma: no cover
        q = math.sqrt(-2.0 * math.log(p))
        return ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
    if p <= p_high:  # pragma: no cover
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        )
    q = math.sqrt(-2.0 * math.log(1.0 - p))  # pragma: no cover
    return -((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]  # pragma: no cover


def _euler_mascheroni() -> float:
    return 0.5772156649015329


# --- public API -------------------------------------------------------------


def probabilistic_sharpe(
    sr: float,
    sr_benchmark: float,
    *,
    n_obs: int,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    r"""Probabilistic Sharpe Ratio (PSR).

    PSR estimates the probability that an *observed* Sharpe ratio ``sr``
    exceeds a benchmark ``sr_benchmark``, given ``n_obs`` observations,
    ``skew``ness, and ``kurt``osis (kurtosis is the *raw* fourth moment
    so a normal distribution has ``kurt = 3``).

    Formula (Bailey & López de Prado 2014):

        PSR = Φ( (SR - SR*) · sqrt(n - 1) /
                  sqrt(1 - γ3 · SR + (γ4 - 1) / 4 · SR²) )

    where ``γ3`` is skew and ``γ4`` is kurtosis.
    """
    if n_obs < 2:
        raise ValueError("n_obs must be >= 2")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0.0:
        # Degenerate; clip to a tiny positive to keep PSR bounded.
        denom = 1e-12
    z = (sr - sr_benchmark) * math.sqrt(n_obs - 1) / math.sqrt(denom)
    return _normal_cdf(z)


def deflated_sharpe(
    sr: float,
    *,
    n_trials: int,
    skew: float = 0.0,
    kurt: float = 3.0,
    n_obs: int,
) -> float:
    r"""Deflated Sharpe Ratio (DSR) — PSR adjusted for selection bias.

    When ``n_trials`` candidate strategies are evaluated, the maximum
    observed Sharpe is biased upward.  The deflated SR replaces the
    benchmark with the expected maximum of ``n_trials`` standard-normal
    Sharpes (López de Prado 2014, eq. 14):

        E[max] ≈ (1 - γ) · Φ⁻¹(1 - 1/N) + γ · Φ⁻¹(1 - 1/(N·e))

    where ``γ`` is the Euler-Mascheroni constant and ``N = n_trials``.
    The DSR is then ``PSR(sr, E[max])``.
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if n_obs < 2:
        raise ValueError("n_obs must be >= 2")
    if n_trials == 1:
        sr_star = 0.0
    else:
        gamma = _euler_mascheroni()
        n = float(n_trials)
        # Guard the inner probabilities against numerical edge cases.
        p1 = max(min(1.0 - 1.0 / n, 1.0 - 1e-12), 1e-12)
        p2 = max(min(1.0 - 1.0 / (n * math.e), 1.0 - 1e-12), 1e-12)
        sr_star = (1.0 - gamma) * _normal_ppf(p1) + gamma * _normal_ppf(p2)
        # Annualize-free: SR* is already in the same units as sr.
        sr_star = sr_star / math.sqrt(n_obs - 1)
    return probabilistic_sharpe(sr, sr_star, n_obs=n_obs, skew=skew, kurt=kurt)


def min_track_record_length(
    sr: float,
    sr_benchmark: float,
    *,
    n_obs: int,  # noqa: ARG001 - kept for signature symmetry / future extensions
    alpha: float = 0.05,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> int:
    r"""Minimum Track Record Length (MinTRL).

    Smallest number of observations required so that PSR ≥ 1 - α:

        MinTRL = 1 + (1 - γ3·SR + (γ4-1)/4·SR²) · ( Φ⁻¹(1-α) / (SR - SR*) )²

    Returns a *positive* integer (rounded up).  Raises ``ValueError`` when
    ``sr <= sr_benchmark`` since the bound is undefined in that case.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    if sr <= sr_benchmark:
        raise ValueError("sr must exceed sr_benchmark for a finite MinTRL")
    z = _normal_ppf(1.0 - alpha)
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0.0:
        denom = 1e-12
    bound = 1.0 + denom * (z / (sr - sr_benchmark)) ** 2
    return int(math.ceil(bound))
