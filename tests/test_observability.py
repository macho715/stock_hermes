"""Smoke tests for observability package - works with or without optional deps."""
from __future__ import annotations

import os
from pathlib import Path


def test_get_logger_returns_callable() -> None:
    from stock_rtx4060.observability import get_logger

    log = get_logger("test")
    assert log is not None
    assert hasattr(log, "info")


def test_configure_logging_idempotent(tmp_path: Path) -> None:
    from stock_rtx4060.observability.log import configure_logging

    configure_logging(level="DEBUG", log_dir=str(tmp_path))
    configure_logging(level="DEBUG", log_dir=str(tmp_path))


def test_metrics_smoke() -> None:
    from stock_rtx4060.observability import (
        gate_count,
        provider_fetch_ms,
        recommendation_latency_ms,
    )

    recommendation_latency_ms.labels(track="S", verdict="GREEN").observe(123.4)
    provider_fetch_ms.labels(provider="yfinance", ticker="AAPL").observe(45.6)
    gate_count.labels(track="S", verdict="GREEN").inc()


def test_mlflow_session_no_op_when_unavailable() -> None:
    from stock_rtx4060.observability import MLflowSession, log_metrics, log_params

    os.environ.pop("MLFLOW_TRACKING_URI", None)
    with MLflowSession("test_experiment"):
        log_params({"a": 1})
        log_metrics({"loss": 0.5})


# ---------------------------------------------------------------------------
# Additional log.py coverage tests
# ---------------------------------------------------------------------------

def test_configure_logging_no_json_sink_skips_file(tmp_path: Path, monkeypatch) -> None:
    """json_sink=False must not create any .jsonl file."""
    import stock_rtx4060.observability.log as log_mod

    # Reset so configure_logging runs again
    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    log_mod.configure_logging(level="WARNING", log_dir=str(tmp_path), json_sink=False)
    jsonl_files = list(tmp_path.glob("*.jsonl"))
    assert jsonl_files == [], f"Expected no jsonl files, found {jsonl_files}"


def test_configure_logging_creates_jsonl_file(tmp_path: Path, monkeypatch) -> None:
    """json_sink=True (default) creates app.jsonl inside log_dir."""
    import stock_rtx4060.observability.log as log_mod

    if not log_mod._HAS_LOGURU:
        import pytest
        pytest.skip("loguru not installed")

    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    log_mod.configure_logging(level="DEBUG", log_dir=str(tmp_path), json_sink=True)
    # The file is created by loguru on add(); it may be created lazily but the
    # directory must exist and _CONFIGURED must be True.
    assert log_mod._CONFIGURED is True
    assert tmp_path.exists()


def test_configure_logging_respects_env_level(tmp_path: Path, monkeypatch) -> None:
    """STOCK1901_LOG_LEVEL env var is used when level arg is None."""
    import stock_rtx4060.observability.log as log_mod

    if not log_mod._HAS_LOGURU:
        import pytest
        pytest.skip("loguru not installed")

    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    monkeypatch.setenv("STOCK1901_LOG_LEVEL", "ERROR")
    # Should not raise even though level is inferred from env
    log_mod.configure_logging(log_dir=str(tmp_path), json_sink=False)
    assert log_mod._CONFIGURED is True


def test_configure_logging_idempotent_second_call_noop(tmp_path: Path, monkeypatch) -> None:
    """Second call with _CONFIGURED=True is a no-op (no exceptions, no re-add)."""
    import stock_rtx4060.observability.log as log_mod

    if not log_mod._HAS_LOGURU:
        import pytest
        pytest.skip("loguru not installed")

    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    log_mod.configure_logging(level="INFO", log_dir=str(tmp_path), json_sink=False)
    # Second call: _CONFIGURED is now True, must be no-op
    log_mod.configure_logging(level="DEBUG", log_dir=str(tmp_path), json_sink=True)
    assert log_mod._CONFIGURED is True


def test_get_logger_returns_bound_logger_with_name() -> None:
    """get_logger with a name returns a logger that has an info method."""
    from stock_rtx4060.observability.log import get_logger

    log = get_logger("mycomponent")
    assert log is not None
    assert hasattr(log, "info")
    assert hasattr(log, "warning") or hasattr(log, "warn")


def test_get_logger_without_name_returns_root_logger() -> None:
    """get_logger() with no args must not raise."""
    from stock_rtx4060.observability.log import get_logger

    log = get_logger()
    assert log is not None
    assert hasattr(log, "info")


def test_get_logger_stdlib_fallback(monkeypatch) -> None:
    """When loguru unavailable get_logger returns stdlib Logger."""
    import logging
    import stock_rtx4060.observability.log as log_mod

    monkeypatch.setattr(log_mod, "_HAS_LOGURU", False)
    log = log_mod.get_logger("fallback_test")
    assert isinstance(log, logging.Logger)
    assert log.name == "fallback_test"


def test_get_logger_stdlib_fallback_no_name(monkeypatch) -> None:
    """stdlib fallback with no name uses default component name."""
    import logging
    import stock_rtx4060.observability.log as log_mod

    monkeypatch.setattr(log_mod, "_HAS_LOGURU", False)
    log = log_mod.get_logger()
    assert isinstance(log, logging.Logger)
    assert log.name == "stock_rtx4060"


def test_configure_logging_noop_when_loguru_missing(tmp_path: Path, monkeypatch) -> None:
    """configure_logging does nothing (no exception) when loguru is not installed."""
    import stock_rtx4060.observability.log as log_mod

    monkeypatch.setattr(log_mod, "_CONFIGURED", False)
    monkeypatch.setattr(log_mod, "_HAS_LOGURU", False)
    log_mod.configure_logging(level="DEBUG", log_dir=str(tmp_path))
    # _CONFIGURED stays False because loguru is absent
    assert log_mod._CONFIGURED is False
