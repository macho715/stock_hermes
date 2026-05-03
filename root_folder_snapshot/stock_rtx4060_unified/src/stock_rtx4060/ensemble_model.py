"""
Walk-forward ensemble model for stock_rtx4060.

Improvements over the previous patch:
- purged TimeSeriesSplit via ``gap`` to reduce horizon leakage;
- version-aware XGBoost CPU/GPU parameters with CPU fallback;
- optional LSTM path instead of mandatory TensorFlow dependency;
- safe AUC calculation for single-class folds;
- out-of-fold probabilities for leak-safe backtesting.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .feature_engine import TARGET_COLUMNS, feature_columns

ModelKind = Literal["auto", "xgb", "logistic"]
DeviceKind = Literal["cpu", "cuda"]


def _safe_auc(y_true: pd.Series | np.ndarray, prob: np.ndarray) -> float:
    y_arr = np.asarray(y_true, dtype=int)
    p_arr = np.asarray(prob, dtype=float)
    if len(y_arr) == 0 or len(np.unique(y_arr)) < 2:
        return 0.5
    try:
        return float(roc_auc_score(y_arr, p_arr))
    except Exception:
        return 0.5


def _xgboost_version_tuple() -> tuple[int, int, int]:
    try:
        import xgboost as xgb  # type: ignore

        parts = str(xgb.__version__).split(".")[:3]
        return tuple(int(p.split("+")[0]) for p in (parts + ["0", "0", "0"])[:3])  # type: ignore[return-value]
    except Exception:
        return (0, 0, 0)


def xgb_params_for_device(base: dict[str, Any], device: DeviceKind = "cpu") -> dict[str, Any]:
    """Return XGBoost params compatible with both pre-2.0 and 2.x+ APIs."""
    params = dict(base)
    version = _xgboost_version_tuple()
    if device == "cuda":
        if version >= (2, 0, 0):
            params["tree_method"] = "hist"
            params["device"] = "cuda"
        else:
            params["tree_method"] = "gpu_hist"
            params.pop("device", None)
    else:
        params["tree_method"] = "hist"
        params.pop("device", None)
    return params


@dataclass
class ModelConfig:
    horizon: int = 5
    seq_len: int = 20
    n_splits: int = 5
    gap: int | None = None
    model_kind: ModelKind = "auto"
    xgb_device: DeviceKind = "cpu"
    prefer_gpu: bool = False
    use_xgboost: bool = False
    lite: bool = False
    use_lstm: bool = False
    xgb_weight: float = 0.70
    lstm_weight: float = 0.30
    random_state: int = 42
    xgb_params: dict[str, Any] = field(
        default_factory=lambda: {
            "n_estimators": 240,
            "max_depth": 4,
            "learning_rate": 0.04,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "min_child_weight": 3,
            "reg_lambda": 1.5,
            "reg_alpha": 0.05,
            "eval_metric": "logloss",
            "random_state": 42,
            "n_jobs": 4,
            "verbosity": 0,
            "use_label_encoder": False,
        }
    )


class DirectionModel:
    """Small wrapper around XGBoost or logistic regression."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.feature_cols: list[str] = []
        self.kind_used: str = "unfitted"
        self.model: Any = None

    def _make_logistic(self) -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=800,
                        solver="lbfgs",
                        class_weight="balanced",
                        random_state=self.config.random_state,
                    ),
                ),
            ]
        )

    def _make_xgb(self, device: DeviceKind):
        from xgboost import XGBClassifier  # type: ignore

        params = xgb_params_for_device(self.config.xgb_params, device=device)
        return XGBClassifier(**params)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "DirectionModel":
        if y.nunique() < 2:
            raise RuntimeError("target class가 하나뿐이라 분류 모델을 학습할 수 없습니다")
        self.feature_cols = list(X.columns)
        clean_X = X.replace([np.inf, -np.inf], np.nan)
        kind = self.config.model_kind

        if kind in {"auto", "xgb"}:
            try:
                self.model = self._make_xgb(self.config.xgb_device)
                self.model.fit(clean_X, y.astype(int))
                self.kind_used = f"xgb-{self.config.xgb_device}"
                return self
            except Exception:
                if kind == "xgb" and self.config.xgb_device == "cpu":
                    raise
                # GPU or xgb failure fallback.
                try:
                    self.model = self._make_xgb("cpu")
                    self.model.fit(clean_X, y.astype(int))
                    self.kind_used = "xgb-cpu-fallback"
                    return self
                except Exception:
                    if kind == "xgb":
                        raise

        self.model = self._make_logistic()
        self.model.fit(clean_X, y.astype(int))
        self.kind_used = "logistic"
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("fit() 먼저 호출 필요")
        clean_X = X.loc[:, self.feature_cols].replace([np.inf, -np.inf], np.nan)
        prob = self.model.predict_proba(clean_X)[:, 1]
        return np.asarray(prob, dtype=float).clip(0.0, 1.0)

    def feature_importance(self) -> pd.Series:
        if self.model is None:
            return pd.Series(dtype=float)
        if hasattr(self.model, "feature_importances_"):
            values = np.asarray(self.model.feature_importances_, dtype=float)
            return pd.Series(values, index=self.feature_cols).sort_values(ascending=False)
        try:
            coef = self.model.named_steps["model"].coef_[0]
            return pd.Series(np.abs(coef), index=self.feature_cols).sort_values(ascending=False)
        except Exception:
            return pd.Series(dtype=float)


