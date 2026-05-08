"""Verify ModelConfig(cv_kind='purged') routes EnsemblePredictor through PurgedKFold."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _build_features() -> pd.DataFrame:
    from stock_rtx4060.feature_engine import TechnicalIndicators

    np.random.seed(11)
    n = 360
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame(
        {
            "Open": close * (1 + np.random.randn(n) * 0.003),
            "High": close * (1 + np.abs(np.random.randn(n)) * 0.005),
            "Low": close * (1 - np.abs(np.random.randn(n)) * 0.005),
            "Close": close,
            "Volume": np.random.randint(500_000, 2_000_000, n).astype(float),
        },
        index=dates,
    )
    return TechnicalIndicators(df).build_all(horizon=5).dropna()


def test_ensemble_purged_cv_runs():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    feat = _build_features()
    cfg = ModelConfig(
        model_kind="logistic",
        n_splits=3,
        lite=True,
        cv_kind="purged",
        embargo_pct=0.02,
    )
    ep = EnsemblePredictor(cfg)
    cv = ep.fit(feat)
    assert ep.trained is True
    assert isinstance(cv, list)
    assert len(cv) >= 2
    assert all("fold" in r and "auc" in r for r in cv)


def test_ensemble_default_cv_still_timeseries():
    """The default cv_kind must remain 'timeseries' (zero-regression contract)."""
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    feat = _build_features()
    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    assert cfg.cv_kind == "timeseries"
    ep = EnsemblePredictor(cfg)
    cv = ep.fit(feat)
    assert ep.trained is True
    assert len(cv) >= 2


def test_ensemble_lightgbm_kind():
    """LightGBM is now selectable via ModelConfig.model_kind='lightgbm'."""
    pytest.importorskip("lightgbm")
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    feat = _build_features()
    cfg = ModelConfig(model_kind="lightgbm", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    cv = ep.fit(feat)
    assert ep.trained is True
    assert len(cv) >= 2


def test_predict_proba_with_shap_returns_tuple():
    pytest.importorskip("shap")
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    feat = _build_features()
    cfg = ModelConfig(model_kind="xgb", xgb_device="cpu", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    ep.fit(feat)
    fc = ep.feature_cols
    X = feat.loc[:, fc].iloc[-30:]
    probs, shap_dict = ep.predict_proba_with_shap(X)
    assert len(probs) == len(X)
    assert isinstance(shap_dict, dict)
