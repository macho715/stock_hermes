"""
Walk-forward ensemble model for stock_rtx4060.

Improvements over the previous patch:
- TimeSeriesSplit ``gap`` or PurgedKFold embargo to reduce horizon leakage;
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .feature_engine import TARGET_COLUMNS, feature_columns

ModelKind = Literal["auto", "xgb", "logistic", "rf", "lightgbm"]
DeviceKind = Literal["cpu", "cuda"]
CVKind = Literal["timeseries", "purged"]


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
    cv_kind: CVKind = "timeseries"
    embargo_pct: float = 0.01
    max_features: int | None = None   # fold-local feature cap; None = use all
    contrarian_mode: bool = False      # flip 1-prob for mean-reversion markets (e.g. KRX)
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

    def _make_rf(self) -> Pipeline:
        return Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=200,
                        max_depth=6,
                        min_samples_leaf=5,
                        max_features="sqrt",
                        class_weight="balanced",
                        random_state=self.config.random_state,
                        n_jobs=4,
                    ),
                ),
            ]
        )

    def _make_xgb(self, device: DeviceKind):
        from xgboost import XGBClassifier  # type: ignore

        params = xgb_params_for_device(self.config.xgb_params, device=device)
        return XGBClassifier(**params)

    def _make_lightgbm(self):
        from .ml.lightgbm_model import make_lightgbm

        device = "cuda" if self.config.xgb_device == "cuda" else "cpu"
        return make_lightgbm(device=device, random_state=self.config.random_state)

    def fit(self, X: pd.DataFrame, y: pd.Series) -> DirectionModel:
        if y.nunique() < 2:
            raise RuntimeError("target class가 하나뿐이라 분류 모델을 학습할 수 없습니다")
        self.feature_cols = list(X.columns)
        clean_X = X.replace([np.inf, -np.inf], np.nan)
        kind = self.config.model_kind

        if kind == "rf":
            self.model = self._make_rf()
            self.model.fit(clean_X, y.astype(int))
            self.kind_used = "rf"
            return self

        if kind == "lightgbm":
            self.model = self._make_lightgbm()
            self.model.fit(clean_X, y.astype(int))
            self.kind_used = "lightgbm"
            return self

        if kind in {"auto", "xgb"}:
            try:
                self.model = self._make_xgb(self.config.xgb_device)
                self.model.fit(clean_X, y.astype(int))
                self.kind_used = f"xgb-{self.config.xgb_device}"
                return self
            except Exception:
                if kind == "xgb" and self.config.xgb_device == "cpu":
                    raise
                # GPU or xgb failure → try CPU XGBoost first.
                try:
                    self.model = self._make_xgb("cpu")
                    self.model.fit(clean_X, y.astype(int))
                    self.kind_used = "xgb-cpu-fallback"
                    return self
                except Exception:
                    if kind == "xgb":
                        raise
                    # XGBoost completely unavailable → fall back to RandomForest.
                    try:
                        self.model = self._make_rf()
                        self.model.fit(clean_X, y.astype(int))
                        self.kind_used = "rf-fallback"
                        return self
                    except Exception:
                        pass

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


def _fold_local_select(
    X_tr: pd.DataFrame,
    y_tr: pd.Series,
    k: int,
) -> tuple[pd.DataFrame, list[str]]:
    """Select top-k features by mutual information — fold-local only.

    Fitting is strictly on ``(X_tr, y_tr)``.  Never call with test data.
    Falls back to returning all columns when selection fails.
    """
    try:
        from sklearn.feature_selection import SelectKBest, mutual_info_classif

        selector = SelectKBest(score_func=mutual_info_classif, k=min(k, X_tr.shape[1]))
        clean = X_tr.fillna(0.0).replace([float("inf"), float("-inf")], 0.0)
        selector.fit(clean, y_tr.astype(int))
        mask = selector.get_support()
        selected = [col for col, m in zip(X_tr.columns, mask, strict=False) if m]
        return X_tr[selected], selected
    except Exception:
        return X_tr, list(X_tr.columns)


def _has_torch() -> bool:
    """Check whether PyTorch (torch) is importable."""
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


class _TorchLSTMNet:  # pragma: no cover
    """Internal PyTorch LSTM network — only instantiated when torch is available."""

    def __init__(self, n_features: int, seq_len: int, device: str) -> None:
        import torch
        import torch.nn as nn

        self.device = torch.device(device)
        self.seq_len = seq_len

        class _Net(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.lstm1 = nn.LSTM(n_features, 64, batch_first=True)
                self.bn    = nn.BatchNorm1d(64)
                self.drop1 = nn.Dropout(0.25)
                self.lstm2 = nn.LSTM(64, 32, batch_first=True)
                self.drop2 = nn.Dropout(0.20)
                self.fc1   = nn.Linear(32, 16)
                self.relu  = nn.ReLU()
                self.fc2   = nn.Linear(16, 1)

            def forward(self, x):  # x: (batch, seq, features)
                out, _ = self.lstm1(x)
                out = self.bn(out[:, -1, :])
                out = self.drop1(out).unsqueeze(1)
                out, _ = self.lstm2(out)
                out = self.drop2(out[:, -1, :])
                return torch.sigmoid(self.fc2(self.relu(self.fc1(out)))).squeeze(1)

        self.net = _Net().to(self.device)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=0.001)
        self.criterion = torch.nn.BCELoss()

    def fit(self, X_seq: np.ndarray, y_seq: np.ndarray, epochs: int = 40) -> None:
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        Xt = torch.tensor(X_seq, dtype=torch.float32).to(self.device)
        yt = torch.tensor(y_seq, dtype=torch.float32).to(self.device)
        ds = TensorDataset(Xt, yt)
        loader = DataLoader(ds, batch_size=32, shuffle=False)
        best_loss, patience, no_improve = float("inf"), 6, 0
        best_state = None
        self.net.train()
        for _ in range(epochs):
            epoch_loss = 0.0
            for xb, yb in loader:
                self.optimizer.zero_grad()
                loss = self.criterion(self.net(xb), yb)
                loss.backward()
                self.optimizer.step()
                epoch_loss += loss.item()
            if epoch_loss < best_loss:
                best_loss = epoch_loss
                best_state = {k: v.clone() for k, v in self.net.state_dict().items()}
                no_improve = 0
            else:
                no_improve += 1
                if no_improve >= patience:
                    break
        if best_state is not None:
            self.net.load_state_dict(best_state)

    def predict(self, X_seq: np.ndarray) -> np.ndarray:
        import torch
        self.net.eval()
        with torch.no_grad():
            Xt = torch.tensor(X_seq, dtype=torch.float32).to(self.device)
            return self.net(Xt).cpu().numpy()


class LSTMPredictor:  # pragma: no cover
    """LSTM time-series predictor.

    Backend selection (automatic):
    - PyTorch + CUDA  when ``torch`` is installed and CUDA is available
    - PyTorch CPU     when ``torch`` is installed but CUDA is not available
    - Raises RuntimeError on ``fit()`` when ``torch`` is not installed
      (``use_lstm=True`` should only be set when torch is present)
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._net: _TorchLSTMNet | None = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")

    @staticmethod
    def _torch_device() -> str:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def _build_sequences(self, X: np.ndarray) -> np.ndarray:
        if len(X) <= self.config.seq_len:
            return np.empty((0, self.config.seq_len, X.shape[1]), dtype=float)
        return np.stack([X[i - self.config.seq_len : i] for i in range(self.config.seq_len, len(X))])

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LSTMPredictor:
        if not _has_torch():
            raise RuntimeError(
                "PyTorch not installed — install with: "
                "pip install torch --index-url https://download.pytorch.org/whl/cu128"
            )
        clean = self.imputer.fit_transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.fit_transform(clean)
        X_seq = self._build_sequences(scaled)
        y_seq = y.astype(int).to_numpy()[self.config.seq_len :]
        if len(X_seq) == 0 or len(np.unique(y_seq)) < 2:
            raise RuntimeError("LSTM 학습 데이터 부족")
        device = self._torch_device()
        self._net = _TorchLSTMNet(X.shape[1], self.config.seq_len, device)
        self._net.fit(X_seq.astype(np.float32), y_seq.astype(np.float32))
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("fit() 먼저 호출 필요")
        clean = self.imputer.transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.transform(clean)
        X_seq = self._build_sequences(scaled)
        if len(X_seq) == 0:
            return np.array([], dtype=float)
        return self._net.predict(X_seq.astype(np.float32)).flatten().clip(0.0, 1.0)


