"""Thin MLflow wrapper. Becomes a no-op when mlflow is unavailable."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Mapping

try:
    import mlflow  # type: ignore[import-not-found]

    _HAS_MLFLOW = True
except ImportError:  # pragma: no cover
    mlflow = None  # type: ignore[assignment]
    _HAS_MLFLOW = False


def _tracking_uri() -> str | None:
    return os.environ.get("MLFLOW_TRACKING_URI")


@contextmanager
def MLflowSession(experiment: str, *, run_name: str | None = None, tags: Mapping[str, str] | None = None) -> Iterator[Any]:
    """Context manager that opens an MLflow run when tracking is configured.

    Yields ``None`` when MLflow is missing, so callers can ``with ... as run`` safely.
    """
    if not _HAS_MLFLOW:
        yield None
        return
    uri = _tracking_uri()
    if uri:
        mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=run_name, tags=dict(tags or {})) as run:
        yield run


def log_params(params: Mapping[str, Any]) -> None:
    if _HAS_MLFLOW:
        mlflow.log_params(dict(params))


def log_metrics(metrics: Mapping[str, float], *, step: int | None = None) -> None:
    if _HAS_MLFLOW:
        mlflow.log_metrics(dict(metrics), step=step)


def log_artifact(local_path: str | os.PathLike[str], *, artifact_path: str | None = None) -> None:
    if _HAS_MLFLOW:
        mlflow.log_artifact(str(local_path), artifact_path=artifact_path)
