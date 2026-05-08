"""SHAP-based model interpretation utilities.

Functions:
- :func:`explain` returns per-row SHAP values for any tree / linear model
  understood by SHAP, with a graceful fallback to ``shap.Explainer``.
- :func:`per_ticker_shap` aggregates mean-abs SHAP per feature, grouped by
  the ``ticker`` column of a panel dataframe.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def _require_shap() -> Any:
    try:
        import shap  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError("shap is required for ml.explain. Install with: pip install 'shap>=0.46'") from exc
    return shap


def _is_tree_model(model: Any) -> bool:
    cls = type(model).__name__.lower()
    return any(k in cls for k in ("xgb", "lgbm", "lightgbm", "randomforest", "gradientboost", "extratrees"))


def _is_linear_model(model: Any) -> bool:
    if isinstance(model, LogisticRegression):
        return True
    if isinstance(model, Pipeline):
        try:
            return isinstance(model.named_steps["model"], LogisticRegression)
        except KeyError:
            return False
    return False


def _build_explainer(model: Any, X: pd.DataFrame) -> Any:
    shap = _require_shap()
    if _is_tree_model(model):
        return shap.TreeExplainer(model)
    if _is_linear_model(model):
        return shap.LinearExplainer(model, X)
    return shap.Explainer(model, X)


def explain(model: Any, X: pd.DataFrame, *, max_samples: int = 200) -> pd.DataFrame:
    """Return a DataFrame of SHAP values, one row per input, columns = features.

    When the underlying explainer returns a multi-class output (e.g. binary
    classification with two columns), the *positive*-class column is used.
    """
    if X is None or len(X) == 0:
        return pd.DataFrame(columns=list(getattr(X, "columns", [])))

    sample = X.iloc[:max_samples] if len(X) > max_samples else X
    explainer = _build_explainer(model, sample)
    raw = explainer.shap_values(sample) if hasattr(explainer, "shap_values") else explainer(sample)

    values = _coerce_shap_array(raw)
    if values.ndim == 3:
        # (n_samples, n_features, n_classes) → take last class
        values = values[..., -1]
    if values.shape[0] != len(sample):
        # some explainers return (n_features, n_samples)
        values = values.T
    return pd.DataFrame(values, index=sample.index, columns=list(sample.columns))


def _coerce_shap_array(raw: Any) -> np.ndarray:
    """Normalise SHAP outputs to a numpy array."""
    if hasattr(raw, "values"):
        return np.asarray(raw.values)
    if isinstance(raw, list):
        # binary classifiers sometimes return [class0, class1] arrays
        return np.asarray(raw[-1])
    return np.asarray(raw)


def per_ticker_shap(model: Any, panel: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Compute mean-abs SHAP per feature, grouped by ``ticker``.

    The panel must contain a ``ticker`` column; remaining numeric columns
    are treated as model features.
    """
    if "ticker" not in panel.columns:
        raise ValueError("panel must contain a 'ticker' column")

    feature_cols = [c for c in panel.columns if c != "ticker"]
    out: dict[str, dict[str, float]] = {}
    for ticker, group in panel.groupby("ticker"):
        X = group.loc[:, feature_cols]
        if len(X) == 0:
            out[str(ticker)] = {c: 0.0 for c in feature_cols}
            continue
        shap_df = explain(model, X)
        out[str(ticker)] = shap_df.abs().mean().to_dict()
    return out


__all__ = ["explain", "per_ticker_shap"]