class GRUPredictor:  # pragma: no cover
    """Gated Recurrent Unit predictor — lightweight RNN alternative to LSTM.

    Uses ``torch.nn.GRU`` when PyTorch is available (GPU-accelerated on CUDA),
    otherwise raises ``RuntimeError`` with an install hint.  The public interface
    mirrors :class:`LSTMPredictor` so callers can substitute one for the other.
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._net: Any | None = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")

    def _build_sequences(self, X: np.ndarray) -> np.ndarray:
        if len(X) <= self.config.seq_len:
            return np.empty((0, self.config.seq_len, X.shape[1]), dtype=float)
        return np.stack([X[i - self.config.seq_len : i] for i in range(self.config.seq_len, len(X))])

    @staticmethod
    def _torch_device() -> str:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def fit(self, X: pd.DataFrame, y: pd.Series) -> GRUPredictor:
        if not _has_torch():
            raise RuntimeError(
                "PyTorch not installed — install with: "
                "pip install torch --index-url https://download.pytorch.org/whl/cu128"
            )
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        clean = self.imputer.fit_transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.fit_transform(clean)
        X_seq = self._build_sequences(scaled)
        y_seq = y.astype(int).to_numpy()[self.config.seq_len :]
        if len(X_seq) == 0 or len(np.unique(y_seq)) < 2:
            raise RuntimeError("GRU 학습 데이터 부족")

        device = torch.device(self._torch_device())
        n_feat = X.shape[1]

        class _GRUNet(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.gru  = nn.GRU(n_feat, 48, num_layers=2, batch_first=True, dropout=0.2)
                self.drop = nn.Dropout(0.2)
                self.fc   = nn.Linear(48, 1)

            def forward(self, x: Any) -> Any:
                out, _ = self.gru(x)
                return torch.sigmoid(self.fc(self.drop(out[:, -1, :]))).squeeze(1)

        net = _GRUNet().to(device)
        opt = torch.optim.Adam(net.parameters(), lr=0.001)
        crit = nn.BCELoss()
        Xt = torch.tensor(X_seq, dtype=torch.float32).to(device)
        yt = torch.tensor(y_seq, dtype=torch.float32).to(device)
        loader = DataLoader(TensorDataset(Xt, yt), batch_size=32, shuffle=False)
        best_loss, patience, no_improve, best_state = float("inf"), 6, 0, None
        net.train()
        for _ in range(35):
            ep_loss = 0.0
            for xb, yb in loader:
                opt.zero_grad()
                loss = crit(net(xb), yb)
                loss.backward()
                opt.step()
                ep_loss += loss.item()
            if ep_loss < best_loss:
                best_loss, no_improve = ep_loss, 0
                best_state = {k: v.clone() for k, v in net.state_dict().items()}
            else:
                no_improve += 1
                if no_improve >= patience:
                    break
        if best_state:
            net.load_state_dict(best_state)
        self._net = (net, device)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self._net is None:
            raise RuntimeError("fit() 먼저 호출 필요")
        import torch
        net, device = self._net
        clean = self.imputer.transform(X.replace([np.inf, -np.inf], np.nan))
        scaled = self.scaler.transform(clean)
        X_seq = self._build_sequences(scaled)
        if len(X_seq) == 0:
            return np.array([], dtype=float)
        net.eval()
        with torch.no_grad():
            Xt = torch.tensor(X_seq, dtype=torch.float32).to(device)
            return net(Xt).cpu().numpy().flatten().clip(0.0, 1.0)


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
        # [Wave 4 BEST-3] TFT as optional 4th model
        from .ml.tft_model import make_tft_predictor as _make_tft
        self.tft = _make_tft()
        self._trained = False
        self.feature_cols: list[str] = []
        self.oof_probabilities_: pd.Series | None = None
        self.cv_results_: list[dict[str, Any]] = []

    def _splitter(self, n_samples: int) -> Any:
        n_splits = min(self.config.n_splits, max(2, n_samples // 80))
        gap = min(max(0, self.config.gap or 0), max(0, n_samples // (n_splits + 1) - 1))
        if self.config.cv_kind == "purged":
            from .ml.cv import PurgedKFold

            return PurgedKFold(n_splits=n_splits, embargo_pct=self.config.embargo_pct)
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

        # MLflow run (no-op when mlflow unavailable). We open a single run
        # around the whole walk-forward CV so all fold metrics share context.
        try:
            from .observability import MLflowSession, log_metrics, log_params

            _mlflow_ctx = MLflowSession("ensemble_train", run_name="walk_forward")
        except Exception:  # pragma: no cover - observability is optional
            from contextlib import nullcontext

            _mlflow_ctx = nullcontext()
            log_metrics = lambda *_a, **_k: None  # noqa: E731
            log_params = lambda *_a, **_k: None  # noqa: E731

        with _mlflow_ctx:
            try:
                log_params(
                    {
                        "model_kind": self.config.model_kind,
                        "n_splits": self.config.n_splits,
                        "gap": self.config.gap,
                        "cv_kind": self.config.cv_kind,
                        "embargo_pct": self.config.embargo_pct,
                    }
                )
            except Exception:  # pragma: no cover
                pass
            # mlflow 3.x log_input — training dataset reference
            try:
                import mlflow  # type: ignore[import-not-found]
                if hasattr(mlflow, 'log_input'):
                    input_ds = mlflow.data.from_pandas(X, targets=y, name="ensemble_train")
                    mlflow.log_input(input_ds, context="training")
            except Exception:  # pragma: no cover - mlflow 3.x optional
                pass
            cv_results = self._fit_folds(
                X, y, oof, splitter, feature_df, log_metrics=log_metrics
            )
            try:
                aucs = [r["auc"] for r in cv_results]
                if aucs:
                    log_metrics(
                        {
                            "best_fold_auc": float(max(aucs)),
                            "mean_oos_auc": float(np.mean(aucs)),
                        }
                    )
                imp = self.main_model.feature_importance().head(20)
                if not imp.empty:
                    log_metrics({f"fi_{k}": float(v) for k, v in imp.items()})
            except Exception:  # pragma: no cover
                pass
        # Tail of fit (full-data refit etc.) is performed inside _fit_folds.
        return cv_results

    def _fit_folds(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        oof: pd.Series,
        splitter: Any,
        feature_df: pd.DataFrame,
        *,
        log_metrics,
    ) -> list[dict[str, Any]]:
        cv_results: list[dict[str, Any]] = []
        # Pass label end-times as groups so PurgedKFold can purge overlapping
        # training rows.  We approximate the horizon from config (default 5 bars).
        horizon = int(getattr(self.config, "horizon", 5))
        _groups = np.arange(len(X)) + horizon
        split_iter = (
            splitter.split(X, groups=_groups)
            if self.config.cv_kind == "purged"
            else splitter.split(X)
        )
        for fold, (train_idx, test_idx) in enumerate(split_iter, start=1):
            X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
            y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]

            # Fold-local feature selection — safe against look-ahead bias because
            # selection uses only X_tr/y_tr (never X_te/y_te).
            if self.config.max_features and X_tr.shape[1] > self.config.max_features:
                X_tr, selected_cols = _fold_local_select(X_tr, y_tr, self.config.max_features)
                X_te = X_te[selected_cols]

            model = DirectionModel(self.config).fit(X_tr, y_tr)
            prob = model.predict_proba(X_te)

            # Contrarian mode: flip 1-prob for mean-reversion markets.
            # Applied BEFORE blending so downstream OOF metrics are correct.
            if self.config.contrarian_mode:
                prob = 1.0 - prob

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
        # Contrarian mode: flip for mean-reversion markets (e.g. KRX)
        if self.config.contrarian_mode:
            prob = 1.0 - prob
            main_prob = 1.0 - main_prob
            lstm_prob = 1.0 - lstm_prob
        confidence = abs(prob - 0.5) * 2.0
        if prob >= 0.56:
            signal = "BUY_REVIEW"
        elif prob <= 0.44:
            signal = "SELL_OR_AVOID"
        else:
            signal = "HOLD_NEUTRAL"
        # [Wave 4 BEST-3] TFT score — 0.5 when not trained or unavailable
        tft_prob = 0.5
        if self.tft is not None:
            try:
                tft_preds = self.tft.predict(X.loc[:, self.feature_cols])
                if tft_preds:
                    tft_prob = float(tft_preds[-1])
            except Exception:
                pass
        return {
            "direction_prob": float(prob),
            "signal": signal,
            "confidence": float(confidence),
            "main_prob": float(main_prob),
            "lstm_prob": float(lstm_prob),
            "tft_prob": float(tft_prob),
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

    def predict_proba_with_shap(self, X: pd.DataFrame) -> tuple[np.ndarray, dict[str, float]]:
        """Return ``(probabilities, mean_abs_shap_per_feature)``.

        When SHAP is not installed, the second element is an empty dict.
        """
        prob = self.predict_proba(X)
        try:
            from .ml.explain import explain

            X_aligned = X.reindex(columns=self.feature_cols).fillna(0.0)
            shap_df = explain(self.main_model.model, X_aligned)
            mean_abs = shap_df.abs().mean().to_dict()
            return prob, {str(k): float(v) for k, v in mean_abs.items()}
        except ImportError:
            return prob, {}
        except Exception:
            return prob, {}

    def predict_latest(self, feature_df: pd.DataFrame) -> dict[str, Any]:
        X = feature_df.reindex(columns=self.feature_cols).fillna(0.0)
        prediction = self.predict(X)
        return {
            "direction_prob": round(float(prediction["direction_prob"]), 6),
            "main_prob": round(float(prediction["main_prob"]), 6),
            "lstm_prob": round(float(prediction["lstm_prob"]), 6),
            "signal": prediction["signal"],
            "confidence": round(float(prediction["confidence"]), 6),
            "backend": prediction["model_kind"],
            "lstm_enabled": self.lstm is not None,
        }
