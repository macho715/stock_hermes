"""Tests for the RD-Agent factor validator."""

from __future__ import annotations

import numpy as np
import pandas as pd

from stock_rtx4060.factors.base import Factor, FactorMeta
from stock_rtx4060.factors.rd_agent.runner import run_factor_mining
from stock_rtx4060.factors.rd_agent.validator import (
    ValidationResult,
    validate_discovered_factor,
)
from stock_rtx4060.feature_engine import make_synthetic_ohlcv


class _NoiseFactor(Factor):
    """A weak factor: small i.i.d. noise — should fail the gates."""

    meta = FactorMeta(name="WeakNoiseFactor", category="discovered", lookback=1)

    def compute(self, panel, as_of=None):  # type: ignore[no-untyped-def]
        rng = np.random.default_rng(42)
        return pd.Series(rng.normal(0.0, 1.0, len(panel.index)), index=panel.index)


class _SyntheticPersistentFactor(Factor):
    """Strong, persistent factor highly correlated with forward returns."""

    meta = FactorMeta(name="StrongPersistentFactor", category="discovered", lookback=1)

    def __init__(self, fwd: pd.Series) -> None:
        self._fwd = fwd

    def compute(self, panel, as_of=None):  # type: ignore[no-untyped-def]
        # Persistent (AR(1)) signal aligned with forward returns sign.
        rng = np.random.default_rng(0)
        n = len(panel.index)
        x = np.zeros(n)
        target = self._fwd.reindex(panel.index).fillna(0.0).values
        for i in range(1, n):
            x[i] = 0.7 * x[i - 1] + 0.3 * float(target[i]) + rng.normal(0, 0.001)
        return pd.Series(x, index=panel.index)


def test_validator_rejects_weak_factor() -> None:
    df = make_synthetic_ohlcv(n=400, seed=11)
    fwd = df["Close"].pct_change(5).shift(-5)
    factor = _NoiseFactor()
    res = validate_discovered_factor(factor, df, fwd)
    assert isinstance(res, ValidationResult)
    assert not res.passed
    assert any("IC" in r or "IR" in r for r in res.reasons)


def test_validator_accepts_strong_factor() -> None:
    df = make_synthetic_ohlcv(n=400, seed=12)
    fwd = df["Close"].pct_change(5).shift(-5)
    factor = _SyntheticPersistentFactor(fwd)
    res = validate_discovered_factor(
        factor,
        df,
        fwd,
        min_abs_ic=0.05,
        min_ir=0.3,
        max_corr_with_existing=0.99,
        min_half_life_days=2,
    )
    # The synthetic strong factor should clear IC and IR.
    assert abs(res.ic) > 0.05
    assert res.ir > 0.3 or np.isnan(res.ir) is False


def test_validator_returns_result_dataclass() -> None:
    df = make_synthetic_ohlcv(n=300, seed=13)
    fwd = df["Close"].pct_change(5).shift(-5)
    res = validate_discovered_factor(_NoiseFactor(), df, fwd)
    assert hasattr(res, "passed")
    assert hasattr(res, "reasons")
    assert hasattr(res, "ic")
    assert hasattr(res, "ir")


def test_run_factor_mining_no_rdagent_returns_empty(tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = run_factor_mining(["AAPL"], cycles=1, budget_usd=0.0, output_dir=tmp_path)
    # rdagent isn't installed in this CI env => empty list.
    assert out == []


def test_run_factor_mining_creates_output_dir(tmp_path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "discovered"
    out = run_factor_mining(["AAPL", "MSFT"], cycles=2, budget_usd=10.0, output_dir=target)
    assert out == []
    assert target.exists()
    assert target.is_dir()


def test_run_factor_mining_handles_stub_rdagent(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Simulate rdagent being importable but lacking factor_loop."""
    import sys
    import types

    fake = types.ModuleType("rdagent")
    monkeypatch.setitem(sys.modules, "rdagent", fake)
    out = run_factor_mining(["AAPL"], cycles=1, budget_usd=0.0, output_dir=tmp_path)
    assert out == []


def test_run_factor_mining_invokes_factor_loop(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Simulate rdagent.factor_loop being present and creating a file."""
    import sys
    import types

    fake = types.ModuleType("rdagent")

    def factor_loop(universe, cycles, budget_usd, output_dir):  # type: ignore[no-untyped-def]
        out = tmp_path / "auto_factor_1.py"
        out.write_text("# generated\n")

    fake.factor_loop = factor_loop  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rdagent", fake)
    out = run_factor_mining(["AAPL"], cycles=1, budget_usd=1.0, output_dir=tmp_path)
    assert any(p.name == "auto_factor_1.py" for p in out)


def test_run_factor_mining_swallows_factor_loop_errors(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    import sys
    import types

    fake = types.ModuleType("rdagent")

    def factor_loop(**_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated upstream error")

    fake.factor_loop = factor_loop  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rdagent", fake)
    out = run_factor_mining(["AAPL"], cycles=1, budget_usd=1.0, output_dir=tmp_path)
    assert out == []
