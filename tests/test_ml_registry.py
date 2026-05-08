"""Tests for ml.registry MLflow Model Registry helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stock_rtx4060.ml import registry as reg


def test_register_model_calls_mlflow(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")
    captured = {}

    def fake_register(uri, name):
        captured["uri"] = uri
        captured["name"] = name
        return MagicMock(version="1")

    monkeypatch.setattr(reg.mlflow, "register_model", fake_register)
    uri = reg.register_model("RUN_ABC", name="direction_v1")
    assert uri == "runs:/RUN_ABC/model"
    assert captured == {"uri": "runs:/RUN_ABC/model", "name": "direction_v1"}


def test_register_model_raises_when_mlflow_missing(monkeypatch):
    monkeypatch.setattr(reg, "_HAS_MLFLOW", False)
    with pytest.raises(ImportError, match="mlflow"):
        reg.register_model("RUN_X", name="m")


def test_promote_uses_transition_when_supported(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")
    client = MagicMock()
    monkeypatch.setattr(reg, "MlflowClient", lambda: client)
    reg.promote("direction_v1", 2, "Production")
    client.transition_model_version_stage.assert_called_once()


def test_promote_falls_back_to_alias(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")
    client = MagicMock()
    client.transition_model_version_stage.side_effect = RuntimeError("deprecated")
    monkeypatch.setattr(reg, "MlflowClient", lambda: client)
    reg.promote("direction_v1", 2, "Production")
    client.set_registered_model_alias.assert_called_once()


def test_load_production_returns_none_on_failure(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")

    pyfunc = MagicMock()
    pyfunc.load_model.side_effect = RuntimeError("not found")
    monkeypatch.setattr(reg.mlflow, "pyfunc", pyfunc)
    out = reg.load_production("does_not_exist")
    assert out is None


def test_load_production_when_mlflow_missing(monkeypatch):
    monkeypatch.setattr(reg, "_HAS_MLFLOW", False)
    assert reg.load_production("anything") is None


def test_list_versions_when_mlflow_missing(monkeypatch):
    monkeypatch.setattr(reg, "_HAS_MLFLOW", False)
    assert reg.list_versions("anything") == []


def test_list_versions_returns_metadata(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")
    fake_v = MagicMock(
        name="direction_v1",
        version="1",
        current_stage="Production",
        run_id="abc",
        status="READY",
    )
    fake_v.name = "direction_v1"  # MagicMock special: name overrides
    fake_v.version = "1"
    fake_v.current_stage = "Production"
    fake_v.run_id = "abc"
    fake_v.status = "READY"
    client = MagicMock()
    client.search_model_versions.return_value = [fake_v]
    monkeypatch.setattr(reg, "MlflowClient", lambda: client)
    out = reg.list_versions("direction_v1")
    assert out == [
        {
            "name": "direction_v1",
            "version": 1,
            "stage": "Production",
            "run_id": "abc",
            "status": "READY",
        }
    ]


def test_list_versions_returns_empty_on_error(monkeypatch):
    if not getattr(reg, "_HAS_MLFLOW", False):
        pytest.skip("mlflow not installed")
    client = MagicMock()
    client.search_model_versions.side_effect = RuntimeError("network")
    monkeypatch.setattr(reg, "MlflowClient", lambda: client)
    assert reg.list_versions("name") == []


def test_ml_init_proxies_resolve():
    """Verify the lazy proxy functions in stock_rtx4060.ml resolve to real callables."""
    from stock_rtx4060 import ml as ml_pkg

    # PurgedKFold is re-exported directly
    assert ml_pkg.PurgedKFold is not None

    # Lazy proxies
    assert callable(ml_pkg.run_hpo)
    assert callable(ml_pkg.register_model)
    assert callable(ml_pkg.promote)
    assert callable(ml_pkg.load_production)
    assert callable(ml_pkg.list_versions)
    # ``ml_pkg.explain`` may resolve to the submodule once imported; the
    # explicit proxy ``shap_explain`` is always callable.
    assert callable(ml_pkg.shap_explain)
    assert callable(ml_pkg.per_ticker_shap)
    assert callable(ml_pkg.make_lightgbm)
    assert callable(ml_pkg.lightgbm_default_params)


def test_ml_init_lightgbm_default_params_works():
    from stock_rtx4060 import ml as ml_pkg

    params = ml_pkg.lightgbm_default_params(device="cpu")
    assert params["n_estimators"] == 300


def test_ml_init_load_production_when_no_model():
    """Smoke test: load_production proxy returns None for unknown model when mlflow stub is unavailable."""
    from stock_rtx4060 import ml as ml_pkg

    # This will either hit MLflow (returning None for unknown name) or short-circuit
    result = ml_pkg.load_production("__nonexistent_model_xyz__")
    assert result is None


def test_ml_init_list_versions_proxy_returns_list():
    from stock_rtx4060 import ml as ml_pkg

    result = ml_pkg.list_versions("__nonexistent_model_xyz__")
    assert isinstance(result, list)
