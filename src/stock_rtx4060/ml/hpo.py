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


def _safe_auc(y_true: np.ndarray, prob: np.ndarray) -> float:
    """Safe ROC-AUC — returns 0.5 for degenerate cases."""
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return 0.5
    try:
        from sklearn.metrics import roc_auc_score
        return float(roc_auc_score(y_true, prob))
    except Exception:
        return 0.5


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
    metric: str = "brier",
) -> dict[str, Any]:
    """Run Optuna HPO and return ``{best_params, best_value, study, metric}``.

    Parameters
    ----------
    metric : ``"brier"`` | ``"auc"`` | ``"hybrid"``
        Objective to minimise.

        * ``"brier"`` — mean OOF Brier score (default, calibration-preserving).
        * ``"auc"`` — ``1 - mean OOF AUC`` (maximises discrimination).
        * ``"hybrid"`` — ``0.5 * brier + 0.5 * (1 - auc)`` **(recommended for
          PAPER_CANDIDATE path)**: balances calibration and discrimination.
    """
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

        brier_scores: list[float] = []
        auc_scores: list[float] = []
        _groups = np.arange(len(X)) + horizon
        for fold_idx, (tr, te) in enumerate(cv.split(X, groups=_groups)):
            est = _clone(estimator)
            X_tr = X.iloc[tr] if isinstance(X, pd.DataFrame) else X_arr[tr]
            X_te = X.iloc[te] if isinstance(X, pd.DataFrame) else X_arr[te]
            est.fit(X_tr, y_arr[tr])
            try:
                prob = est.predict_proba(X_te)[:, 1]
            except Exception:
                prob = est.predict(X_te).astype(float)
            brier_scores.append(_safe_brier(y_arr[te], prob))
            auc_scores.append(_safe_auc(y_arr[te], prob))
            # Report composite score for pruning
            _brier_now = float(np.mean(brier_scores))
            _auc_now = float(np.mean(auc_scores))
            if metric == "auc":
                _report = 1.0 - _auc_now
            elif metric == "hybrid":
                _report = 0.5 * _brier_now + 0.5 * (1.0 - _auc_now)
            else:
                _report = _brier_now
            trial.report(_report, step=fold_idx)
            if trial.should_prune():
                raise optuna.TrialPruned()

        mean_brier = float(np.mean(brier_scores))
        mean_auc = float(np.mean(auc_scores))
        if metric == "auc":
            mean_score = 1.0 - mean_auc
        elif metric == "hybrid":
            mean_score = 0.5 * mean_brier + 0.5 * (1.0 - mean_auc)
        else:
            mean_score = mean_brier
        try:
            with MLflowSession(experiment, run_name=f"trial_{trial.number}"):
                log_params({**params, "model": model, "metric": metric})
                log_metrics({"oos_brier": mean_brier, "oos_auc": mean_auc, "objective": mean_score})
                # mlflow 3.x log_input — training fold reference
                try:
                    import mlflow  # type: ignore[import-not-found]
                    if hasattr(mlflow, 'log_input'):
                        input_ds = mlflow.data.from_numpy(np.asarray(X_tr), targets=y_arr[tr], name="hpo_trial_train")
                        mlflow.log_input(input_ds, context="training")
                except Exception:  # pragma: no cover - mlflow 3.x optional
                    pass
        except Exception:  # pragma: no cover - MLflow optional
            _LOG.debug("mlflow logging failed for trial %d", trial.number)
        return mean_score

    study.optimize(_objective, n_trials=n_trials, show_progress_bar=False)

    _write_trial_log(study, experiment=experiment, model=model)

    return {
        "best_params": dict(study.best_params),
        "best_value": float(study.best_value),
        "study": study,
        "metric": metric,
    }


def _write_trial_log(study: Any, *, experiment: str, model: str) -> None:
    """Append HPO trial summary to ``audit_log/hpo_trials.jsonl``.

    Logged fields prevent backtest overfitting analysis: knowing how many
    parameter combinations were tried is essential for adjusting confidence
    in reported metrics (see Bailey et al., Probability of Backtest Overfitting).
    Best-effort — never raises.
    """
    import json
    from datetime import UTC, datetime
    from pathlib import Path

    try:
        completed = [t for t in study.trials if t.state.name == "COMPLETE"]
        record = {
            "ts": datetime.now(UTC).isoformat(timespec="seconds"),
            "experiment": experiment,
            "model": model,
            "n_trials_total": len(study.trials),
            "n_trials_complete": len(completed),
            "n_trials_pruned": sum(1 for t in study.trials if t.state.name == "PRUNED"),
            "best_value": float(study.best_value),
            "best_params": dict(study.best_params),
        }
        log_path = Path("audit_log") / "hpo_trials.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # pragma: no cover - best-effort
        _LOG.debug("hpo trial log write failed")


def _clone(estimator: Any) -> Any:
    """Best-effort sklearn clone that falls back to ``__class__(**params)``."""
    try:
        from sklearn.base import clone

        return clone(estimator)
    except Exception:
        params = getattr(estimator, "get_params", lambda: {})()
        return estimator.__class__(**params)


__all__ = ["run_hpo", "make_journal_storage"]
