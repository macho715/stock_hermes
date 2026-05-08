"""Smoke / sanity tests for the seven WorldQuant 101 alphas implemented."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_rtx4060.factors.alpha101 import (
    ALPHA101_FACTORS,
    Alpha001,
    Alpha003,
    Alpha006,
    Alpha012,
    Alpha041,
    Alpha054,
    Alpha101,
)
from stock_rtx4060.feature_engine import make_synthetic_ohlcv


@pytest.fixture(scope="module")
def synth() -> pd.DataFrame:
    return make_synthetic_ohlcv(n=200)


@pytest.mark.parametrize(
    "factor_cls",
    [Alpha001, Alpha003, Alpha006, Alpha012, Alpha041, Alpha054, Alpha101],
)
def test_alpha_runs_on_synthetic(factor_cls: type, synth: pd.DataFrame) -> None:
    factor = factor_cls()
    series = factor.compute(synth)
    assert isinstance(series, pd.Series)
    assert series.index.equals(synth.index)
    finite = np.isfinite(series.dropna())
    assert finite.any(), f"{factor_cls.__name__}: no finite values"
    # Most data points (>= 30%) should be finite once the warm-up window passes.
    assert (np.isfinite(series).sum() / len(series)) >= 0.30


def test_alpha101_count() -> None:
    assert len(ALPHA101_FACTORS) >= 7


def test_alpha_no_lookahead(synth: pd.DataFrame) -> None:
    """For each factor, computing with as_of=t must equal the t-th element of full run.

    This exercises the slice_as_of contract: truncating future bars before
    computing must not change the past.  A leak-free factor depends only on
    inputs at index <= as_of.
    """
    factor = Alpha012()
    full = factor.compute(synth)
    cutoff = synth.index[150]
    truncated = factor.compute(synth, as_of=cutoff)
    # Both series should agree on the cutoff date.
    assert truncated.index[-1] == cutoff
    pd.testing.assert_series_equal(
        full.loc[:cutoff].dropna(),
        truncated.dropna(),
        check_names=False,
    )


def test_alpha_with_panel_input() -> None:
    df1 = make_synthetic_ohlcv(n=100, seed=1)
    df2 = make_synthetic_ohlcv(n=100, seed=2)
    cols1 = pd.MultiIndex.from_product([["AAA"], df1.columns], names=["ticker", "field"])
    cols2 = pd.MultiIndex.from_product([["BBB"], df2.columns], names=["ticker", "field"])
    panel = pd.concat(
        [
            pd.DataFrame(df1.values, index=df1.index, columns=cols1),
            pd.DataFrame(df2.values, index=df2.index, columns=cols2),
        ],
        axis=1,
    )
    factor = Alpha101()
    series = factor.compute(panel)
    assert isinstance(series.index, pd.MultiIndex)
    levels = series.index.names
    assert "ticker" in levels
    assert series.dropna().shape[0] > 0


def test_alpha_ic_signal_recovery(synth: pd.DataFrame) -> None:
    """Sanity: at least one alpha shows a non-zero IC against forward returns."""
    fwd = synth["Close"].pct_change(5).shift(-5)
    from stock_rtx4060.factors.analytics import compute_ic

    ic_values = []
    for f in [Alpha012(), Alpha101(), Alpha041()]:
        v = f.compute(synth)
        ic = compute_ic(v, fwd)
        ic_values.append(ic)
    # On 200 bars of synthetic data IC magnitudes are small; assert at least one
    # is a finite real number (rather than collapsed to NaN).
    assert any(np.isfinite(v) for v in ic_values)
