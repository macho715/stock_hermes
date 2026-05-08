"""Tests for ml.hpo Optuna runner."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

optuna = pytest.importorskip("optuna")
xgb = pytest.importorskip("xgboost")

from stock_rtx4060.ml.cv import PurgedKFold  # noqa: E402
from stock_rtx4060.ml.hpo import run_hpo  # noqa: E402


@pytest.fixture
def synth_dataset():
    np.random.seed(7)
    n, p = 240, 6
    X = pd.DataFrame(np.random.randn(n, p), columns=[f"f{i}" for i in range(p)])
    # signal strong enough that 3 trials of XGB beat random Brier (0.25)
    y = pd.Series((X["f0"] + 0.3 * X["f1"] + np.random.randn(n) * 0.4 > 0).astype(int))
    return X, y


def test_run_hpo_basic(tmp_path, synth_dataset, monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file://{tmp_path / 'mlruns'}")
    X, y = synth_dataset
    cv = PurgedKFold(n_splits=3, embargo_pct=0.01)
    result = run_hpo(
        X,
        y,
        model="xgboost",
        n_trials=3,
        cv=cv,
        experiment="test_direction_v1",
    )
    assert isinstance(result, dict)
    assert isinstance(result["best_params"], dict)
    assert "best_value" in result
    # Brier scores are bounded in [0, 1]; random binary classifier averages 0.25.
    # With a real signal even 3 trials should beat 0.5.
    assert 0.0 <= result["best_value"] < 0.5
    assert result["study"] is not None


def test_run_hpo_invalid_model(synth_dataset):
    X, y = synth_dataset
    with pytest.raises(ValueError, match="unsupported"):
        run_hpo(X, y, model="random_forest", n_trials=1)  # type: ignore[arg-type]


def test_run_hpo_lightgbm_smoke(synth_dataset, tmp_path, monkeypatch):
    pytest.importorskip("lightgbm")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"file://{tmp_path / 'mlruns'}")
    X, y = synth_dataset
    cv = PurgedKFold(n_splits=3, embargo_pct=0.01)
    result = run_hpo(X, y, model="lightgbm", n_trials=2, cv=cv, experiment="lgbm_test")
    assert isinstance(result, dict)
    assert "best_params" in result
    assert 0.0 <= result["best_value"] <= 1.0


def test_run_hpo_optuna_missing(monkeypatch, synth_dataset):
    """When optuna is unavailable, run_hpo raises an informative ImportError."""
    monkeypatch.setitem(sys.modules, "optuna", None)
    import importlib

    import stock_rtx4060.ml.hpo as hpo_mod

    importlib.reload(hpo_mod)
    X, y = synth_dataset
    with pytest.raises(ImportError, match="optuna"):
        hpo_mod.run_hpo(X, y, n_trials=1)
    monkeypatch.delitem(sys.modules, "optuna", raising=False)
    importlib.reload(hpo_mod)
