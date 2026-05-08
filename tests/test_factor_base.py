"""Tests for the Factor ABC and FactorMeta dataclass."""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from stock_rtx4060.factors.base import (
    Factor,
    FactorMeta,
    field_for,
    is_panel,
    slice_as_of,
)


def test_factor_meta_validates_name() -> None:
    with pytest.raises(ValueError):
        FactorMeta(name="", category="technical", lookback=5)


def test_factor_meta_validates_lookback() -> None:
    with pytest.raises(ValueError):
        FactorMeta(name="X", category="technical", lookback=0)


def test_factor_meta_validates_category() -> None:
    with pytest.raises(ValueError):
        FactorMeta(name="X", category="bogus", lookback=5)  # type: ignore[arg-type]


def test_factor_meta_is_frozen() -> None:
    meta = FactorMeta(name="X", category="technical", lookback=5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.name = "Y"  # type: ignore[misc]


def test_factor_meta_equality() -> None:
    a = FactorMeta(name="X", category="technical", lookback=5)
    b = FactorMeta(name="X", category="technical", lookback=5)
    assert a == b


def test_concrete_factor_must_define_meta() -> None:
    with pytest.raises(TypeError):

        class _BadFactor(Factor):  # noqa: D401 — exercise meta enforcement
            def compute(self, panel, as_of=None):  # type: ignore[no-untyped-def]
                return pd.Series(dtype=float)


def test_factor_subclass_works_with_meta() -> None:
    class GoodFactor(Factor):
        meta = FactorMeta(name="GoodFactor", category="technical", lookback=3)

        def compute(self, panel, as_of=None):  # type: ignore[no-untyped-def]
            return panel["Close"].diff()

    inst = GoodFactor()
    assert inst.name == "GoodFactor"
    assert inst.lookback == 3


def test_is_panel_detection() -> None:
    flat = pd.DataFrame({"Open": [1.0, 2.0], "Close": [1.0, 2.0]}, index=pd.bdate_range("2020-01-01", periods=2))
    cols = pd.MultiIndex.from_product([["AAPL", "MSFT"], ["Close"]], names=["ticker", "field"])
    panel = pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], index=pd.bdate_range("2020-01-01", periods=2), columns=cols)
    assert not is_panel(flat)
    assert is_panel(panel)


def test_slice_as_of_inclusive() -> None:
    idx = pd.bdate_range("2020-01-01", periods=5)
    df = pd.DataFrame({"Close": [1, 2, 3, 4, 5]}, index=idx)
    out = slice_as_of(df, idx[2])
    assert len(out) == 3
    assert out.index[-1] == idx[2]


def test_slice_as_of_none_returns_input() -> None:
    df = pd.DataFrame({"Close": [1, 2]}, index=pd.bdate_range("2020-01-01", periods=2))
    assert slice_as_of(df, None) is df


def test_field_for_panel_and_flat() -> None:
    idx = pd.bdate_range("2020-01-01", periods=2)
    flat = pd.DataFrame({"Close": [1.0, 2.0], "Open": [3.0, 4.0]}, index=idx)
    cols = pd.MultiIndex.from_product([["AAPL"], ["Close", "Open"]], names=["ticker", "field"])
    panel = pd.DataFrame([[1.0, 3.0], [2.0, 4.0]], index=idx, columns=cols)
    assert isinstance(field_for(flat, "Close"), pd.Series)
    assert isinstance(field_for(panel, "Close"), pd.DataFrame)


def test_field_for_missing_column_raises() -> None:
    df = pd.DataFrame({"Close": [1.0]}, index=pd.bdate_range("2020-01-01", periods=1))
    with pytest.raises(KeyError):
        field_for(df, "Open")
