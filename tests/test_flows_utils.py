"""Phase 7: tests for flows/utils.py — verify no-op decorators, retry, slack notifier."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flows import utils as flow_utils  # noqa: E402


def test_flow_decorator_returns_callable_without_prefect():
    @flow_utils.flow(name="example")
    def my_flow(x: int) -> int:
        return x * 2

    assert callable(my_flow)
    assert my_flow(3) == 6


def test_flow_decorator_bare_usage():
    @flow_utils.flow
    def my_flow(x: int) -> int:
        return x + 1

    assert callable(my_flow)
    assert my_flow(2) == 3


def test_task_decorator_with_kwargs_returns_callable():
    @flow_utils.task(name="t")
    def my_task(x: int) -> int:
        return x + 10

    assert callable(my_task)
    assert my_task(5) == 15


def test_get_run_logger_returns_logger():
    logger = flow_utils.get_run_logger()
    assert isinstance(logger, logging.Logger)


def test_slack_on_failure_logs_warning_when_no_webhook(caplog, monkeypatch):
    monkeypatch.delenv("STOCK1901_SLACK_WEBHOOK_URL", raising=False)
    caplog.set_level(logging.WARNING, logger="flows")
    flow_utils.slack_on_failure("test failure")
    assert any("no webhook URL" in rec.getMessage() for rec in caplog.records)


def test_slack_on_failure_handles_httpx_error(monkeypatch):
    """When httpx raises, slack_on_failure must NOT propagate."""
    monkeypatch.setenv("STOCK1901_SLACK_WEBHOOK_URL", "https://example.invalid/hook")

    class _Boom:
        @staticmethod
        def post(*_a, **_k):
            raise RuntimeError("network down")

    monkeypatch.setitem(sys.modules, "httpx", _Boom)
    # Should swallow exception silently.
    flow_utils.slack_on_failure("boom")


def test_with_retries_succeeds_on_first_try():
    counter = {"n": 0}

    @flow_utils.with_retries(retries=2, retry_delay_seconds=0)
    def fn() -> str:
        counter["n"] += 1
        return "ok"

    assert fn() == "ok"
    assert counter["n"] == 1


def test_with_retries_retries_on_exception():
    counter = {"n": 0}

    @flow_utils.with_retries(retries=2, retry_delay_seconds=0)
    def fn() -> str:
        counter["n"] += 1
        if counter["n"] < 3:
            raise ValueError("retry me")
        return "ok"

    if flow_utils._HAS_PREFECT:
        pytest.skip("prefect-task path is exercised via prefect runtime, not this unit test")
    assert fn() == "ok"
    assert counter["n"] == 3


def test_with_retries_raises_after_exhaustion():
    @flow_utils.with_retries(retries=1, retry_delay_seconds=0)
    def fn() -> None:
        raise RuntimeError("permanent failure")

    if flow_utils._HAS_PREFECT:
        pytest.skip("prefect-task path is exercised via prefect runtime, not this unit test")
    with pytest.raises(RuntimeError, match="permanent failure"):
        fn()


def test_with_retries_rejects_negative():
    with pytest.raises(ValueError):
        flow_utils.with_retries(retries=-1)
