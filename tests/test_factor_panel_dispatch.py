"""Tests covering the wide-MultiIndex panel dispatch path of factors."""

from __future__ import annotations

import pandas as pd

from stock_rtx4060.factors.alpha101 import Alpha012, Alpha101
from stock_rtx4060.factors.factor_zoo import FactorRegistry
from stock_rtx4060.factors.technical import RSI14, BBPct, MACDHistogram, SMARatio20
from stock_rtx4060.feature_engine import make_synthetic_ohlcv


def _panel(n_tickers: int = 3, n: int = 200) -> pd.DataFrame:
    frames = []
    for i in range(n_tickers):
        df = make_synthetic_ohlcv(n=n, seed=20 + i)
        cols = pd.MultiIndex.from_product([[f"T{i}"], df.columns], names=["ticker", "field"])
        frames.append(pd.DataFrame(df.values, index=df.index, columns=cols))
    return pd.concat(frames, axis=1)


def test_rsi_panel_dispatch() -> None:
    panel = _panel()
    out = RSI14().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)
    assert out.dropna().shape[0] > 0


def test_macd_panel_dispatch() -> None:
    panel = _panel()
    out = MACDHistogram().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)


def test_sma_ratio_panel_dispatch() -> None:
    panel = _panel()
    out = SMARatio20().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)


def test_bbpct_panel_dispatch() -> None:
    panel = _panel()
    out = BBPct().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)


def test_alpha101_panel_dispatch() -> None:
    panel = _panel()
    out = Alpha012().compute(panel)
    assert isinstance(out.index, pd.MultiIndex)
    out2 = Alpha101().compute(panel)
    assert isinstance(out2.index, pd.MultiIndex)


def test_compute_all_with_panel_input() -> None:
    panel = _panel(n_tickers=2, n=300)
    reg = FactorRegistry()
    techs = ["RSI14", "Alpha101"]
    out = reg.compute_all(panel, names=techs)
    assert set(out.columns) == set(techs)


def test_compute_all_with_unknown_name_filtered() -> None:
    df = make_synthetic_ohlcv(n=300)
    reg = FactorRegistry()
    out = reg.compute_all(df, names=["__bogus__", "RSI14"])
    assert list(out.columns) == ["RSI14"]


def test_compute_all_empty_chosen_returns_index_only_frame() -> None:
    df = make_synthetic_ohlcv(n=50)
    reg = FactorRegistry()
    out = reg.compute_all(df, names=["__nope__"])
    assert out.shape[1] == 0
