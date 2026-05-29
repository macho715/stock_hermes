"""Tests for TFT model stub — Wave 4 BEST-3."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Import guard
# ---------------------------------------------------------------------------

from stock_rtx4060.ml.tft_model import (
    TFTPredictor,
    _TFT_AVAILABLE,
    make_tft_predictor,
    TFT_MODEL_ENABLED,
)


def test_tft_available_is_bool():
    assert isinstance(_TFT_AVAILABLE, bool)


def test_tft_model_enabled_is_bool():
    assert isinstance(TFT_MODEL_ENABLED, bool)


# ---------------------------------------------------------------------------
# make_tft_predictor factory
# ---------------------------------------------------------------------------

def test_make_tft_predictor_disabled_returns_none(monkeypatch):
    monkeypatch.setattr("stock_rtx4060.ml.tft_model.TFT_MODEL_ENABLED", False)
    result = make_tft_predictor()
    assert result is None


def test_make_tft_predictor_enabled_returns_instance(monkeypatch):
    monkeypatch.setattr("stock_rtx4060.ml.tft_model.TFT_MODEL_ENABLED", True)
    result = make_tft_predictor()
    assert isinstance(result, TFTPredictor)


# ---------------------------------------------------------------------------
# TFTPredictor stub behaviour
# ---------------------------------------------------------------------------

def test_tft_predictor_predict_returns_half_without_training():
    """Untrained predictor returns 0.5 for every sample."""
    predictor = TFTPredictor()
    result = predictor.predict([1, 2, 3])
    assert result == [0.5, 0.5, 0.5]


def test_tft_predictor_predict_length_matches_input():
    predictor = TFTPredictor()
    result = predictor.predict(list(range(10)))
    assert len(result) == 10


def test_tft_predictor_is_available_false_when_not_trained():
    predictor = TFTPredictor()
    # is_available requires both _TFT_AVAILABLE and _trained
    assert predictor.is_available is False


def test_tft_predictor_fit_noop_without_torch():
    """fit() must not raise even without torch/pytorch_forecasting."""
    if _TFT_AVAILABLE:
        pytest.skip("torch available — skip no-op test")
    predictor = TFTPredictor()
    # Should not raise
    predictor.fit([], [])


# ---------------------------------------------------------------------------
# EnsembleModel integration: tft_prob in predict() output
# ---------------------------------------------------------------------------

def test_ensemble_model_predict_includes_tft_prob(monkeypatch):
    """EnsembleModel.predict() must include tft_prob key."""
    import numpy as np
    import pandas as pd
    from stock_rtx4060.ensemble_model import EnsemblePredictor as EnsembleModel, ModelConfig as EnsembleConfig

    monkeypatch.setattr("stock_rtx4060.ml.tft_model.TFT_MODEL_ENABLED", True)

    cfg = EnsembleConfig(model_kind="logistic", n_splits=2, gap=0, cv_kind="tscv")
    model = EnsembleModel(cfg)

    # Build minimal feature_df
    rng = np.random.default_rng(42)
    n = 100
    df = pd.DataFrame(rng.normal(size=(n, 5)), columns=[f"f{i}" for i in range(5)])
    df["target_direction"] = (rng.normal(size=n) > 0).astype(int)
    model.fit(df)

    result = model.predict(df.tail(5))
    assert "tft_prob" in result
    assert isinstance(result["tft_prob"], float)


def test_ensemble_model_predict_tft_prob_zero_point_five_when_disabled(monkeypatch):
    """When TFT disabled, tft_prob should be 0.5."""
    import numpy as np
    import pandas as pd
    from stock_rtx4060.ensemble_model import EnsemblePredictor as EnsembleModel, ModelConfig as EnsembleConfig

    monkeypatch.setattr("stock_rtx4060.ml.tft_model.TFT_MODEL_ENABLED", False)

    cfg = EnsembleConfig(model_kind="logistic", n_splits=2, gap=0, cv_kind="tscv")
    model = EnsembleModel(cfg)

    rng = np.random.default_rng(0)
    n = 100
    df = pd.DataFrame(rng.normal(size=(n, 5)), columns=[f"f{i}" for i in range(5)])
    df["target_direction"] = (rng.normal(size=n) > 0).astype(int)
    model.fit(df)

    result = model.predict(df.tail(5))
    assert result["tft_prob"] == 0.5
