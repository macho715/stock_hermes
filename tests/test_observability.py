"""Smoke tests for observability package - works with or without optional deps."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


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
    with MLflowSession("test_experiment") as run:
        log_params({"a": 1})
        log_metrics({"loss": 0.5})
