"""Tests for ml.lightgbm_model factory."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

lightgbm = pytest.importorskip("lightgbm")

from stock_rtx4060.ml.lightgbm_model import lightgbm_default_params, make_lightgbm  # noqa: E402


def test_lightgbm_default_params_cpu():
    params = lightgbm_default_params(device="cpu")
    assert params["n_estimators"] == 300
    assert params["max_depth"] == 4
    assert params["learning_rate"] == pytest.approx(0.04)
    assert params["subsample"] == pytest.approx(0.85)
    assert params["colsample_bytree"] == pytest.approx(0.85)
    assert params["min_data_in_leaf"] == 20
    assert params["reg_lambda"] == pytest.approx(1.5)
    assert "device_type" not in params


def test_lightgbm_default_params_gpu():
    params = lightgbm_default_params(device="gpu")
    assert params["device_type"] == "gpu"


def test_make_lightgbm_predict_proba_shape():
    np.random.seed(0)
    n = 100
    X = pd.DataFrame(np.random.randn(n, 5), columns=[f"f{i}" for i in range(5)])
    y = (X["f0"] + np.random.randn(n) * 0.1 > 0).astype(int)
    model = make_lightgbm(n_estimators=20, verbosity=-1)
    model.fit(X, y)
    proba = model.predict_proba(X)
    assert proba.shape == (n, 2)
    assert np.all((proba >= 0) & (proba <= 1))


def test_make_lightgbm_dart():
    model = make_lightgbm(boosting="dart", n_estimators=10, verbosity=-1)
    assert model.boosting_type == "dart"


def test_make_lightgbm_import_error(monkeypatch):
    """When lightgbm is unavailable, make_lightgbm should raise ImportError with hint."""
    # Force the module-internal import to fail
    monkeypatch.setitem(sys.modules, "lightgbm", None)
    # Force re-execution by removing cached attribute
    import importlib

    import stock_rtx4060.ml.lightgbm_model as lgb_mod

    importlib.reload(lgb_mod)
    with pytest.raises(ImportError, match="lightgbm"):
        lgb_mod.make_lightgbm()
    # Restore module so subsequent tests behave normally
    monkeypatch.delitem(sys.modules, "lightgbm", raising=False)
    importlib.reload(lgb_mod)
