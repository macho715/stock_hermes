"""Tests for ``stock_rtx4060.portfolio.views`` (Black-Litterman view translation)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.portfolio.views import LLMViews, ViewItem, to_black_litterman_inputs


def _prior(tickers: list[str]) -> pd.Series:
    return pd.Series(0.001, index=tickers, name="prior")


def test_high_confidence_yields_tight_omega():
    prior = _prior(["AAA", "BBB", "CCC"])
    views = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=0.5, confidence=1.0)])
    p, q, omega = to_black_litterman_inputs(views, prior, absolute_view_max=0.05)
    # confidence=1 => omega only the floor (1e-8)
    assert np.diag(omega)[0] == pytest.approx(1e-8, abs=1e-12)


def test_low_confidence_yields_wide_omega():
    prior = _prior(["AAA", "BBB", "CCC"])
    views_lo = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=0.5, confidence=0.0)])
    views_hi = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=0.5, confidence=1.0)])
    _, _, omega_lo = to_black_litterman_inputs(views_lo, prior)
    _, _, omega_hi = to_black_litterman_inputs(views_hi, prior)
    assert np.diag(omega_lo)[0] > np.diag(omega_hi)[0]


def test_q_magnitude_matches_score_times_max():
    prior = _prior(["AAA", "BBB"])
    views = LLMViews(
        items=[
            ViewItem(ticker="AAA", advisory_score=0.5, confidence=0.7),
            ViewItem(ticker="BBB", advisory_score=-0.3, confidence=0.5),
        ]
    )
    _, q, _ = to_black_litterman_inputs(views, prior, absolute_view_max=0.05)
    assert q[0] == pytest.approx(0.5 * 0.05)
    assert q[1] == pytest.approx(-0.3 * 0.05)


def test_p_picking_matrix_has_one_per_view():
    prior = _prior(["AAA", "BBB", "CCC"])
    views = LLMViews(
        items=[
            ViewItem(ticker="BBB", advisory_score=0.4, confidence=0.5),
            ViewItem(ticker="CCC", advisory_score=-0.2, confidence=0.3),
        ]
    )
    p, _, _ = to_black_litterman_inputs(views, prior)
    assert p.shape == (2, 3)
    assert p[0, 1] == 1.0  # BBB is the second column
    assert p[1, 2] == 1.0  # CCC is the third column
    # Other entries are zero
    assert p.sum() == 2.0


def test_unknown_ticker_is_silently_dropped():
    prior = _prior(["AAA", "BBB"])
    views = LLMViews(
        items=[
            ViewItem(ticker="AAA", advisory_score=0.5, confidence=0.5),
            ViewItem(ticker="ZZZ", advisory_score=0.5, confidence=0.5),  # not in prior
        ]
    )
    p, q, omega = to_black_litterman_inputs(views, prior)
    assert p.shape == (1, 2)
    assert q.shape == (1,)
    assert omega.shape == (1, 1)


def test_advisory_score_clipped_to_unit_range():
    prior = _prior(["AAA"])
    views = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=10.0, confidence=0.5)])
    _, q, _ = to_black_litterman_inputs(views, prior, absolute_view_max=0.05)
    # 10.0 clipped to 1.0 => Q = 0.05
    assert q[0] == pytest.approx(0.05)


def test_confidence_clipped_to_unit_range():
    prior = _prior(["AAA"])
    views_high = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=1.0, confidence=5.0)])
    _, _, omega_high = to_black_litterman_inputs(views_high, prior)
    # confidence clipped to 1.0 => floor only
    assert np.diag(omega_high)[0] == pytest.approx(1e-8, abs=1e-12)


def test_zero_views_returns_empty_matrices():
    prior = _prior(["AAA", "BBB"])
    views = LLMViews(items=[])
    p, q, omega = to_black_litterman_inputs(views, prior)
    assert p.shape == (0, 2)
    assert q.shape == (0,)
    assert omega.shape == (0, 0)


def test_absolute_view_max_must_be_positive():
    prior = _prior(["AAA"])
    views = LLMViews(items=[ViewItem(ticker="AAA", advisory_score=0.5, confidence=0.5)])
    with pytest.raises(ValueError):
        to_black_litterman_inputs(views, prior, absolute_view_max=0.0)
