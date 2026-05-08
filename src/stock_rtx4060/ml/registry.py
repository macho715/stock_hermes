"""MLflow Model Registry helpers.

All functions degrade gracefully when MLflow is unavailable:
- ``register_model`` and ``promote`` raise :class:`ImportError`
- ``load_production`` and ``list_versions`` return ``None`` / ``[]``
"""

from __future__ import annotations

from typing import Any, Literal

try:
    import mlflow  # type: ignore[import-not-found]
    from mlflow.tracking import MlflowClient  # type: ignore[import-not-found]

    _HAS_MLFLOW = True
except ImportError:  # pragma: no cover - import guard
    mlflow = None  # type: ignore[assignment]
    MlflowClient = None  # type: ignore[assignment]
    _HAS_MLFLOW = False


Stage = Literal["Staging", "Production", "Archived", "None"]


def _require_mlflow() -> None:
    if not _HAS_MLFLOW:
        raise ImportError(
            "mlflow is required for model registry operations. " "Install with: pip install 'mlflow>=2.16'"
        )


def register_model(run_id: str, name: str = "direction_v1") -> str:
    """Register the model artifact of an MLflow run and return its URI.

    Parameters
    ----------
    run_id:
        MLflow run id holding a logged ``model`` artifact.
    name:
        Registered-model name in the registry.
    """
    _require_mlflow()
    model_uri = f"runs:/{run_id}/model"
    mlflow.register_model(model_uri, name)
    return model_uri


def promote(name: str, version: int, stage: Stage) -> None:
    """Move a registered model version to ``stage``.

    Uses the modern alias-based API when available, falling back to
    ``transition_model_version_stage`` for older MLflow versions.
    """
    _require_mlflow()
    client = MlflowClient()
    try:
        client.transition_model_version_stage(name=name, version=str(version), stage=stage)
    except Exception:
        # MLflow 3.x deprecates stages in favour of aliases.
        alias = stage.lower()
        client.set_registered_model_alias(name=name, alias=alias, version=str(version))


def load_production(name: str = "direction_v1") -> Any:
    """Load the Production-stage model. Returns ``None`` when unavailable."""
    if not _HAS_MLFLOW:
        return None
    try:
        return mlflow.pyfunc.load_model(f"models:/{name}/Production")
    except Exception:
        # Fall back to alias lookup for newer MLflow versions
        try:
            return mlflow.pyfunc.load_model(f"models:/{name}@production")
        except Exception:
            return None


def list_versions(name: str) -> list[dict[str, Any]]:
    """Return metadata for every registered version of ``name``.

    Returns ``[]`` when MLflow is unavailable or the model is unknown.
    """
    if not _HAS_MLFLOW:
        return []
    try:
        client = MlflowClient()
        versions = client.search_model_versions(f"name='{name}'")
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for v in versions:
        out.append(
            {
                "name": getattr(v, "name", name),
                "version": int(getattr(v, "version", 0) or 0),
                "stage": getattr(v, "current_stage", None),
                "run_id": getattr(v, "run_id", None),
                "status": getattr(v, "status", None),
            }
        )
    return out


__all__ = ["register_model", "promote", "load_production", "list_versions"]
