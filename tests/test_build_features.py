"""Regression tests for the new ``feature_engine.build_features`` helper."""

from __future__ import annotations

import pandas as pd

from stock_rtx4060.feature_engine import (
    TechnicalIndicators,
    build_features,
    make_synthetic_ohlcv,
)


def test_default_matches_legacy_pipeline() -> None:
    df = make_synthetic_ohlcv(n=400, seed=99)
    new = build_features(df)
    legacy = TechnicalIndicators(df).build_all(horizon=5)
    pd.testing.assert_frame_equal(new, legacy)


def test_factors_argument_appends_columns() -> None:
    df = make_synthetic_ohlcv(n=400, seed=100)
    out = build_features(df, factors=["RSI14", "Alpha101"])
    assert "RSI14" in out.columns
    assert "Alpha101" in out.columns


def test_unknown_factor_silently_skipped() -> None:
    df = make_synthetic_ohlcv(n=300)
    out = build_features(df, factors=["__no_such_factor__"])
    legacy = TechnicalIndicators(df).build_all(horizon=5)
    pd.testing.assert_frame_equal(out, legacy)


def test_horizon_propagates_to_targets() -> None:
    df = make_synthetic_ohlcv(n=400)
    out_short = build_features(df, horizon=3)
    out_long = build_features(df, horizon=20)
    # Forward-return horizons differ -> target columns differ.
    assert not out_short["target_return"].equals(out_long["target_return"])
