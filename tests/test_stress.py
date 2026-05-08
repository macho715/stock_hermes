"""Tests for the Phase-5 stress replay scenarios."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from stock_rtx4060.backtest.stress import SCENARIOS, run_replay


def _series_for(scenario: str, *, value: float = 0.001) -> pd.Series:
    start, end = SCENARIOS[scenario]
    idx = pd.bdate_range(start=start, end=end)
    return pd.Series(np.full(len(idx), value), index=idx, name="strategy")


def test_run_replay_period_return_matches_naive_compound():
    rets = _series_for("covid_2020", value=0.001)
    out = run_replay(rets, scenario="covid_2020")
    # Geometric compound (1+r)**n - 1 since returns are constant.
    expected_return = (1.0 + 0.001) ** len(rets) - 1.0
    assert math.isclose(out["period_return"], expected_return, rel_tol=1e-9, abs_tol=1e-12)
    assert out["n_days"] == len(rets)


def test_run_replay_n_days_matches_scenario_length():
    rets = _series_for("gfc_2008", value=0.0)
    out = run_replay(rets, scenario="gfc_2008")
    start, end = SCENARIOS["gfc_2008"]
    expected_days = len(pd.bdate_range(start=start, end=end))
    assert out["n_days"] == expected_days
    # Worst day on a constant-zero series is 0.
    assert out["worst_day"] == 0.0


def test_run_replay_unknown_scenario_raises():
    rets = pd.Series(np.zeros(10), index=pd.bdate_range(end="2024-01-01", periods=10))
    try:
        run_replay(rets, scenario="not_a_real_thing")
    except KeyError:
        return
    raise AssertionError("expected KeyError for unknown scenario")


def test_run_replay_negative_window_max_dd_positive():
    rets = _series_for("rates_2022", value=-0.005)
    out = run_replay(rets, scenario="rates_2022")
    assert out["period_return"] < 0.0
    assert out["max_dd"] > 0.0


def test_run_replay_outside_window_returns_zero_metrics():
    # A series entirely outside the scenario window yields zero everywhere.
    idx = pd.bdate_range(start="2030-01-01", periods=10)
    rets = pd.Series(np.full(10, 0.01), index=idx)
    out = run_replay(rets, scenario="gfc_2008")
    assert out["n_days"] == 0
    assert out["period_return"] == 0.0
    assert out["max_dd"] == 0.0
    assert out["sharpe"] == 0.0


def test_run_replay_coerces_string_index():
    # Pass a Series indexed by date strings; should still work.
    start, end = SCENARIOS["covid_2020"]
    idx = pd.bdate_range(start=start, end=end)
    rets = pd.Series(np.full(len(idx), 0.0), index=[d.strftime("%Y-%m-%d") for d in idx])
    out = run_replay(rets, scenario="covid_2020")
    assert out["n_days"] == len(idx)


def test_run_replay_input_type_validation():
    import pytest

    with pytest.raises(TypeError):
        run_replay([0.01, 0.02], scenario="covid_2020")  # type: ignore[arg-type]
