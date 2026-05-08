"""Tests for ml.explain SHAP wrapper."""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

shap = pytest.importorskip("shap")
xgb = pytest.importorskip("xgboost")

from stock_rtx4060.ml.explain import explain, per_ticker_shap  # noqa: E402


@pytest.fixture
def fitted_xgb():
    np.random.seed(123)
    n, p = 100, 6
    X = pd.DataFrame(np.random.randn(n, p), columns=[f"f{i}" for i in range(p)])
    y = (X.sum(axis=1) > 0).astype(int)
    model = xgb.XGBClassifier(n_estimators=20, max_depth=3, tree_method="hist", verbosity=0)
    model.fit(X, y)
    return model, X, y


def test_explain_shape(fitted_xgb):
    model, X, _y = fitted_xgb
    sample = X.iloc[:50]
    out = explain(model, sample, max_samples=200)
    assert isinstance(out, pd.DataFrame)
    assert out.shape == (50, X.shape[1])
    assert list(out.columns) == list(X.columns)


def test_explain_max_samples_caps(fitted_xgb):
    model, X, _y = fitted_xgb
    out = explain(model, X, max_samples=10)
    assert out.shape == (10, X.shape[1])


def test_explain_empty_input(fitted_xgb):
    model, X, _y = fitted_xgb
    out = explain(model, X.iloc[:0])
    assert out.shape[0] == 0


def test_per_ticker_shap_groups(fitted_xgb):
    model, X, _y = fitted_xgb
    panel = X.copy()
    tickers = ["AAPL"] * 50 + ["MSFT"] * 50
    panel["ticker"] = tickers
    out = per_ticker_shap(model, panel)
    assert set(out.keys()) == {"AAPL", "MSFT"}
    for _ticker, fi in out.items():
        assert set(fi.keys()) == set(X.columns)
        assert all(v >= 0 for v in fi.values())


def test_per_ticker_shap_missing_ticker_column(fitted_xgb):
    model, X, _y = fitted_xgb
    with pytest.raises(ValueError, match="ticker"):
        per_ticker_shap(model, X)


def test_explain_logistic(fitted_xgb):
    """Linear models should be explained via shap.LinearExplainer."""
    from sklearn.linear_model import LogisticRegression

    _model, X, y = fitted_xgb
    lr = LogisticRegression(max_iter=200).fit(X, y)
    out = explain(lr, X.iloc[:30])
    assert out.shape == (30, X.shape[1])


def test_explain_shap_missing(monkeypatch, fitted_xgb):
    """When shap is not importable, explain raises a clear ImportError."""
    model, X, _y = fitted_xgb
    monkeypatch.setitem(sys.modules, "shap", None)
    import importlib

    import stock_rtx4060.ml.explain as exp_mod

    importlib.reload(exp_mod)
    with pytest.raises(ImportError, match="shap"):
        exp_mod.explain(model, X.iloc[:5])
    # Restore for subsequent tests
    monkeypatch.delitem(sys.modules, "shap", raising=False)
    importlib.reload(exp_mod)
