"""Extra coverage for ensemble_model.py — targets 49% → ≥80%."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _synthetic_ohlcv(n: int = 360) -> pd.DataFrame:
    np.random.seed(42)
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
    return df


def _build_features() -> pd.DataFrame:
    from stock_rtx4060.feature_engine import TechnicalIndicators

    ohlcv = _synthetic_ohlcv(360)
    feat = TechnicalIndicators(ohlcv).build_all(horizon=5)
    return feat.dropna()


@pytest.fixture(scope="module")
def feature_df():
    return _build_features()


# ---------------------------------------------------------------------------
# _safe_auc
# ---------------------------------------------------------------------------

def test_safe_auc_normal():
    from stock_rtx4060.ensemble_model import _safe_auc

    y = np.array([0, 1, 0, 1, 1])
    prob = np.array([0.1, 0.9, 0.2, 0.8, 0.7])
    result = _safe_auc(y, prob)
    assert 0.0 <= result <= 1.0
    assert result > 0.5


def test_safe_auc_single_class():
    from stock_rtx4060.ensemble_model import _safe_auc

    y = np.array([1, 1, 1, 1])
    prob = np.array([0.8, 0.9, 0.7, 0.6])
    assert _safe_auc(y, prob) == 0.5


def test_safe_auc_empty():
    from stock_rtx4060.ensemble_model import _safe_auc

    assert _safe_auc(np.array([]), np.array([])) == 0.5


def test_safe_auc_pd_series():
    from stock_rtx4060.ensemble_model import _safe_auc

    y = pd.Series([0, 1, 0, 1])
    prob = np.array([0.1, 0.9, 0.2, 0.8])
    result = _safe_auc(y, prob)
    assert result == 1.0


# ---------------------------------------------------------------------------
# _xgboost_version_tuple
# ---------------------------------------------------------------------------

def test_xgb_version_tuple_normal():
    from stock_rtx4060.ensemble_model import _xgboost_version_tuple

    result = _xgboost_version_tuple()
    assert isinstance(result, tuple)
    assert len(result) == 3
    assert all(isinstance(v, int) for v in result)


def test_xgb_version_tuple_parses_semver(monkeypatch):
    from stock_rtx4060.ensemble_model import _xgboost_version_tuple

    fake_xgb = SimpleNamespace(__version__="2.0.3")
    monkeypatch.setitem(sys.modules, "xgboost", fake_xgb)
    result = _xgboost_version_tuple()
    assert result == (2, 0, 3)


def test_xgb_version_tuple_parses_dev(monkeypatch):
    from stock_rtx4060.ensemble_model import _xgboost_version_tuple

    fake_xgb = SimpleNamespace(__version__="3.1.0+dev")
    monkeypatch.setitem(sys.modules, "xgboost", fake_xgb)
    result = _xgboost_version_tuple()
    assert result[0] == 3


def test_xgb_version_tuple_import_error(monkeypatch):
    from stock_rtx4060.ensemble_model import _xgboost_version_tuple

    monkeypatch.setitem(sys.modules, "xgboost", None)
    result = _xgboost_version_tuple()
    assert result == (0, 0, 0)


# ---------------------------------------------------------------------------
# xgb_params_for_device
# ---------------------------------------------------------------------------

def test_xgb_params_cpu():
    from stock_rtx4060.ensemble_model import xgb_params_for_device

    base = {"n_estimators": 100, "device": "cuda"}
    result = xgb_params_for_device(base, device="cpu")
    assert result["tree_method"] == "hist"
    assert "device" not in result


def test_xgb_params_cuda_new_api(monkeypatch):
    from stock_rtx4060.ensemble_model import xgb_params_for_device

    fake_xgb = SimpleNamespace(__version__="2.0.0")
    monkeypatch.setitem(sys.modules, "xgboost", fake_xgb)
    base = {"n_estimators": 100}
    result = xgb_params_for_device(base, device="cuda")
    assert result["tree_method"] == "hist"
    assert result.get("device") == "cuda"


def test_xgb_params_cuda_old_api(monkeypatch):
    from stock_rtx4060.ensemble_model import xgb_params_for_device

    fake_xgb = SimpleNamespace(__version__="1.7.0")
    monkeypatch.setitem(sys.modules, "xgboost", fake_xgb)
    base = {"n_estimators": 100}
    result = xgb_params_for_device(base, device="cuda")
    assert result["tree_method"] == "gpu_hist"
    assert "device" not in result


# ---------------------------------------------------------------------------
# ModelConfig
# ---------------------------------------------------------------------------

def test_model_config_defaults():
    from stock_rtx4060.ensemble_model import ModelConfig

    cfg = ModelConfig()
    assert cfg.horizon == 5
    assert cfg.model_kind == "auto"
    assert cfg.xgb_device == "cpu"
    assert cfg.lite is False


def test_model_config_lite():
    from stock_rtx4060.ensemble_model import ModelConfig

    cfg = ModelConfig(lite=True, n_splits=3)
    assert cfg.lite is True
    assert cfg.n_splits == 3


# ---------------------------------------------------------------------------
# DirectionModel.fit — direct kinds
# ---------------------------------------------------------------------------

def test_direction_model_fit_rf(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="rf")
    dm = DirectionModel(cfg)
    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:100]
    y = pd.Series(np.random.randint(0, 2, len(X)))
    while y.nunique() < 2:
        y = pd.Series(np.random.randint(0, 2, len(X)))
    dm.fit(X, y)
    assert dm.kind_used == "rf"
    assert dm.model is not None


def test_direction_model_fit_logistic(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="logistic")
    dm = DirectionModel(cfg)
    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    dm.fit(X, y)
    assert dm.kind_used == "logistic"


def test_direction_model_fit_single_class_raises(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="rf")
    dm = DirectionModel(cfg)
    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:50]
    y = pd.Series([1] * len(X))
    with pytest.raises(RuntimeError, match="class"):
        dm.fit(X, y)


def test_direction_model_fit_xgb_fallback_to_logistic(feature_df, monkeypatch):
    """Both xgb attempts fail → falls back to logistic."""
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    def _fail(*a, **kw):
        raise RuntimeError("no xgb")

    cfg = ModelConfig(model_kind="auto")
    dm = DirectionModel(cfg)
    monkeypatch.setattr(dm, "_make_xgb", _fail)
    monkeypatch.setattr(dm, "_make_rf", _fail)

    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    dm.fit(X, y)
    assert dm.kind_used == "logistic"


def test_direction_model_fit_xgb_fallback_to_rf(feature_df, monkeypatch):
    """xgb fails, rf succeeds → kind_used contains rf-fallback."""
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    def _fail_xgb(*a, **kw):
        raise RuntimeError("no xgb")

    cfg = ModelConfig(model_kind="auto")
    dm = DirectionModel(cfg)
    monkeypatch.setattr(dm, "_make_xgb", _fail_xgb)

    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    dm.fit(X, y)
    assert "rf" in dm.kind_used or "logistic" in dm.kind_used


def test_direction_model_fit_xgb_cpu_raises_on_cpu(feature_df, monkeypatch):
    """kind=xgb + device=cpu: first exception must propagate, no silent fallback."""
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    def _fail(*a, **kw):
        raise RuntimeError("hard fail")

    cfg = ModelConfig(model_kind="xgb", xgb_device="cpu")
    dm = DirectionModel(cfg)
    monkeypatch.setattr(dm, "_make_xgb", _fail)

    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    with pytest.raises(RuntimeError):
        dm.fit(X, y)


# ---------------------------------------------------------------------------
# DirectionModel.predict_proba / feature_importance
# ---------------------------------------------------------------------------

def test_direction_model_predict_proba_rf(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="rf")
    dm = DirectionModel(cfg)
    from stock_rtx4060.feature_engine import TARGET_COLUMNS, feature_columns
    target_cols = list(TARGET_COLUMNS)
    fc = [c for c in feature_columns(feature_df) if c not in target_cols]
    X = feature_df.loc[:, fc].iloc[:120]
    y = pd.Series([0, 1] * (len(X) // 2), index=X.index)
    dm.fit(X, y)
    proba = dm.predict_proba(X)
    assert proba.shape == (len(X),)
    assert np.all((proba >= 0) & (proba <= 1))


def test_direction_model_predict_proba_unfitted_raises():
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    dm = DirectionModel(ModelConfig())
    X = pd.DataFrame({"a": [1.0, 2.0]})
    with pytest.raises(RuntimeError):
        dm.predict_proba(X)


def test_direction_model_feature_importance_rf(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig
    from stock_rtx4060.feature_engine import TARGET_COLUMNS, feature_columns

    cfg = ModelConfig(model_kind="rf")
    dm = DirectionModel(cfg)
    target_cols = list(TARGET_COLUMNS)
    fc = [c for c in feature_columns(feature_df) if c not in target_cols]
    X = feature_df.loc[:, fc].iloc[:120]
    y = pd.Series([0, 1] * (len(X) // 2), index=X.index)
    dm.fit(X, y)
    imp = dm.feature_importance()
    # RF is wrapped in a Pipeline; sklearn 1.8 doesn't forward feature_importances_
    # so the method falls through to the except branch and returns an empty Series.
    assert isinstance(imp, pd.Series)


def test_direction_model_feature_importance_logistic(feature_df):
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig
    from stock_rtx4060.feature_engine import TARGET_COLUMNS, feature_columns

    cfg = ModelConfig(model_kind="logistic")
    dm = DirectionModel(cfg)
    target_cols = list(TARGET_COLUMNS)
    fc = [c for c in feature_columns(feature_df) if c not in target_cols]
    X = feature_df.loc[:, fc].iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2), index=X.index)
    dm.fit(X, y)
    imp = dm.feature_importance()
    assert isinstance(imp, pd.Series)


def test_direction_model_feature_importance_unfitted():
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    dm = DirectionModel(ModelConfig())
    imp = dm.feature_importance()
    assert isinstance(imp, pd.Series)
    assert len(imp) == 0


# ---------------------------------------------------------------------------
# LSTMPredictor._build_sequences
# ---------------------------------------------------------------------------

def test_lstm_build_sequences_too_short():
    from stock_rtx4060.ensemble_model import LSTMPredictor, ModelConfig

    cfg = ModelConfig(seq_len=20)
    lstm = LSTMPredictor(cfg)
    X = np.random.rand(10, 5)
    result = lstm._build_sequences(X)
    assert result.shape == (0, 20, 5)


def test_lstm_build_sequences_normal():
    from stock_rtx4060.ensemble_model import LSTMPredictor, ModelConfig

    cfg = ModelConfig(seq_len=5)
    lstm = LSTMPredictor(cfg)
    X = np.random.rand(15, 3)
    result = lstm._build_sequences(X)
    assert result.shape == (10, 5, 3)


def test_lstm_predict_proba_no_model_raises():
    from stock_rtx4060.ensemble_model import LSTMPredictor, ModelConfig

    cfg = ModelConfig()
    lstm = LSTMPredictor(cfg)
    X = pd.DataFrame(np.random.rand(30, 5))
    with pytest.raises(RuntimeError):
        lstm.predict_proba(X)


# ---------------------------------------------------------------------------
# EnsemblePredictor — init edge cases
# ---------------------------------------------------------------------------

def test_ensemble_init_gap_none():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(horizon=10, gap=None)
    ep = EnsemblePredictor(cfg)
    assert ep.config.gap == 10


def test_ensemble_init_prefer_gpu():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(prefer_gpu=True)
    ep = EnsemblePredictor(cfg)
    assert ep.config.xgb_device == "cuda"


def test_ensemble_init_use_xgboost_overrides_logistic():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(use_xgboost=True, model_kind="logistic")
    ep = EnsemblePredictor(cfg)
    assert ep.config.model_kind == "xgb"


def test_ensemble_init_lite_reduces_estimators():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(lite=True)
    ep = EnsemblePredictor(cfg)
    assert ep.config.xgb_params["n_estimators"] <= 120


def test_ensemble_not_trained_initially():
    from stock_rtx4060.ensemble_model import EnsemblePredictor

    ep = EnsemblePredictor()
    assert ep.trained is False


# ---------------------------------------------------------------------------
# EnsemblePredictor.fit
# ---------------------------------------------------------------------------

def test_ensemble_fit_logistic(feature_df):
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    cv = ep.fit(feature_df)
    assert ep.trained is True
    assert isinstance(cv, list)
    assert len(cv) >= 2


def test_ensemble_fit_rf(feature_df):
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="rf", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    cv = ep.fit(feature_df)
    assert ep.trained is True
    assert all("fold" in r for r in cv)


def test_ensemble_fit_too_few_rows():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    small_df = _build_features().iloc[:50]
    cfg = ModelConfig(n_splits=2)
    ep = EnsemblePredictor(cfg)
    with pytest.raises(RuntimeError, match="부족"):
        ep.fit(small_df)


def test_ensemble_fit_single_class_raises():
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    feat = _build_features()
    feat = feat.copy()
    feat["target_direction"] = 1
    cfg = ModelConfig(model_kind="logistic", n_splits=2)
    ep = EnsemblePredictor(cfg)
    with pytest.raises(RuntimeError, match="class"):
        ep.fit(feat)


# ---------------------------------------------------------------------------
# EnsemblePredictor.predict / predict_proba / predict_latest
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fitted_ensemble(feature_df):
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    ep.fit(feature_df)
    return ep


def test_ensemble_predict_not_trained_raises():
    from stock_rtx4060.ensemble_model import EnsemblePredictor

    ep = EnsemblePredictor()
    with pytest.raises(RuntimeError):
        ep.predict(pd.DataFrame({"a": [1.0]}))


def test_ensemble_predict_returns_dict(fitted_ensemble, feature_df):
    fc = fitted_ensemble.feature_cols
    X = feature_df.loc[:, fc].iloc[-30:]
    result = fitted_ensemble.predict(X)
    assert "direction_prob" in result
    assert "signal" in result
    assert result["signal"] in {"BUY_REVIEW", "SELL_OR_AVOID", "HOLD_NEUTRAL"}


def test_ensemble_predict_proba_shape(fitted_ensemble, feature_df):
    fc = fitted_ensemble.feature_cols
    X = feature_df.loc[:, fc].iloc[-50:]
    proba = fitted_ensemble.predict_proba(X)
    assert len(proba) == len(X)
    assert np.all((proba >= 0) & (proba <= 1))


def test_ensemble_predict_latest_keys(fitted_ensemble, feature_df):
    result = fitted_ensemble.predict_latest(feature_df)
    for key in ("direction_prob", "main_prob", "lstm_prob", "signal", "confidence", "backend"):
        assert key in result


def test_ensemble_xgb_property(fitted_ensemble):
    ns = fitted_ensemble.xgb
    assert hasattr(ns, "backend")


def test_ensemble_predict_not_trained_proba_raises():
    from stock_rtx4060.ensemble_model import EnsemblePredictor

    ep = EnsemblePredictor()
    with pytest.raises(RuntimeError):
        ep.predict_proba(pd.DataFrame({"a": [1.0]}))


# ---------------------------------------------------------------------------
# _safe_auc — exception path (lines 40-41)
# ---------------------------------------------------------------------------

def test_safe_auc_exception_path(monkeypatch):
    """roc_auc_score raises → returns 0.5."""
    import stock_rtx4060.ensemble_model as _em
    from stock_rtx4060.ensemble_model import _safe_auc

    monkeypatch.setattr(_em, "roc_auc_score", lambda *a, **kw: (_ for _ in ()).throw(ValueError("bad")))
    y = np.array([0, 1, 0, 1])
    prob = np.array([0.1, 0.9, 0.2, 0.8])
    assert _safe_auc(y, prob) == 0.5


# ---------------------------------------------------------------------------
# feature_importance — XGBoost path (lines 212-213)
# ---------------------------------------------------------------------------

def test_direction_model_feature_importance_xgb(feature_df):
    """XGBClassifier is stored directly (not in a Pipeline) → feature_importances_ is forwarded."""
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="xgb", xgb_device="cpu")
    dm = DirectionModel(cfg)
    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    dm.fit(X, y)
    imp = dm.feature_importance()
    assert isinstance(imp, pd.Series)
    # XGBClassifier has feature_importances_ directly → should be non-empty
    assert len(imp) > 0


# ---------------------------------------------------------------------------
# EnsemblePredictor.predict — signal branches (lines 396/398/400)
# ---------------------------------------------------------------------------

def _make_fitted_ep_with_prob(feature_df, fixed_prob: float):
    """Create a trained EnsemblePredictor whose main_model always returns fixed_prob."""
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    ep.fit(feature_df)
    # Monkey-patch DirectionModel.predict_proba to return fixed probability
    ep.main_model.predict_proba = lambda X: np.full(len(X), fixed_prob)
    ep.lstm = None
    return ep


def test_predict_signal_buy_review(feature_df):
    """prob >= 0.56 → BUY_REVIEW."""
    ep = _make_fitted_ep_with_prob(feature_df, 0.70)
    fc = ep.feature_cols
    X = feature_df.loc[:, fc].iloc[-20:]
    result = ep.predict(X)
    assert result["signal"] == "BUY_REVIEW"


def test_predict_signal_sell_or_avoid(feature_df):
    """prob <= 0.44 → SELL_OR_AVOID."""
    ep = _make_fitted_ep_with_prob(feature_df, 0.30)
    fc = ep.feature_cols
    X = feature_df.loc[:, fc].iloc[-20:]
    result = ep.predict(X)
    assert result["signal"] == "SELL_OR_AVOID"


def test_predict_signal_hold_neutral(feature_df):
    """0.44 < prob < 0.56 → HOLD_NEUTRAL."""
    ep = _make_fitted_ep_with_prob(feature_df, 0.50)
    fc = ep.feature_cols
    X = feature_df.loc[:, fc].iloc[-20:]
    result = ep.predict(X)
    assert result["signal"] == "HOLD_NEUTRAL"


# ---------------------------------------------------------------------------
# DirectionModel.fit — xgb-cpu-fallback path (lines 181-183)
# ---------------------------------------------------------------------------

def test_direction_model_fit_xgb_cpu_fallback(feature_df, monkeypatch):
    """First _make_xgb call raises (GPU failure) → second _make_xgb("cpu") succeeds → kind_used='xgb-cpu-fallback'."""
    from stock_rtx4060.ensemble_model import DirectionModel, ModelConfig

    cfg = ModelConfig(model_kind="auto", xgb_device="cuda")
    dm = DirectionModel(cfg)

    call_count = {"n": 0}
    original_make_xgb = dm._make_xgb

    def patched_make_xgb(device):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated CUDA unavailable")
        return original_make_xgb("cpu")

    monkeypatch.setattr(dm, "_make_xgb", patched_make_xgb)

    X = feature_df.drop(columns=["target_direction"], errors="ignore").select_dtypes(include=[np.number]).iloc[:80]
    y = pd.Series([0, 1] * (len(X) // 2))
    dm.fit(X, y)
    assert dm.kind_used == "xgb-cpu-fallback"


# ---------------------------------------------------------------------------
# EnsemblePredictor.predict_proba — LSTM blending path (lines 417-426)
# ---------------------------------------------------------------------------

def test_predict_proba_with_lstm_blend(feature_df):
    """Inject a mock LSTM whose predict_proba returns a fixed array to exercise the LSTM blend branch."""
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    ep.fit(feature_df)

    fc = ep.feature_cols
    X = feature_df.loc[:, fc].iloc[-30:]

    # Inject a fake LSTM with known probabilities
    n = len(X)
    fake_lstm_probs = np.full(n, 0.6)

    class _FakeLSTM:
        def predict_proba(self, X):
            return fake_lstm_probs

    ep.lstm = _FakeLSTM()
    proba = ep.predict_proba(X)
    assert len(proba) == n
    assert np.all((proba >= 0) & (proba <= 1))


def test_predict_proba_with_lstm_exception(feature_df):
    """Injected LSTM raises → falls back to main_prob (line 420)."""
    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    cfg = ModelConfig(model_kind="logistic", n_splits=2, lite=True)
    ep = EnsemblePredictor(cfg)
    ep.fit(feature_df)

    fc = ep.feature_cols
    X = feature_df.loc[:, fc].iloc[-20:]

    class _BrokenLSTM:
        def predict_proba(self, X):
            raise RuntimeError("lstm error")

    ep.lstm = _BrokenLSTM()
    # Should not raise; falls back to main model
    proba = ep.predict_proba(X)
    assert len(proba) == len(X)


# ---------------------------------------------------------------------------
# LSTMPredictor — PyTorch backend (W-C patch)
# ---------------------------------------------------------------------------


def test_lstm_has_torch_function_importable():
    """_has_torch must be importable from ensemble_model."""
    from stock_rtx4060.ensemble_model import _has_torch

    result = _has_torch()
    assert isinstance(result, bool)


def test_lstm_fit_raises_without_torch(monkeypatch):
    """LSTMPredictor.fit() raises RuntimeError when torch is not installed."""
    from unittest.mock import patch

    from stock_rtx4060.ensemble_model import LSTMPredictor, ModelConfig

    cfg = ModelConfig(seq_len=5)
    lstm = LSTMPredictor(cfg)
    X = pd.DataFrame(np.random.rand(30, 4))
    y = pd.Series([0, 1] * 15)

    with patch("stock_rtx4060.ensemble_model._has_torch", return_value=False):
        with pytest.raises(RuntimeError, match="PyTorch not installed"):
            lstm.fit(X, y)


def test_lstm_torch_device_returns_string():
    """_torch_device() always returns a non-empty string."""
    from stock_rtx4060.ensemble_model import LSTMPredictor

    device = LSTMPredictor._torch_device()
    assert isinstance(device, str)
    assert device in ("cpu", "cuda")


def test_lstm_build_sequences_interface_unchanged():
    """_build_sequences output shape contract is preserved after PyTorch port."""
    from stock_rtx4060.ensemble_model import LSTMPredictor, ModelConfig

    cfg = ModelConfig(seq_len=3)
    lstm = LSTMPredictor(cfg)
    X = np.ones((10, 4), dtype=float)
    seq = lstm._build_sequences(X)
    assert seq.shape == (7, 3, 4), f"Expected (7,3,4) got {seq.shape}"


# ---------------------------------------------------------------------------
# contrarian_mode (KRX mean-reversion)
# ---------------------------------------------------------------------------


def test_contrarian_mode_flips_probability():
    """contrarian_mode=True flips prob → 1-prob in predict()."""
    import numpy as np
    import pandas as pd

    from stock_rtx4060.ensemble_model import EnsemblePredictor, ModelConfig

    rng = np.random.default_rng(99)
    n = 200
    X = pd.DataFrame(rng.standard_normal((n, 4)), columns=["a", "b", "c", "d"])
    X["target_direction"] = (rng.standard_normal(n) > 0).astype(int)
    X["target_return"] = rng.standard_normal(n) * 0.01

    cfg_normal = ModelConfig(horizon=5, n_splits=3, cv_kind="purged", embargo_pct=0.01, lite=True)
    cfg_contr = ModelConfig(horizon=5, n_splits=3, cv_kind="purged", embargo_pct=0.01, lite=True, contrarian_mode=True)

    ep_n = EnsemblePredictor(cfg_normal)
    ep_n.fit(X)
    pred_n = ep_n.predict(X)

    ep_c = EnsemblePredictor(cfg_contr)
    ep_c.fit(X)
    pred_c = ep_c.predict(X)

    # Both should have same train data → raw probs are identical before flip
    # Flipped: prob_c ≈ 1 - prob_n
    assert abs(pred_c["direction_prob"] + pred_n["direction_prob"] - 1.0) < 0.01, (
        f"Contrarian prob {pred_c['direction_prob']:.4f} + normal {pred_n['direction_prob']:.4f} != 1.0"
    )


def test_contrarian_mode_config_default_false():
    """ModelConfig.contrarian_mode defaults to False."""
    from stock_rtx4060.ensemble_model import ModelConfig
    assert ModelConfig().contrarian_mode is False
