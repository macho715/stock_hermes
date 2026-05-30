"""Tests for ThompsonWeights (Multi-Armed Bandit advisor weighting)."""

from __future__ import annotations

from collections import Counter

import pytest


class TestThompsonWeightsSample:
    """ThompsonWeights.sample() returns a dict of advisor weights summing to 1.0."""

    def setup_method(self) -> None:
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeights

        self.cls = ThompsonWeights

    def test_sample_returns_dict(self) -> None:
        """sample() returns a dict[str, float]."""
        tw = self.cls(advisors=["news_sentiment", "devils_advocate", "macro_regime"])
        result = tw.sample()
        assert isinstance(result, dict)
        assert set(result.keys()) == {"news_sentiment", "devils_advocate", "macro_regime"}

    def test_sample_weights_sum_to_one(self) -> None:
        """Sample weights sum to 1.0 within floating point tolerance."""
        tw = self.cls(advisors=["news_sentiment", "devils_advocate", "macro_regime"])
        for _ in range(100):
            sample = tw.sample()
            total = sum(sample.values())
            assert abs(total - 1.0) < 1e-6

    def test_sample_respects_prior(self) -> None:
        """With neutral priors (alpha=1, beta=1), all advisors have similar weight range."""
        tw = self.cls(advisors=["a", "b", "c"], alpha_prior=1.0, beta_prior=1.0)
        samples = [tw.sample() for _ in range(200)]

        winners = Counter()
        for s in samples:
            winners[max(s, key=s.get)] += 1

        max_winner_count = max(winners.values())
        assert max_winner_count < 160, f"Advisors too concentrated: winners={dict(winners)}"


class TestThompsonWeightsUpdate:
    """ThompsonWeights.update() correctly updates the Beta distribution per advisor."""

    def setup_method(self) -> None:
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeights

        self.cls = ThompsonWeights

    def test_update_single_reward(self) -> None:
        """A single positive reward moves alpha up by 1."""
        tw = self.cls(advisors=["a"])
        for _ in range(100):
            tw.update("a", reward=1.0)
        assert tw._alpha["a"] >= 100
        assert tw._beta["a"] == 1

    def test_update_punish_negative_reward(self) -> None:
        """reward=0.0 moves beta up by 1 (failure recorded)."""
        tw = self.cls(advisors=["a"])
        for _ in range(50):
            tw.update("a", reward=0.0)
        assert tw._beta["a"] >= 50
        assert tw._alpha["a"] == 1

    def test_update_mixed_rewards(self) -> None:
        """Mixed rewards produce a Beta distribution skewed toward overall accuracy."""
        tw = self.cls(advisors=["a"])
        for _ in range(80):
            tw.update("a", reward=1.0)
        for _ in range(20):
            tw.update("a", reward=0.0)
        assert tw._alpha["a"] == 81
        assert tw._beta["a"] == 21


class TestThompsonWeightsConvergence:
    """ThompsonWeights converges toward higher-reward advisors after many updates."""

    def setup_method(self) -> None:
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeightsImpl

        self.cls = ThompsonWeightsImpl

    def test_convergence_high_reward_wins(self) -> None:
        """After 100 updates, high-reward advisor gets higher average weight than low."""
        tw = self.cls(advisors=["good", "bad"])

        for _ in range(100):
            tw.update("good", reward=1.0)
            tw.update("bad", reward=0.0)

        samples = [tw.sample() for _ in range(300)]
        avg_good = sum(s["good"] for s in samples) / 300
        avg_bad = sum(s["bad"] for s in samples) / 300

        assert avg_good > avg_bad, f"Expected good > bad: good={avg_good:.3f}, bad={avg_bad:.3f}"

    def test_reset_to_fixed_restores_priors(self) -> None:
        """reset_to_fixed() restores priors, which under uniform prior yields near-uniform samples."""
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeightsImpl

        tw = ThompsonWeightsImpl(
            advisors=["news_sentiment", "devils_advocate", "macro_regime"],
            alpha_prior=1.0,
            beta_prior=1.0,
        )

        for _ in range(50):
            tw.update("news_sentiment", reward=1.0)

        tw.reset_to_fixed()

        samples = [tw.sample() for _ in range(300)]
        avg_ns = sum(s["news_sentiment"] for s in samples) / 300
        avg_da = sum(s["devils_advocate"] for s in samples) / 300
        avg_mr = sum(s["macro_regime"] for s in samples) / 300

        assert abs(avg_ns - 0.333) < 0.05, f"news_sentiment avg={avg_ns:.3f}"
        assert abs(avg_da - 0.333) < 0.05, f"devils_advocate avg={avg_da:.3f}"
        assert abs(avg_mr - 0.333) < 0.05, f"macro_regime avg={avg_mr:.3f}"


class TestThompsonWeightsEdgeCases:
    """Edge cases: unknown advisor, zero-sum rewards."""

    def setup_method(self) -> None:
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeights

        self.cls = ThompsonWeights

    def test_update_unknown_advisor_creates_new(self) -> None:
        """update() for a new advisor auto-initializes with prior."""
        tw = self.cls(advisors=["known"])
        tw.update("unknown_advisor", reward=1.0)
        assert "unknown_advisor" in tw._alpha
        assert "unknown_advisor" in tw._beta

    def test_sample_empty_advisors_raises(self) -> None:
        """Empty advisors list raises ValueError."""
        from stock_rtx4060.advisors.thompson_weights import ThompsonWeightsImpl

        with pytest.raises(ValueError):
            ThompsonWeightsImpl(advisors=[])