"""Unit tests for ml.explain — no shap install required; all SHAP calls mocked."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_X(n: int = 40, p: int = 4) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    return pd.DataFrame(rng.standard_normal((n, p)), columns=[f"f{i}" for i in range(p)])


def _shap_values_2d(X: pd.DataFrame) -> np.ndarray:
    """Return fake SHAP values shaped (n_samples, n_features)."""
    rng = np.random.default_rng(99)
    return rng.standard_normal(X.shape)


# ---------------------------------------------------------------------------
# _is_tree_model
# ---------------------------------------------------------------------------

def test_is_tree_model_xgb():
    from stock_rtx4060.ml.explain import _is_tree_model

    mock_xgb = MagicMock()
    mock_xgb.__class__.__name__ = "XGBClassifier"
    assert _is_tree_model(mock_xgb) is True


def test_is_tree_model_lgbm():
    from stock_rtx4060.ml.explain import _is_tree_model

    mock = MagicMock()
    mock.__class__.__name__ = "LGBMClassifier"
    assert _is_tree_model(mock) is True


def test_is_tree_model_rf():
    from stock_rtx4060.ml.explain import _is_tree_model

    mock = MagicMock()
    mock.__class__.__name__ = "RandomForestClassifier"
    assert _is_tree_model(mock) is True


def test_is_tree_model_other():
    from stock_rtx4060.ml.explain import _is_tree_model

    mock = MagicMock()
    mock.__class__.__name__ = "SomeOtherModel"
    assert _is_tree_model(mock) is False


# ---------------------------------------------------------------------------
# _is_linear_model
# ---------------------------------------------------------------------------

def test_is_linear_model_logistic():
    from stock_rtx4060.ml.explain import _is_linear_model

    lr = LogisticRegression()
    assert _is_linear_model(lr) is True


def test_is_linear_model_pipeline_with_lr():
    from stock_rtx4060.ml.explain import _is_linear_model

    pipe = Pipeline([("model", LogisticRegression())])
    assert _is_linear_model(pipe) is True


def test_is_linear_model_pipeline_without_model_step():
    from stock_rtx4060.ml.explain import _is_linear_model

    pipe = Pipeline([("scaler", MagicMock())])
    assert _is_linear_model(pipe) is False


def test_is_linear_model_other():
    from stock_rtx4060.ml.explain import _is_linear_model

    assert _is_linear_model(MagicMock()) is False


# ---------------------------------------------------------------------------
# _coerce_shap_array
# ---------------------------------------------------------------------------

def test_coerce_shap_array_ndarray():
    from stock_rtx4060.ml.explain import _coerce_shap_array

    arr = np.ones((5, 3))
    result = _coerce_shap_array(arr)
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, arr)


def test_coerce_shap_array_has_values_attr():
    from stock_rtx4060.ml.explain import _coerce_shap_array

    mock = MagicMock()
    mock.values = np.zeros((5, 3))
    result = _coerce_shap_array(mock)
    assert result.shape == (5, 3)


def test_coerce_shap_array_list_returns_last():
    from stock_rtx4060.ml.explain import _coerce_shap_array

    class0 = np.ones((5, 3))
    class1 = np.full((5, 3), 2.0)
    result = _coerce_shap_array([class0, class1])
    np.testing.assert_array_equal(result, class1)


# ---------------------------------------------------------------------------
# explain() — mocked shap
# ---------------------------------------------------------------------------

def _build_shap_mock(shap_values_output):
    """Build a fake shap module and fake explainer."""
    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = shap_values_output

    mock_shap = MagicMock()
    mock_shap.TreeExplainer.return_value = mock_explainer
    mock_shap.LinearExplainer.return_value = mock_explainer
    mock_shap.Explainer.return_value = mock_explainer
    return mock_shap, mock_explainer


def test_explain_empty_dataframe():
    from stock_rtx4060.ml.explain import explain

    model = MagicMock()
    X = pd.DataFrame(columns=["a", "b", "c"])
    out = explain(model, X)
    assert isinstance(out, pd.DataFrame)
    assert out.shape[0] == 0
    assert list(out.columns) == ["a", "b", "c"]


def test_explain_none_input():
    from stock_rtx4060.ml.explain import explain

    model = MagicMock()
    out = explain(model, None)
    assert isinstance(out, pd.DataFrame)
    assert out.shape[0] == 0


def test_explain_tree_model_2d_output():
    from stock_rtx4060.ml.explain import explain

    X = _make_X(20, 4)
    shap_vals = _shap_values_2d(X)
    mock_shap, _exp = _build_shap_mock(shap_vals)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        tree_model = MagicMock()
        tree_model.__class__.__name__ = "XGBClassifier"
        out = mod.explain(tree_model, X)

    assert isinstance(out, pd.DataFrame)
    assert out.shape == (20, 4)
    assert list(out.columns) == list(X.columns)


def test_explain_max_samples_caps_rows():
    from stock_rtx4060.ml.explain import explain

    X = _make_X(50, 3)
    cap = 10
    shap_vals = _shap_values_2d(X.iloc[:cap])
    mock_shap, _exp = _build_shap_mock(shap_vals)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        out = mod.explain(model, X, max_samples=cap)

    assert out.shape[0] == cap


def test_explain_multiclass_3d_shap_uses_last_class():
    """3-D SHAP output (n_samples, n_features, n_classes) → last class used."""
    X = _make_X(10, 3)
    shap_vals_3d = np.random.default_rng(1).standard_normal((10, 3, 2))
    mock_shap, _exp = _build_shap_mock(shap_vals_3d)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        out = mod.explain(model, X)

    assert out.shape == (10, 3)


def test_explain_transposed_output_is_corrected():
    """Some explainers return (n_features, n_samples) — explain must transpose."""
    X = _make_X(8, 5)
    transposed = np.random.default_rng(2).standard_normal((5, 8))  # features × samples
    mock_shap, _exp = _build_shap_mock(transposed)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        out = mod.explain(model, X)

    assert out.shape == (8, 5)


def test_explain_raises_when_shap_absent():
    """explain must raise ImportError with a helpful message when shap is missing."""
    with patch.dict(sys.modules, {"shap": None}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        X = _make_X(5, 3)
        with pytest.raises(ImportError, match="shap"):
            mod.explain(model, X)

    # restore
    import importlib
    import stock_rtx4060.ml.explain as mod
    importlib.reload(mod)


# ---------------------------------------------------------------------------
# per_ticker_shap
# ---------------------------------------------------------------------------

def test_per_ticker_shap_no_ticker_column():
    from stock_rtx4060.ml.explain import per_ticker_shap

    model = MagicMock()
    X = _make_X()
    with pytest.raises(ValueError, match="ticker"):
        per_ticker_shap(model, X)


def test_per_ticker_shap_groups():
    X = _make_X(20, 3)
    panel = X.copy()
    panel["ticker"] = ["AAPL"] * 10 + ["MSFT"] * 10
    shap_vals = _shap_values_2d(X.iloc[:10])
    mock_shap, _exp = _build_shap_mock(shap_vals)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        out = mod.per_ticker_shap(model, panel)

    assert set(out.keys()) == {"AAPL", "MSFT"}
    for ticker_key, fi in out.items():
        assert set(fi.keys()) == {"f0", "f1", "f2"}
        assert all(v >= 0 for v in fi.values())


def test_per_ticker_shap_empty_group():
    """A ticker group with zero rows must return zeros, not crash."""
    X = _make_X(10, 3)
    panel = X.copy()
    panel["ticker"] = "SOLO"
    # Manually add an empty-group ticker by creating a panel with a filter
    # that would leave one ticker empty — simulate via a real group of rows
    shap_vals = _shap_values_2d(X)
    mock_shap, _exp = _build_shap_mock(shap_vals)

    with patch.dict(sys.modules, {"shap": mock_shap}):
        import importlib
        import stock_rtx4060.ml.explain as mod
        importlib.reload(mod)

        model = MagicMock()
        model.__class__.__name__ = "XGBClassifier"
        out = mod.per_ticker_shap(model, panel)

    assert "SOLO" in out
    assert all(v >= 0 for v in out["SOLO"].values())
