"""Thompson Sampling Multi-Armed Bandit advisor weighting.

``ThompsonWeights`` maintains a Beta distribution per advisor and samples
weights from the posterior each time ``sample()`` is called.
Higher reward history → higher sampled weight.

Set ``ADVISOR_WEIGHTS_MODE=fixed`` to fall back to uniform DEFAULT_WEIGHTS.
"""

from __future__ import annotations

import os
import random as _random
from dataclasses import dataclass, field

_WEIGHTS_MODE = os.getenv("ADVISOR_WEIGHTS_MODE", "mab").lower()

# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

if _WEIGHTS_MODE == "fixed":
    from .orchestrator import DEFAULT_WEIGHTS  # noqa: F401

    def ThompsonWeights(
        advisors: list[str],
        *,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
    ) -> "ThompsonWeights":
        return _FixedWeights(advisors)

else:

    def ThompsonWeights(
        advisors: list[str],
        *,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
    ) -> "ThompsonWeightsImpl":
        return ThompsonWeightsImpl(advisors, alpha_prior, beta_prior)


# ---------------------------------------------------------------------------
# Implementation
# ---------------------------------------------------------------------------

try:
    from numpy import random as _np_random

    def _sample_beta(a: float, b: float) -> float:
        return max(_np_random.beta(a, b), 1e-9)

except ImportError:  # pragma: no cover

    def _sample_beta(a: float, b: float) -> float:
        return max(_random.betavariate(a, b), 1e-9)


@dataclass
class ThompsonWeightsImpl:
    """Thompson Sampling Beta-Bernoulli bandit per advisor.

    Each advisor has a Beta(alpha, beta) posterior.
    ``sample()`` draws from each posterior and normalises to sum=1.
    ``update(advisor_id, reward)`` increments alpha (success) or beta (failure).
    """

    advisors: list[str]
    alpha_prior: float = 1.0
    beta_prior: float = 1.0

    # Internal posterior counts (keyed by advisor name)
    _alpha: dict[str, float] = field(default_factory=dict, repr=False)
    _beta: dict[str, float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if not self.advisors:
            raise ValueError("advisors list cannot be empty")
        for name in self.advisors:
            self._alpha.setdefault(name, self.alpha_prior)
            self._beta.setdefault(name, self.beta_prior)

    def sample(self) -> dict[str, float]:
        """Draw one weight vector from the posterior and return normalised weights."""
        raw = {name: _sample_beta(self._alpha[name], self._beta[name]) for name in self.advisors}
        total = sum(raw.values())
        return {name: raw[name] / total for name in self.advisors}

    def update(self, advisor_id: str, reward: float) -> None:
        """Record a reward outcome for the given advisor.

        reward > 0.5 → success (increment alpha)
        reward <= 0.5 → failure (increment beta)
        """
        if advisor_id not in self._alpha:
            self._alpha[advisor_id] = self.alpha_prior
            self._beta[advisor_id] = self.beta_prior

        if reward > 0.5:
            self._alpha[advisor_id] += 1.0
        else:
            self._beta[advisor_id] += 1.0

    def reset_to_fixed(self) -> None:
        """Reset all posterior parameters to the prior."""
        for name in self.advisors:
            self._alpha[name] = self.alpha_prior
            self._beta[name] = self.beta_prior


@dataclass
class _FixedWeights:
    """Zero-history fallback that returns uniform weights."""

    advisors: list[str]

    def sample(self) -> dict[str, float]:
        n = len(self.advisors)
        w = 1.0 / n if n > 0 else 0.0
        return {name: w for name in self.advisors}

    def update(self, advisor_id: str, reward: float) -> None:
        pass

    def reset_to_fixed(self) -> None:
        pass


__all__ = ["ThompsonWeights", "ThompsonWeightsImpl", "_FixedWeights"]