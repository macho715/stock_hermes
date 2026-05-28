"""Property-based tests for stock_rtx4060 financial invariants.

Uses Hypothesis to verify that core safety properties hold across the full
input space — not just hand-crafted examples.  Each test targets one
concrete invariant from the project specification:

  INV-1  paper_trading_only is always True on PaperDecision
  INV-2  BUY score < min_buy_score (56.0) is always rejected
  INV-3  PIT as_of with a future date always raises RuntimeError
  INV-4  advisory_score is always clipped to [-1, +1]
  INV-5  portfolio optimize() weights always sum to ~1.0
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from stock_rtx4060.paper_trading import (
    PaperTradingConfig,
    PaperTradingEngine,
    PaperTradingSignal,
)


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Valid model quality values that pass model-evidence gates so the GAP-01
# threshold check is reached.
_GOOD_AUC = st.floats(0.56, 0.99, allow_nan=False)
_GOOD_ACC = st.floats(0.53, 0.99, allow_nan=False)
_GOOD_OOF = st.floats(0.81, 1.0, allow_nan=False)

# US tickers — phase1_us_only rejects KRX tickers before score check.
_US_TICKER = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    min_size=1,
    max_size=5,
)


def _engine(market: str = "US") -> PaperTradingEngine:
    return PaperTradingEngine(PaperTradingConfig(market=market, phase1_us_only=False))


# ---------------------------------------------------------------------------
# INV-1: paper_trading_only is always True
# ---------------------------------------------------------------------------


@given(
    score=st.floats(0.0, 100.0, allow_nan=False),
    signal=st.sampled_from(["BUY", "SELL", "HOLD", "buy", "sell", "hold"]),
    auc=_GOOD_AUC,
    acc=_GOOD_ACC,
    oof=_GOOD_OOF,
)
@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
def test_inv1_paper_trading_only_always_true(score, signal, auc, acc, oof):
    """INV-1: Every PaperDecision has paper_trading_only=True regardless of input."""
    engine = _engine()
    sig = PaperTradingSignal(
        ticker="AAPL",
        score=score,
        signal=signal,
        model_auc=auc,
        model_accuracy=acc,
        oof_coverage=oof,
    )
    decision = engine.evaluate_signal(sig, bars=None)
    assert decision.paper_trading_only is True, (
        f"paper_trading_only must always be True, got False for "
        f"signal={signal!r} score={score}"
    )


# ---------------------------------------------------------------------------
# INV-2: BUY score < 56.0 is always rejected
# ---------------------------------------------------------------------------


@given(
    score=st.floats(0.0, 55.999, allow_nan=False, exclude_max=False),
    auc=_GOOD_AUC,
    acc=_GOOD_ACC,
    oof=_GOOD_OOF,
    ticker=_US_TICKER,
)
@settings(max_examples=300)
def test_inv2_buy_below_threshold_always_rejected(score, auc, acc, oof, ticker):
    """INV-2: BUY with score < 56.0 is always rejected as buy_score_below_threshold."""
    engine = _engine()
    sig = PaperTradingSignal(
        ticker=ticker or "AAPL",
        score=score,
        signal="BUY",
        model_auc=auc,
        model_accuracy=acc,
        oof_coverage=oof,
    )
    decision = engine.evaluate_signal(sig, bars=None)
    assert decision.status.upper() == "REJECTED", (
        f"BUY with score={score} should be rejected, got {decision.status!r}"
    )
    assert "score" in decision.reason.lower() or "threshold" in decision.reason.lower(), (
        f"Reject reason should mention score/threshold, got {decision.reason!r}"
    )


# ---------------------------------------------------------------------------
# INV-3: PIT as_of with future date always raises RuntimeError
# ---------------------------------------------------------------------------


@given(days_future=st.integers(min_value=1, max_value=3650))
@settings(max_examples=100)
def test_inv3_pit_future_as_of_raises(days_future):
    """INV-3: as_of pointing to the future must raise RuntimeError (no look-ahead)."""
    from stock_rtx4060.data_providers import load_ohlcv_with_provider

    future_date = (date.today() + timedelta(days=days_future)).isoformat()
    with pytest.raises(RuntimeError, match="lake miss|as_of"):
        load_ohlcv_with_provider(
            "AAPL",
            "1y",
            as_of=future_date,
            data_lake_first=True,
        )


# ---------------------------------------------------------------------------
# INV-4: AdvisoryOutput always enforces score ∈ [-1, +1]
# ---------------------------------------------------------------------------


@given(score=st.floats(-1.0, 1.0, allow_nan=False))
@settings(max_examples=300)
def test_inv4_advisory_output_accepts_valid_scores(score):
    """INV-4a: AdvisoryOutput accepts any score in [-1, +1]."""
    from stock_rtx4060.advisors.base import AdvisoryOutput

    out = AdvisoryOutput(
        agent="test",
        ticker="AAPL",
        score=score,
        confidence=0.5,
        rationale="test",
        citations=[],
        prompt_hash="abc",
        tokens_in=100,
        tokens_out=10,
        cost_usd=0.001,
    )
    assert -1.0 <= out.score <= 1.0


@given(score=st.one_of(st.floats(1.001, 100.0), st.floats(-100.0, -1.001)))
@settings(max_examples=100)
def test_inv4_advisory_output_rejects_out_of_range(score):
    """INV-4b: AdvisoryOutput raises ValueError for score outside [-1, +1]."""
    from stock_rtx4060.advisors.base import AdvisoryOutput

    with pytest.raises(ValueError, match=r"\[-1"):
        AdvisoryOutput(
            agent="test",
            ticker="AAPL",
            score=score,
            confidence=0.5,
            rationale="test",
            citations=[],
            prompt_hash="abc",
            tokens_in=100,
            tokens_out=10,
            cost_usd=0.001,
        )


# ---------------------------------------------------------------------------
# INV-5: optimize() weights always sum to ≈1.0
# ---------------------------------------------------------------------------


@given(
    n_assets=st.integers(min_value=2, max_value=15),
    n_rows=st.integers(min_value=10, max_value=100),
)
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_inv5_portfolio_weights_sum_to_one(n_assets, n_rows):
    """INV-5: optimize() always returns weights that sum to 1.0 ± 1e-5."""
    from stock_rtx4060.portfolio.optimizer import optimize

    # max_weight=0.25 requires n_assets >= 4 to be feasible (0.25 * 4 = 1.0).
    assume(n_assets >= 4)
    rng = np.random.default_rng(seed=42 + n_assets + n_rows)
    returns = pd.DataFrame(
        rng.standard_normal((n_rows, n_assets)),
        columns=[f"S{i}" for i in range(n_assets)],
    )
    assume(returns.shape[0] >= 5)

    weights = optimize(returns, method="hrp")
    total = float(weights.sum())
    assert math.isclose(total, 1.0, abs_tol=1e-5), (
        f"weights.sum() = {total}, expected 1.0 ± 1e-5 "
        f"(n_assets={n_assets}, n_rows={n_rows})"
    )
