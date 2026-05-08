"""Tests for cross-sectional / fundamental factors."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_rtx4060.factors.cross_sectional import (
    CROSS_SECTIONAL_FACTORS,
    AmihudIlliquidity,
    Momentum12_1,
    Quality,
    Size,
    Value,
    Volatility60d,
    attach_fundamentals,
)
from stock_rtx4060.feature_engine import make_synthetic_ohlcv


def _make_panel(n_tickers: int = 2, n: int = 400) -> pd.DataFrame:
    frames = []
    for i in range(n_tickers):
        df = make_synthetic_ohlcv(n=n, seed=10 + i)
        cols = pd.MultiIndex.from_product([[f"T{i}"], df.columns], names=["ticker", "field"])
        frames.append(pd.DataFrame(df.values, index=df.index, columns=cols))
    return pd.concat(frames, axis=1)


def test_size_returns_nan_when_no_fundamentals() -> None:
    df = make_synthetic_ohlcv(n=200)
    out = Size().compute(df)
    assert out.isna().all()


def test_size_with_fundamentals_via_attrs() -> None:
    df = make_synthetic_ohlcv(n=200)
    df.attrs["ticker"] = "AAA"
    attach_fundamentals(df, {"AAA": {"market_cap": 1_000_000_000.0}})
    out = Size().compute(df)
    assert np.isclose(out.iloc[0], np.log(1_000_000_000.0))


def test_size_panel_with_attrs_fundamentals() -> None:
    panel = _make_panel(n_tickers=2, n=200)
    attach_fundamentals(panel, {"T0": {"market_cap": 1e9}, "T1": {"market_cap": 1e10}})
    out = Size().compute(panel)
    # Multiindex (date, ticker)
    assert isinstance(out.index, pd.MultiIndex)
    # T1 should have a higher Size value than T0.
    s_by_ticker = out.unstack("ticker")
    assert (s_by_ticker["T1"] > s_by_ticker["T0"]).all()


def test_size_handles_zero_or_negative_market_cap() -> None:
    df = make_synthetic_ohlcv(n=100)
    attach_fundamentals(df, {"X": {"market_cap": 0.0}, "Y": {"market_cap": -5.0}})
    df.attrs["ticker"] = "X"
    assert Size().compute(df).isna().all()


def test_value_with_partial_ratios() -> None:
    df = make_synthetic_ohlcv(n=120)
    df.attrs["ticker"] = "AAA"
    attach_fundamentals(df, {"AAA": {"pe": 20.0, "pb": 4.0}})
    out = Value().compute(df)
    expected = float(np.mean([1 / 20.0, 1 / 4.0]))
    assert np.isclose(out.iloc[0], expected)


def test_value_handles_garbage_input() -> None:
    df = make_synthetic_ohlcv(n=120)
    df.attrs["ticker"] = "AAA"
    attach_fundamentals(df, {"AAA": {"pe": "bogus", "pb": -1.0, "ev_ebitda": None}})
    out = Value().compute(df)
    assert out.isna().all()


def test_value_no_fundamentals_returns_nan() -> None:
    df = make_synthetic_ohlcv(n=120)
    out = Value().compute(df)
    assert out.isna().all()


def test_quality_with_roe_and_accruals() -> None:
    df = make_synthetic_ohlcv(n=120)
    df.attrs["ticker"] = "AAA"
    attach_fundamentals(df, {"AAA": {"roe": 0.20, "net_income": 100, "ocf": 200}})
    out = Quality().compute(df)
    assert np.isclose(out.iloc[0], 0.20 - 0.5)


def test_quality_no_fundamentals_returns_nan() -> None:
    df = make_synthetic_ohlcv(n=120)
    out = Quality().compute(df)
    assert out.isna().all()


def test_momentum_12_1_single() -> None:
    df = make_synthetic_ohlcv(n=400)
    out = Momentum12_1().compute(df)
    # The first 252 values must be NaN (close.shift(252) is NaN there).
    assert out.iloc[:252].isna().all()
    assert np.isfinite(out.dropna()).all()


def test_momentum_12_1_panel() -> None:
    panel = _make_panel(n_tickers=2, n=400)
    out = Momentum12_1().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)


def test_volatility60d_single_and_panel() -> None:
    df = make_synthetic_ohlcv(n=300)
    s = Volatility60d().compute(df)
    finite = s.dropna()
    assert (finite > 0).all()

    panel = _make_panel(n_tickers=2, n=300)
    p = Volatility60d().compute(panel)
    assert isinstance(p.index, pd.MultiIndex)


def test_amihud_illiquidity_single_and_panel() -> None:
    df = make_synthetic_ohlcv(n=300)
    s = AmihudIlliquidity().compute(df)
    assert s.dropna().shape[0] > 0

    panel = _make_panel(n_tickers=2, n=300)
    p = AmihudIlliquidity().compute(panel)
    assert isinstance(p.index, pd.MultiIndex)


def test_cross_sectional_factor_count() -> None:
    assert len(CROSS_SECTIONAL_FACTORS) == 6


def test_attach_fundamentals_returns_panel() -> None:
    df = make_synthetic_ohlcv(n=30)
    out = attach_fundamentals(df, {"AAA": {"pe": 10.0}})
    assert out is df
    assert "fundamentals" in df.attrs
