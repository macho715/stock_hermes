"""Optuna-driven hyper-parameter optimisation with purged cross-validation.

The objective is the mean out-of-fold Brier score. Lower is better. Every
trial is logged to MLflow as a nested run when MLflow is available; when not,
the optimisation still runs and returns a plain dict.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss

from ..observability import MLflowSession, get_logger, log_metrics, log_params
from .cv import PurgedKFold

ModelKind = Literal["xgboost", "lightgbm"]

_LOG = get_logger(__name__)


def _require_optuna() -> Any:
    try:
        import optuna  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError("optuna is required for run_hpo(). Install with: pip install 'optuna>=4.8'") from exc
    return optuna


def make_journal_storage(path: str) -> Any:
    """Create an Optuna ``JournalStorage`` backed by a local file.

    JournalStorage is the recommended zero-dependency storage for multi-process
    HPO runs on a single machine (no RDB server required).  It uses file locking
    internally so multiple workers can share the same study safely.

    Parameters
    ----------
    path:
        File path for the journal log (e.g. ``"./optuna_journal.log"``).
        The file is created if it does not exist.

    Returns
    -------
    ``optuna.storages.JournalStorage`` instance.

    Example
    -------
    >>> storage = make_journal_storage("./runs/study.log")
    >>> result = run_hpo(X, y, storage=storage, study_name="my_study")

    Notes
    -----
    For large-scale distributed HPO across many nodes use
    ``GrpcStorageProxy`` instead — see
    https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.GrpcStorageProxy.html
    """
    _require_optuna()
    from optuna.storages import JournalStorage  # type: ignore[import-not-found]
    from optuna.storages.journal import JournalFileBackend  # type: ignore[import-not-found]

    return JournalStorage(JournalFileBackend(path))


def _make_xgb(trial: Any) -> Any:
    from xgboost import XGBClassifier  # type: ignore[import-not-found]

    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 7),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 5.0, log=True),
        "tree_method": "hist",
        "verbosity": 0,
        "random_state": 42,
        "n_jobs": 2,
        "eval_metric": "logloss",
    }
    return XGBClassifier(**params), params


def _make_lgbm(trial: Any) -> Any:
    from .lightgbm_model import make_lightgbm

    params = {
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 5.0, log=True),
        "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 5, 40),
    }
    model = make_lightgbm(**params)
    return model, params


def _safe_brier(y_true: np.ndarray, prob: np.ndarray) -> float:
    if len(y_true) == 0:
        return 0.5
    try:
        return float(brier_score_loss(y_true, prob))
    except Exception:
        return 0.5


def run_hpo(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    model: ModelKind = "xgboost",
    n_trials: int = 50,
    cv: PurgedKFold | None = None,
    horizon: int = 5,
    experiment: str = "direction_v1",
    study_name: str | None = None,
    storage: str | None = None,
) -> dict[str, Any]:
    """Run Optuna HPO and return ``{best_params, best_value, study}``."""
    optuna = _require_optuna()
    cv = cv or PurgedKFold(n_splits=5, embargo_pct=0.01)
    X_arr = X.values if isinstance(X, pd.DataFrame) else np.asarray(X)
    y_arr = np.asarray(y).astype(int)

    sampler = optuna.samplers.TPESampler(seed=42)
    pruner = optuna.pruners.MedianPruner()
    study = optuna.create_study(
        direction="minimize",
        sampler=sampler,
        pruner=pruner,
        study_name=study_name,
        storage=storage,
        load_if_exists=storage is not None,
    )

    def _objective(trial: Any) -> float:
        if model == "xgboost":
            estimator, params = _make_xgb(trial)
        elif model == "lightgbm":
            estimator, params = _make_lgbm(trial)
        else:
            raise ValueError(f"unsupported model {model!r}")

        scores: list[float] = []
        _groups = np.arange(len(X)) + horizon
        for fold_idx, (tr, te) in enumerate(cv.split(X, groups=_groups)):
            est = _clone(estimator)
            est.fit(X_arr[tr], y_arr[tr])
            try:
                prob = est.predict_proba(X_arr[te])[:, 1]
            except Exception:
                prob = est.predict(X_arr[te]).astype(float)
            scores.append(_safe_brier(y_arr[te], prob))
            trial.report(float(np.mean(scores)), step=fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        mean_score = float(np.mean(scores))
        try:
            with MLflowSession(experiment, run_name=f"trial_{trial.number}"):
                log_params({**params, "model": model})
                log_metrics({"oos_brier": mean_score})
                # mlflow 3.x log_input — training fold reference
                try:
                    import mlflow  # type: ignore[import-not-found]
                    if hasattr(mlflow, 'log_input'):
                        input_ds = mlflow.data.from_numpy(X_arr[tr], targets=y_arr[tr], name="hpo_trial_train")
                        mlflow.log_input(input_ds, context="training")
                except Exception:  # pragma: no cover - mlflow 3.x optional
                    pass
        except Exception:  # pragma: no cover - MLflow optional
            _LOG.debug("mlflow logging failed for trial %d", trial.number)
        return mean_score

    study.optimize(_objective, n_trials=n_trials, show_progress_bar=False)

    return {
        "best_params": dict(study.best_params),
        "best_value": float(study.best_value),
        "study": study,
    }


def _clone(estimator: Any) -> Any:
    """Best-effort sklearn clone that falls back to ``__class__(**params)``."""
    try:
        from sklearn.base import clone

        return clone(estimator)
    except Exception:
        params = getattr(estimator, "get_params", lambda: {})()
        return estimator.__class__(**params)


__all__ = ["run_hpo", "make_journal_storage"]
