"""LightGBM factory mirroring ``ensemble_model._make_xgb`` semantics.

Provides ``make_lightgbm`` and ``lightgbm_default_params`` so the rest of the
codebase can use LightGBM in the same shape as XGBoost. LightGBM is an
optional dependency; importing this module does not import lightgbm itself.
"""

from __future__ import annotations

from typing import Any, Literal

DeviceKind = Literal["cpu", "gpu", "cuda"]
BoostingKind = Literal["gbdt", "dart"]


def lightgbm_default_params(device: str = "cpu") -> dict[str, Any]:
    """Return sensible defaults for a directional-classification LGBMClassifier."""
    params: dict[str, Any] = {
        "n_estimators": 300,
        "max_depth": 4,
        "num_leaves": 15,  # 2 ** max_depth - 1 keeps the tree balanced
        "learning_rate": 0.04,
        "subsample": 0.85,
        "subsample_freq": 1,
        "colsample_bytree": 0.85,
        "min_data_in_leaf": 20,
        "reg_lambda": 1.5,
        "reg_alpha": 0.05,
        "objective": "binary",
        "random_state": 42,
        "n_jobs": 4,
        "verbosity": -1,
    }
    if device in {"gpu", "cuda"}:
        params["device_type"] = device
    return params


def make_lightgbm(
    *,
    device: str = "cpu",
    boosting: BoostingKind = "gbdt",
    **kwargs: Any,
) -> Any:
    """Construct a ``lightgbm.LGBMClassifier``.

    Raises
    ------
    ImportError
        If lightgbm is not installed. The error message includes an install
        hint so callers can self-heal.
    """
    try:
        from lightgbm import LGBMClassifier  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - import guard
        raise ImportError(
            "lightgbm is required for make_lightgbm(). " "Install with: pip install 'lightgbm>=4.5'"
        ) from exc

    params = lightgbm_default_params(device=device)
    params["boosting_type"] = boosting
    params.update(kwargs)
    return LGBMClassifier(**params)


__all__ = ["make_lightgbm", "lightgbm_default_params"]
