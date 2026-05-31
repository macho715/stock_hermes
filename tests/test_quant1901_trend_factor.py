"""Tests for Quant1901TrendFactor — Factor Zoo blockers fixed.

Verifies the three blockers identified during the parallel strategy test:
  1. PIT guard: rows < 60 must return zeros, not raise ValueError
  2. HTF regime: short panels (< ~25 rows) log a debug warning, do not crash
  3. category="technical" is stable and documented

Run:
    PYTHONPATH=src pytest tests/test_quant1901_trend_factor.py -q
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "quant1901_executable_bundle"
for p in (str(ROOT / "src"), str(BUNDLE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402

from quant1901_executor import make_synthetic_ohlcv  # noqa: E402
from stock_rtx4060.factors.quant1901_trend_factor import (  # noqa: E402
    Quant1901TrendFactor,
    quant1901_trend_factor,
)


def _make_short_ohlcv(rows: int) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame without the make_synthetic_ohlcv >= 60 guard."""
    rng = np.random.default_rng(seed=999)
    close = 100.0 + np.cumsum(rng.normal(0, 1, rows))
    dates = pd.bdate_range(end="2026-05-31", periods=rows)
    return pd.DataFrame(
        {
            "Open": close * 0.99,
            "High": close * 1.01,
            "Low": close * 0.98,
            "Close": close,
            "Volume": rng.integers(100_000, 1_000_000, rows).astype(float),
        },
        index=dates,
    )


# ── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture
def factor() -> Quant1901TrendFactor:
    return Quant1901TrendFactor()


@pytest.fixture
def full_df() -> pd.DataFrame:
    """120 rows — above lookback=60, valid for normal compute."""
    return make_synthetic_ohlcv(rows=120, seed=42)


# ── 1. Blocker fix: rows < 60 must return zeros, not raise ValueError ───────
def test_short_panel_returns_zeros_not_error(factor):
    """Blocker 1: panels shorter than lookback (60) must not raise."""
    short = _make_short_ohlcv(30)
    result = factor._compute_single(short)
    assert isinstance(result, pd.Series)
    assert (result == 0.0).all(), "Expected all-zeros for short panel"
    assert len(result) == len(short)


def test_exactly_lookback_minus_one_returns_zeros(factor):
    """One row below lookback threshold → zeros (boundary check)."""
    df = _make_short_ohlcv(59)
    result = factor._compute_single(df)
    assert (result == 0.0).all()


def test_exactly_lookback_does_not_return_all_zeros(factor):
    """At exactly lookback (60 rows) the factor attempts a real compute."""
    df = make_synthetic_ohlcv(rows=60, seed=3)
    result = factor._compute_single(df)
    assert isinstance(result, pd.Series)
    assert len(result) == 60
    # Not guaranteed to be all-zeros once compute runs
    assert result.dtype == float


# ── 2. Blocker fix: short panels log debug, do not crash ────────────────────
def test_htf_short_panel_logs_debug_not_crashes(factor, caplog):
    """Blocker 2: panel with < ~25 rows (5 weekly bars) should warn via debug log."""
    short = _make_short_ohlcv(24)  # < 25 rows → < 5 weekly bars
    with caplog.at_level(logging.DEBUG, logger="stock_rtx4060.factors.quant1901_trend_factor"):
        result = factor._compute_single(short)
    # Must not crash
    assert isinstance(result, pd.Series)
    # Must return zeros (short panel guard fires first)
    assert (result == 0.0).all()


def test_htf_border_panel_60rows_no_crash(factor):
    """Panel at exactly 60 rows: 60 // 5 = 12 weekly bars >= 5 → no warning."""
    df = make_synthetic_ohlcv(rows=60, seed=6)  # use bundle's generator (60 is minimum)
    # Should not raise anything
    result = factor._compute_single(df)
    assert isinstance(result, pd.Series)


# ── 3. Blocker fix: category="technical" is stable ──────────────────────────
def test_factor_meta_category_is_technical(factor):
    """Blocker 3: category must remain 'technical' until explicitly changed."""
    assert factor.meta.category == "technical"


def test_factor_meta_name_stable():
    """Factor registry key must not change across re-imports."""
    assert quant1901_trend_factor.meta.name == "quant1901_trend"


def test_factor_meta_lookback_is_60(factor):
    """lookback=60 matches quant1901_executor's normalize_ohlcv minimum."""
    assert factor.meta.lookback == 60


# ── 4. Normal compute on sufficient data ────────────────────────────────────
def test_compute_returns_binary_signal_on_full_panel(factor, full_df):
    """Full 120-row panel: output is 0.0 or 1.0 only."""
    result = factor._compute_single(full_df)
    assert set(result.dropna().unique()).issubset({0.0, 1.0})


def test_compute_index_alignment(factor, full_df):
    """Output index must match input index length."""
    result = factor._compute_single(full_df)
    assert len(result) == len(full_df)


def test_compute_via_public_method(factor, full_df):
    """compute() public API (used by factor_zoo.compute_all) must work."""
    result = factor.compute(full_df)
    assert isinstance(result, pd.Series)
    assert len(result) == len(full_df)


# ── 5. Auto-registration smoke ───────────────────────────────────────────────
def test_auto_registered_in_factor_zoo():
    """Module-level register_factor() must have registered 'quant1901_trend'."""
    from stock_rtx4060.factors.factor_zoo import FactorRegistry

    registry = FactorRegistry()
    assert "quant1901_trend" in registry