class LSTMPredictor:
    """Optional TensorFlow LSTM.  If TensorFlow is unavailable, caller falls back."""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")

    def _build_sequences(self, X: np.ndarray) -> np.ndarray:
        if len(X) <= self.config.seq_len:
            return np.empty((0, self.config.seq_len, X.shape[1]), dtype=float)
        return np.stack([X[i - self.config.seq_len : i] for i in range(self.config.seq_len, len(X))])

    def _build_model(self, n_features: int):
        import tensorflow as tf  # type: ignore
        from tensorflow.keras.layers import LSTM, BatchNormalization, Dense, Dropout, Input
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.optimizers import Adam

        model = Sequential(
            [
                Input(shape=(self.config.seq_len, n_features)),
                LSTM(64, return_sequences=True),
                BatchNormalization(),
                Dropout(0.25),
                LSTM(32),
                Dropout(0.20),
                Dense(16, activation="relu"),
                Dense(1, activation="sigmoid", dtype="float32"),
            ]
        )
        model.compile(optimizer=Adam(learning_rate=0.001), loss="binary_crossentropy", metrics=["accuracy"])
        return model

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LSTMPredictor":
        from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau  # type: ignore

        clean = self.imputer.fit_transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.fit_transform(clean)
        X_seq = self._build_sequences(scaled)
        y_seq = y.astype(int).to_numpy()[self.config.seq_len :]
        if len(X_seq) == 0 or len(np.unique(y_seq)) < 2:
            raise RuntimeError("LSTM 학습 데이터 부족")
        self.model = self._build_model(X.shape[1])
        self.model.fit(
            X_seq,
            y_seq,
            epochs=40,
            batch_size=32,
            validation_split=0.1,
            callbacks=[EarlyStopping(patience=6, restore_best_weights=True), ReduceLROnPlateau(patience=3, factor=0.5)],
            verbose=0,
        )
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("fit() 먼저 호출 필요")
        clean = self.imputer.transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.transform(clean)
        X_seq = self._build_sequences(scaled)
        if len(X_seq) == 0:
            return np.array([], dtype=float)
        return self.model.predict(X_seq, verbose=0).flatten().clip(0.0, 1.0)


