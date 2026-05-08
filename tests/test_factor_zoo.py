"""Tests for the FactorRegistry singleton and compute_all dispatch."""

from __future__ import annotations

import pandas as pd

from stock_rtx4060.factors import FactorRegistry, register_factor
from stock_rtx4060.factors.base import Factor, FactorMeta
from stock_rtx4060.feature_engine import make_synthetic_ohlcv


def test_registry_singleton() -> None:
    a = FactorRegistry()
    b = FactorRegistry()
    assert a is b


def test_registry_has_minimum_factors() -> None:
    reg = FactorRegistry()
    assert len(reg) >= 15
    # Specific named factors must be present.
    for name in ("RSI14", "MACDHistogram", "Alpha101", "Size", "Momentum12_1"):
        assert name in reg, f"missing built-in factor {name}"


def test_alpha101_category_filter() -> None:
    reg = FactorRegistry()
    a101 = reg.list(category="alpha101")
    assert len(a101) >= 7
    assert all(reg.get(n).meta.category == "alpha101" for n in a101)


def test_compute_all_returns_wide_dataframe() -> None:
    df = make_synthetic_ohlcv(n=300)
    reg = FactorRegistry()
    technical_names = reg.list(category="technical")
    out = reg.compute_all(df, names=technical_names)
    assert isinstance(out, pd.DataFrame)
    assert out.shape[1] == len(technical_names)
    assert set(out.columns) == set(technical_names)


def test_compute_all_filters_by_category() -> None:
    df = make_synthetic_ohlcv(n=300)
    reg = FactorRegistry()
    out = reg.compute_all(df, category="alpha101")
    assert all(reg.get(c).meta.category == "alpha101" for c in out.columns)


def test_register_unknown_get_raises() -> None:
    reg = FactorRegistry()
    try:
        reg.get("nope__not__a__factor")
    except KeyError:
        return
    raise AssertionError("get should raise KeyError")


def test_register_factor_helper() -> None:
    class MyOne(Factor):
        meta = FactorMeta(name="ZooTestOne", category="discovered", lookback=2)

        def compute(self, panel, as_of=None):  # type: ignore[no-untyped-def]
            return panel["Close"].diff()

    inst = MyOne()
    register_factor(inst)
    reg = FactorRegistry()
    assert "ZooTestOne" in reg


def test_registry_list_sorted() -> None:
    reg = FactorRegistry()
    names = reg.list()
    assert names == sorted(names)
