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


# ---------------------------------------------------------------------------
# Additional tests: force _HAS_MLFLOW=True with mocked mlflow module so we
# exercise code paths that are normally guarded behind the import check.
# ---------------------------------------------------------------------------


def test_register_model_forced_mock(monkeypatch):
    """register_model builds the correct URI and calls mlflow.register_model."""
    mock_mlflow = MagicMock()
    mock_mlflow.register_model.return_value = MagicMock(version="3")
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "mlflow", mock_mlflow)
    uri = reg.register_model("RUN_FORCED", name="test_model")
    assert uri == "runs:/RUN_FORCED/model"
    mock_mlflow.register_model.assert_called_once_with("runs:/RUN_FORCED/model", "test_model")


def test_promote_forced_mock_transition(monkeypatch):
    """promote calls transition_model_version_stage with correct args."""
    mock_client = MagicMock()
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "MlflowClient", lambda: mock_client)
    reg.promote("my_model", 1, "Staging")
    mock_client.transition_model_version_stage.assert_called_once_with(
        name="my_model", version="1", stage="Staging"
    )


def test_promote_forced_mock_alias_fallback(monkeypatch):
    """promote falls back to set_registered_model_alias when stage raises."""
    mock_client = MagicMock()
    mock_client.transition_model_version_stage.side_effect = Exception("stages removed")
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "MlflowClient", lambda: mock_client)
    reg.promote("my_model", 5, "Production")
    mock_client.set_registered_model_alias.assert_called_once_with(
        name="my_model", alias="production", version="5"
    )


def test_load_production_forced_mock_success(monkeypatch):
    """load_production returns pyfunc model on first try."""
    fake_model = MagicMock()
    mock_pyfunc = MagicMock()
    mock_pyfunc.load_model.return_value = fake_model
    mock_mlflow = MagicMock()
    mock_mlflow.pyfunc = mock_pyfunc
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "mlflow", mock_mlflow)
    result = reg.load_production("direction_v1")
    assert result is fake_model
    mock_pyfunc.load_model.assert_called_once_with("models:/direction_v1/Production")


def test_load_production_forced_mock_alias_fallback(monkeypatch):
    """load_production falls back to @production alias when stage lookup fails."""
    fake_model = MagicMock()
    mock_pyfunc = MagicMock()
    # First call raises, second (alias) succeeds
    mock_pyfunc.load_model.side_effect = [RuntimeError("no stage"), fake_model]
    mock_mlflow = MagicMock()
    mock_mlflow.pyfunc = mock_pyfunc
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "mlflow", mock_mlflow)
    result = reg.load_production("direction_v1")
    assert result is fake_model
    assert mock_pyfunc.load_model.call_count == 2


def test_load_production_forced_both_fail_returns_none(monkeypatch):
    """load_production returns None when both stage and alias lookup fail."""
    mock_pyfunc = MagicMock()
    mock_pyfunc.load_model.side_effect = RuntimeError("always fails")
    mock_mlflow = MagicMock()
    mock_mlflow.pyfunc = mock_pyfunc
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "mlflow", mock_mlflow)
    result = reg.load_production("nonexistent")
    assert result is None


def test_list_versions_forced_mock(monkeypatch):
    """list_versions correctly maps ModelVersion fields to dicts."""
    v = MagicMock()
    v.name = "dir_v2"
    v.version = "7"
    v.current_stage = "Staging"
    v.run_id = "run999"
    v.status = "READY"
    mock_client = MagicMock()
    mock_client.search_model_versions.return_value = [v]
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "MlflowClient", lambda: mock_client)
    out = reg.list_versions("dir_v2")
    assert out == [
        {
            "name": "dir_v2",
            "version": 7,
            "stage": "Staging",
            "run_id": "run999",
            "status": "READY",
        }
    ]


def test_list_versions_forced_mock_empty_result(monkeypatch):
    """list_versions returns [] when no versions found."""
    mock_client = MagicMock()
    mock_client.search_model_versions.return_value = []
    monkeypatch.setattr(reg, "_HAS_MLFLOW", True)
    monkeypatch.setattr(reg, "MlflowClient", lambda: mock_client)
    out = reg.list_versions("no_model")
    assert out == []


def test_require_mlflow_raises_import_error_when_missing(monkeypatch):
    """_require_mlflow raises ImportError with helpful message."""
    monkeypatch.setattr(reg, "_HAS_MLFLOW", False)
    with pytest.raises(ImportError, match="pip install"):
        reg._require_mlflow()
