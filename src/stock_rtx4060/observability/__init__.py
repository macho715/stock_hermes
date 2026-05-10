"""Observability package: structured logs, metrics, MLflow tracking."""
from .log import configure_logging, get_logger
from .metrics import (
    advisor_calls_total,
    gate_count,
    provider_fetch_ms,
    recommendation_latency_ms,
    start_http_server,
)
from .mlflow_client import MLflowSession, log_metrics, log_params

__all__ = [
    "get_logger",
    "configure_logging",
    "recommendation_latency_ms",
    "provider_fetch_ms",
    "gate_count",
    "advisor_calls_total",
    "start_http_server",
    "MLflowSession",
    "log_metrics",
    "log_params",
]
