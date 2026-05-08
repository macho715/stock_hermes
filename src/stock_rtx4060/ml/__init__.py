"""ML upgrade package: PurgedKFold, Optuna HPO, MLflow registry, SHAP, LightGBM."""

from __future__ import annotations

from typing import Any

from .cv import PurgedKFold


def _proxy_call(submodule: str, fn_name: str, *args: Any, **kwargs: Any) -> Any:
    """Lazy import + dispatch to keep optional deps out of the import path."""
    from importlib import import_module

    mod = import_module(f"{__name__}.{submodule}")
    return getattr(mod, fn_name)(*args, **kwargs)


def run_hpo(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("hpo", "run_hpo", *args, **kwargs)


def register_model(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("registry", "register_model", *args, **kwargs)


def promote(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("registry", "promote", *args, **kwargs)


def load_production(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("registry", "load_production", *args, **kwargs)


def list_versions(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("registry", "list_versions", *args, **kwargs)


def shap_explain(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("explain", "explain", *args, **kwargs)


def per_ticker_shap(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("explain", "per_ticker_shap", *args, **kwargs)


def make_lightgbm(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("lightgbm_model", "make_lightgbm", *args, **kwargs)


def lightgbm_default_params(*args: Any, **kwargs: Any) -> Any:
    return _proxy_call("lightgbm_model", "lightgbm_default_params", *args, **kwargs)


__all__ = [
    "PurgedKFold",
    "run_hpo",
    "register_model",
    "promote",
    "load_production",
    "list_versions",
    "shap_explain",
    "per_ticker_shap",
    "make_lightgbm",
    "lightgbm_default_params",
]


def __getattr__(name: str) -> Any:
    """Module-level lazy attribute access for ``explain``.

    Python's import machinery binds ``ml.explain`` to the submodule whenever
    that submodule is imported. We intercept attribute lookup so that
    ``from stock_rtx4060.ml import explain`` returns the function (when no
    submodule has been loaded yet) and otherwise expose ``shap_explain``.
    """
    if name == "explain":
        return shap_explain
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
