"""
ensemble_model.py — RTX 4060 Laptop 8GB VRAM 최적화
- XGBoost: device="cuda" → GPU 트리 (3072 CUDA cores)
- LSTM: FP16 Mixed Precision → Tensor Core 가속, VRAM 40%↓
- Walk-Forward CV: TimeSeriesSplit (룩어헤드 바이어스 차단)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
import warnings
warnings.filterwarnings("ignore")

from sklearn.preprocessing import RobustScaler    # 이상치 강건
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score

from hw_profile import (
    HW_PROFILE, XGB_GPU_PARAMS, XGB_CPU_PARAMS,
    LSTM_CONFIG, LSTM_CONFIG_LITE, configure_gpu
)


# ─────────────────────────────────────────────────
# § XGBoost GPU 예측기
# ─────────────────────────────────────────────────

class XGBPredictor:
    """
    XGBoost RTX 4060 GPU 가속 분류기
    tree_method="hist" + device="cuda" → GPU 히스토그램 트리
    """

    def __init__(self, use_gpu: bool = True):
        from xgboost import XGBClassifier
        params = XGB_GPU_PARAMS if use_gpu else XGB_CPU_PARAMS
        self.model = XGBClassifier(**params)
        self.scaler = RobustScaler()
        self.feature_cols: list[str] = []
        self._gpu = use_gpu

    def fit(self, X: pd.DataFrame, y: pd.Series,
            eval_set: Optional[tuple] = None) -> "XGBPredictor":
        self.feature_cols = list(X.columns)
        X_s = self.scaler.fit_transform(X)
        fit_kwargs = {}
        if eval_set:
            X_val, y_val = eval_set
            X_val_s = self.scaler.transform(X_val)
            fit_kwargs["eval_set"] = [(X_val_s, y_val)]
            fit_kwargs["verbose"] = False
        self.model.fit(X_s, y, **fit_kwargs)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        X_s = self.scaler.transform(X[self.feature_cols])
        return self.model.predict_proba(X_s)[:, 1]

    def feature_importance(self, top_n: int = 15) -> pd.Series:
        return pd.Series(
            self.model.feature_importances_,
            index=self.feature_cols
        ).nlargest(top_n)


# ─────────────────────────────────────────────────
# § LSTM FP16 예측기 (RTX 4060 Tensor Core)
# ─────────────────────────────────────────────────

class LSTMPredictor:
    """
    FP16 Mixed Precision LSTM
    
    RTX 4060 최적화:
    - FP16 연산: Tensor Core 4세대 가속 (~1.7x 속도)
    - batch_size=64: 3072 CUDA core 포화율 최대화
    - VRAM 사용: ~400MB (FP16 기준)
    
    아키텍처:
    Input(seq=30, feats) → LSTM(128) → BN → Drop(0.3)
                         → LSTM(64)  → Drop(0.2)
                         → Dense(32, relu) → Dense(1, sigmoid)
    """

    def __init__(self, lite_mode: bool = False, gpu_configured: bool = False):
        cfg = LSTM_CONFIG_LITE if lite_mode else LSTM_CONFIG
        self.cfg = cfg
        self.model = None
        self.scaler = RobustScaler()
        self.gpu_configured = gpu_configured

    def _build_sequences(self, X: np.ndarray) -> np.ndarray:
        """(n, feats) → (n-seq, seq, feats) — 롤링 윈도우"""
        seq_len = self.cfg["seq_len"]
        n = len(X) - seq_len
        if n <= 0:
            return np.empty((0, seq_len, X.shape[1]), dtype=np.float32)
        out = np.lib.stride_tricks.sliding_window_view(
            X, (seq_len, X.shape[1])
        ).reshape(n, seq_len, X.shape[1])
        return out.astype(np.float32)

    def _build_model(self, n_features: int):
        """RTX 4060 Tensor Core 최적 아키텍처"""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import (
            LSTM, Dense, Dropout, BatchNormalization,
            Input
        )
        from tensorflow.keras.optimizers import Adam

        cfg = self.cfg
        model = Sequential([
            Input(shape=(cfg["seq_len"], n_features)),
            LSTM(cfg["units_1"], return_sequences=True),
            BatchNormalization(),
            Dropout(cfg["dropout_rate"]),
            LSTM(cfg["units_2"], return_sequences=False),
            Dropout(cfg["dropout_rate"] * 0.7),
            Dense(cfg["dense_units"], activation="relu"),
            # FP16 출력: 마지막 Dense는 float32로 캐스팅 (수치 안정)
            Dense(1, activation="sigmoid", dtype="float32"),
        ])
        model.compile(
            optimizer=Adam(learning_rate=cfg["learning_rate"]),
            loss="binary_crossentropy",
            metrics=["accuracy"]
        )
        return model

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LSTMPredictor":
        from tensorflow.keras.callbacks import (
            EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
        )

        X_s = self.scaler.fit_transform(X).astype(np.float32)
        X_seq = self._build_sequences(X_s)
        y_seq = y.values[self.cfg["seq_len"]:].astype(np.float32)

        if len(X_seq) == 0:
            raise ValueError("시퀀스 생성 실패: 데이터 부족")

        self.model = self._build_model(X.shape[1])

        callbacks = [
            EarlyStopping(patience=12, restore_best_weights=True, monitor="val_loss"),
            ReduceLROnPlateau(patience=6, factor=0.5, min_lr=1e-6),
        ]

        self.model.fit(
            X_seq, y_seq,
            epochs=self.cfg["epochs"],
            batch_size=self.cfg["batch_size"],  # RTX 4060 최적: 64
            validation_split=0.15,
            callbacks=callbacks,
            verbose=0
        )
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("fit() 먼저 호출 필요")
        X_s = self.scaler.transform(X).astype(np.float32)
        X_seq = self._build_sequences(X_s)
        if len(X_seq) == 0:
            return np.array([])
        return self.model.predict(X_seq, batch_size=self.cfg["batch_size"],
                                  verbose=0).flatten()


# ─────────────────────────────────────────────────
# § 앙상블 오케스트레이터
# ─────────────────────────────────────────────────

@dataclass
class EnsembleConfig:
    horizon: int   = 5
    xgb_weight: float = 0.55
    lstm_weight: float = 0.45
    n_splits: int  = 5
    threshold_buy: float = 0.55
    lite_mode: bool = False     # Ollama 동시 실행 시 True


class EnsemblePredictor:
    """
    XGBoost(GPU) + LSTM(FP16) 가중 앙상블

    VRAM 예산 (RTX 4060 8GB):
    ┌─────────────────────┬──────────┐
    │ TF 예약             │ 6,144 MB │
    │  └ LSTM 파라미터    │    ~2 MB │
    │  └ 배치 활성화      │  ~400 MB │
    │  └ 그래디언트(FP16) │  ~200 MB │
    │ XGBoost GPU         │  ~512 MB │
    │ OS / 드라이버       │ ~1,500MB │
    │ 여유 (Ollama 공존)  │ ~1,344MB │
    └─────────────────────┴──────────┘
    """

    def __init__(self, config: Optional[EnsembleConfig] = None):
        self.config = config or EnsembleConfig()

        # GPU 설정
        vram_limit = 4096 if self.config.lite_mode else 6144
        gpu_info = configure_gpu(vram_limit_mb=vram_limit, verbose=True)
        self._gpu_ok = gpu_info["gpu_available"]

        self.xgb = XGBPredictor(use_gpu=self._gpu_ok)
        self.lstm = LSTMPredictor(
            lite_mode=self.config.lite_mode,
            gpu_configured=self._gpu_ok
        )
        self._trained = False
        self._feat_cols: list[str] = []

    def fit(self, feature_df: pd.DataFrame) -> list[dict]:
        TARGET = ["target_direction", "target_return"]
        self._feat_cols = [c for c in feature_df.columns if c not in TARGET]
        X = feature_df[self._feat_cols]
        y = feature_df["target_direction"]

        tscv = TimeSeriesSplit(n_splits=self.config.n_splits)
        cv_results = []

        print(f"\n🔄 Walk-Forward CV ({self.config.n_splits} folds) | GPU: {'✅' if self._gpu_ok else '⚠️ CPU'}")

        for fold, (tr_idx, te_idx) in enumerate(tscv.split(X)):
            X_tr, X_te = X.iloc[tr_idx], X.iloc[te_idx]
            y_tr, y_te = y.iloc[tr_idx], y.iloc[te_idx]

            # XGBoost fold
            xgb_f = XGBPredictor(use_gpu=self._gpu_ok)
            xgb_f.fit(X_tr, y_tr, eval_set=(X_te, y_te))
            xgb_prob = xgb_f.predict_proba(X_te)

            # LSTM fold
            lstm_prob = xgb_prob  # fallback
            seq_len = self.lstm.cfg["seq_len"]
            if len(X_tr) > seq_len * 3:
                try:
                    lstm_f = LSTMPredictor(lite_mode=self.config.lite_mode,
                                           gpu_configured=self._gpu_ok)
                    lstm_f.fit(X_tr, y_tr)
                    ctx = pd.concat([X_tr.iloc[-seq_len:], X_te], ignore_index=True)
                    lstm_all = lstm_f.predict_proba(ctx)
                    if len(lstm_all) >= len(X_te):
                        lstm_prob = lstm_all[-len(X_te):]
                except Exception as e:
                    print(f"    ⚠️  LSTM fold {fold+1} 스킵: {e}")

            # 앙상블
            n = min(len(xgb_prob), len(lstm_prob), len(y_te))
            ens = self.config.xgb_weight * xgb_prob[:n] + \
                  self.config.lstm_weight * lstm_prob[:n]
            pred = (ens >= 0.5).astype(int)

            acc = accuracy_score(y_te.values[:n], pred)
            auc = roc_auc_score(y_te.values[:n], ens)
            cv_results.append({"fold": fold+1, "accuracy": acc, "auc": auc,
                               "n_train": len(X_tr), "n_test": n})
            print(f"  Fold {fold+1}: Acc={acc:.3f} | AUC={auc:.3f} | "
                  f"Train={len(X_tr):,} Test={n:,}")

        # 최종 전체 학습
        print("\n🏋️  최종 모델 학습 (전체 데이터)...")
        self.xgb.fit(X, y)
        self.lstm.fit(X, y)
        self._trained = True

        cv_df = pd.DataFrame(cv_results)
        print(f"\n📊 CV 결과: "
              f"Acc={cv_df['accuracy'].mean():.3f}±{cv_df['accuracy'].std():.3f} | "
              f"AUC={cv_df['auc'].mean():.3f}±{cv_df['auc'].std():.3f}")
        return cv_results

    def predict(self, X: pd.DataFrame) -> dict:
        if not self._trained:
            raise RuntimeError("fit() 먼저 호출 필요")

        X_feat = X[self._feat_cols] if set(self._feat_cols).issubset(X.columns) else X

        xgb_prob = float(self.xgb.predict_proba(X_feat)[-1])
        lstm_all = self.lstm.predict_proba(X_feat)
        lstm_prob = float(lstm_all[-1]) if len(lstm_all) > 0 else xgb_prob

        ens = self.config.xgb_weight * xgb_prob + self.config.lstm_weight * lstm_prob
        confidence = abs(ens - 0.5) * 2

        return {
            "direction_prob": round(ens, 4),
            "signal": "BUY 📈" if ens >= self.config.threshold_buy else "SELL 📉",
            "confidence": round(confidence, 4),
            "xgb_prob":  round(xgb_prob, 4),
            "lstm_prob": round(lstm_prob, 4),
        }

    def top_features(self, n: int = 10) -> pd.Series:
        return self.xgb.feature_importance(n)
