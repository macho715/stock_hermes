"""Prometheus metrics for recommendation/provider/advisor flows."""
from __future__ import annotations

from typing import Any

try:
    from prometheus_client import Counter, Histogram
    from prometheus_client import start_http_server as _start_http_server

    _HAS_PROM = True
except ImportError:  # pragma: no cover
    Counter = Histogram = None  # type: ignore[assignment,misc]
    _start_http_server = None  # type: ignore[assignment]
    _HAS_PROM = False


class _NoOp:
    def labels(self, *_: Any, **__: Any) -> _NoOp:
        return self

    def observe(self, *_: Any, **__: Any) -> None:
        pass

    def inc(self, *_: Any, **__: Any) -> None:
        pass

    def time(self) -> _NoOp:  # context manager noop
        return self

    def __enter__(self) -> _NoOp:
        return self

    def __exit__(self, *_: Any) -> None:
        return None


if _HAS_PROM:
    recommendation_latency_ms = Histogram(
        "stock1901_recommendation_latency_ms",
        "Wall-clock latency of full recommendation cycle",
        labelnames=("track", "verdict"),
        buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000),
    )
    provider_fetch_ms = Histogram(
        "stock1901_provider_fetch_ms",
        "Provider OHLCV fetch latency",
        labelnames=("provider", "ticker"),
        buckets=(50, 100, 250, 500, 1000, 2500, 5000),
    )
    gate_count = Counter(
        "stock1901_gate_count_total",
        "Count of risk-gate verdicts emitted",
        labelnames=("track", "verdict"),
    )
    advisor_calls_total = Counter(
        "stock1901_advisor_calls_total",
        "LLM advisor agent invocations",
        labelnames=("agent", "outcome"),
    )
else:
    recommendation_latency_ms = _NoOp()  # type: ignore[assignment]
    provider_fetch_ms = _NoOp()  # type: ignore[assignment]
    gate_count = _NoOp()  # type: ignore[assignment]
    advisor_calls_total = _NoOp()  # type: ignore[assignment]


def start_http_server(port: int = 9100) -> None:
    """Expose /metrics on ``port`` for Prometheus scrape."""
    if _HAS_PROM and _start_http_server is not None:
        _start_http_server(port)