class EnsemblePredictor:
    """XGBoost/logistic plus optional LSTM with leak-safe walk-forward CV."""

    def __init__(self, config: ModelConfig | None = None):
        self.config = config or ModelConfig()
        if self.config.gap is None:
            self.config.gap = max(1, self.config.horizon)
        if self.config.prefer_gpu:
            self.config.xgb_device = "cuda"
        if self.config.use_xgboost and self.config.model_kind == "logistic":
            self.config.model_kind = "xgb"
        if self.config.lite:
            self.config.xgb_params["n_estimators"] = min(int(self.config.xgb_params.get("n_estimators", 160)), 120)
        self.main_model = DirectionModel(self.config)
        self.lstm: LSTMPredictor | None = None
        self._trained = False
        self.feature_cols: list[str] = []
        self.oof_probabilities_: pd.Series | None = None
        self.cv_results_: list[dict[str, Any]] = []

    def _splitter(self, n_samples: int) -> TimeSeriesSplit:
        n_splits = min(self.config.n_splits, max(2, n_samples // 80))
        gap = min(max(0, self.config.gap or 0), max(0, n_samples // (n_splits + 1) - 1))
        return TimeSeriesSplit(n_splits=n_splits, gap=gap)

    def fit(self, feature_df: pd.DataFrame) -> list[dict[str, Any]]:
        target_cols = list(TARGET_COLUMNS)
        self.feature_cols = [c for c in feature_columns(feature_df) if c not in target_cols]
        X = feature_df.loc[:, self.feature_cols].copy()
        y = feature_df["target_direction"].astype(int)
        if len(X) < 80:
            raise RuntimeError(f"학습 데이터 부족: rows={len(X)}")
        if y.nunique() < 2:
            raise RuntimeError("target class가 하나뿐입니다")

        oof = pd.Series(np.nan, index=feature_df.index, dtype=float)
        cv_results: list[dict[str, Any]] = []
        splitter = self._splitter(len(X))

        for fold, (train_idx, test_idx) in enumerate(splitter.split(X), start=1):
            X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
            model = DirectionModel(self.config).fit(X_tr, y_tr)
            prob = model.predict_proba(X_te)

            # Optional fold-local LSTM.  It must never see the test labels.
            if self.config.use_lstm and len(X_tr) > self.config.seq_len * 3:
                try:
                    lstm = LSTMPredictor(self.config).fit(X_tr, y_tr)
                    lstm_input = pd.concat([X_tr.iloc[-self.config.seq_len :], X_te], axis=0)
                    lstm_prob = lstm.predict_proba(lstm_input)[-len(X_te) :]
                    if len(lstm_prob) == len(prob):
                        prob = self.config.xgb_weight * prob + self.config.lstm_weight * lstm_prob
                except Exception:
                    pass

            pred = (prob >= 0.5).astype(int)
            oof.iloc[test_idx] = prob
            cv_results.append(
                {
                    "fold": fold,
                    "accuracy": float(accuracy_score(y_te, pred)),
                    "auc": _safe_auc(y_te, prob),
                    "n_train": int(len(X_tr)),
                    "n_test": int(len(X_te)),
                    "gap": int(self.config.gap or 0),
                    "model": model.kind_used,
                }
            )

        self.main_model.fit(X, y)
        if self.config.use_lstm:
            try:
                self.lstm = LSTMPredictor(self.config).fit(X, y)
            except Exception:
                self.lstm = None

        self.oof_probabilities_ = oof
        self.cv_results_ = cv_results
        self._trained = True
        return cv_results

    @property
    def trained(self) -> bool:
        return self._trained

    @property
    def xgb(self) -> Any:
        return SimpleNamespace(backend=self.main_model.kind_used)

    def predict(self, X: pd.DataFrame) -> dict[str, float | str]:
        if not self._trained:
            raise RuntimeError("fit() 먼저 호출 필요")
        main_prob = float(self.main_model.predict_proba(X.loc[:, self.feature_cols])[-1])
        lstm_prob = main_prob
        if self.lstm is not None and len(X) > self.config.seq_len:
            try:
                arr = self.lstm.predict_proba(X.loc[:, self.feature_cols])
                if len(arr):
                    lstm_prob = float(arr[-1])
            except Exception:
                lstm_prob = main_prob
        if self.lstm is None:
            prob = main_prob
        else:
            prob = self.config.xgb_weight * main_prob + self.config.lstm_weight * lstm_prob
        confidence = abs(prob - 0.5) * 2.0
        if prob >= 0.56:
            signal = "BUY_REVIEW"
        elif prob <= 0.44:
            signal = "SELL_OR_AVOID"
        else:
            signal = "HOLD_NEUTRAL"
        return {
            "direction_prob": float(prob),
            "signal": signal,
            "confidence": float(confidence),
            "main_prob": float(main_prob),
            "lstm_prob": float(lstm_prob),
            "model_kind": self.main_model.kind_used,
        }

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if not self._trained:
            raise RuntimeError("fit() 먼저 호출 필요")
        X_aligned = X.reindex(columns=self.feature_cols).fillna(0.0)
        main_prob = self.main_model.predict_proba(X_aligned)
        if self.lstm is None:
            return main_prob
        try:
            lstm_prob = self.lstm.predict_proba(X_aligned)
        except Exception:
            return main_prob
        if len(lstm_prob) == 0:
            return main_prob
        result = main_prob.copy()
        offset = len(result) - len(lstm_prob)
        result[offset:] = self.config.xgb_weight * main_prob[offset:] + self.config.lstm_weight * lstm_prob
        return result

    def predict_latest(self, feature_df: pd.DataFrame) -> dict[str, Any]:
        X = feature_df.reindex(columns=self.feature_cols).fillna(0.0)
        prediction = self.predict(X)
        return {
            "direction_prob": round(float(prediction["direction_prob"]), 6),
            "signal": prediction["signal"],
            "confidence": round(float(prediction["confidence"]), 6),
            "backend": prediction["model_kind"],
            "lstm_enabled": self.lstm is not None,
        }
