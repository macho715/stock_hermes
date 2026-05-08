"""Tests for López de Prado statistical tests (PSR / DSR / MinTRL).

The acceptance criteria mirror the assertions in the project plan:

- ``deflated_sharpe(sr=2.0, n_trials=100, n_obs=252) > 0``
- ``probabilistic_sharpe(2.0, 0.0, n_obs=252) > 0.95``
- ``min_track_record_length(...)`` returns a positive integer.
"""

from __future__ import annotations

import math

import pytest

from stock_rtx4060.backtest.stat_tests import (
    deflated_sharpe,
    min_track_record_length,
    probabilistic_sharpe,
)


def test_probabilistic_sharpe_strong_strategy():
    psr = probabilistic_sharpe(2.0, 0.0, n_obs=252)
    # SR=2 over 252 obs vs 0 benchmark is overwhelmingly significant.
    assert psr > 0.95
    # Still bounded on [0, 1].
    assert 0.0 < psr <= 1.0


def test_deflated_sharpe_positive_on_realistic_grid():
    dsr = deflated_sharpe(sr=2.0, n_trials=100, n_obs=252)
    assert dsr > 0.0
    assert dsr <= 1.0


def test_min_track_record_length_positive_integer():
    n = min_track_record_length(0.5, 0.0, n_obs=100, alpha=0.05)
    assert isinstance(n, int)
    assert n > 0


def test_probabilistic_sharpe_zero_when_sr_below_benchmark():
    # When sr is well below the benchmark, PSR should be small.
    psr = probabilistic_sharpe(0.0, 1.0, n_obs=252)
    assert psr < 0.5


def test_deflated_sharpe_more_trials_lowers_psr():
    base = deflated_sharpe(1.0, n_trials=1, n_obs=252)
    deflated = deflated_sharpe(1.0, n_trials=500, n_obs=252)
    # Selection bias correction must reduce significance.
    assert deflated <= base + 1e-9


def test_min_track_record_length_raises_for_dominated_sr():
    with pytest.raises(ValueError):
        min_track_record_length(0.0, 1.0, n_obs=100)


def test_skew_kurt_bounds_finite():
    # Non-trivial higher moments must keep PSR finite and bounded.
    psr = probabilistic_sharpe(1.5, 0.5, n_obs=252, skew=-0.5, kurt=5.0)
    assert math.isfinite(psr)
    assert 0.0 <= psr <= 1.0


def test_deflated_sharpe_n_trials_one_equals_psr_zero():
    # With a single trial, DSR collapses to PSR(sr, 0) — same probabilistic
    # significance vs. zero benchmark.
    sr = 1.2
    n_obs = 252
    dsr = deflated_sharpe(sr, n_trials=1, n_obs=n_obs)
    psr = probabilistic_sharpe(sr, 0.0, n_obs=n_obs)
    assert math.isclose(dsr, psr, rel_tol=1e-9, abs_tol=1e-12)


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        deflated_sharpe(1.0, n_trials=0, n_obs=252)
    with pytest.raises(ValueError):
        deflated_sharpe(1.0, n_trials=10, n_obs=1)
    with pytest.raises(ValueError):
        probabilistic_sharpe(1.0, 0.0, n_obs=1)
    with pytest.raises(ValueError):
        min_track_record_length(0.5, 0.0, n_obs=100, alpha=1.5)


def test_high_skew_kurt_does_not_blow_up():
    # Pathological denominator path — kurt=0 makes denom negative for SR=2.
    # Function must clip and still return a finite probability.
    psr = probabilistic_sharpe(2.0, 0.0, n_obs=252, skew=10.0, kurt=0.0)
    assert math.isfinite(psr)
    assert 0.0 <= psr <= 1.0
    n = min_track_record_length(2.0, 0.0, n_obs=252, skew=10.0, kurt=0.0)
    assert n > 0
