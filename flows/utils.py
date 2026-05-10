"""Shared Prefect helpers for the ``flows/`` deployment package.

Design goals
------------
* Make ``flow``/``task`` decorators cleanly importable even when ``prefect``
  is missing — tests run in a slim environment that does not pin Prefect.
* Provide :func:`slack_on_failure` (best-effort failure notifier) and
  :func:`with_retries` (decorator factory) used by every flow's tasks.
* Provide :func:`get_run_logger` shim so flow code can ``from flows.utils
  import get_run_logger`` without conditionalising on Prefect availability.
"""

from __future__ import annotations

import functools
import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("flows")

F = TypeVar("F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Optional Prefect import — fall back to no-op decorators when absent.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - exercised only when prefect is installed
    from prefect import flow as _prefect_flow
    from prefect import get_run_logger as _prefect_get_run_logger
    from prefect import task as _prefect_task

    _HAS_PREFECT = True
except Exception:  # noqa: BLE001 - prefect is optional
    _prefect_flow = None  # type: ignore[assignment]
    _prefect_task = None  # type: ignore[assignment]
    _prefect_get_run_logger = None  # type: ignore[assignment]
    _HAS_PREFECT = False


def _noop_decorator_factory() -> Callable[..., Callable[[F], F]]:
    """Return a callable that mimics ``@prefect.flow``/``@prefect.task``.

    Supports both bare usage (``@flow``) and parameterised usage
    (``@flow(name='x')``). The wrapped callable is returned unchanged.
    """

    def _factory(*dargs: Any, **dkwargs: Any) -> Any:
        # Bare usage: @flow / @task — first positional is the function itself.
        if len(dargs) == 1 and not dkwargs and callable(dargs[0]):
            return dargs[0]

        def _wrap(fn: F) -> F:
            return fn

        return _wrap

    return _factory


if _HAS_PREFECT:  # pragma: no cover - happy path requires prefect installed
    flow = _prefect_flow  # type: ignore[assignment]
    task = _prefect_task  # type: ignore[assignment]
else:
    flow = _noop_decorator_factory()  # type: ignore[assignment]
    task = _noop_decorator_factory()  # type: ignore[assignment]


def get_run_logger() -> logging.Logger:
    """Return the Prefect run logger when active, else the module logger."""
    if _HAS_PREFECT and _prefect_get_run_logger is not None:
        try:
            return _prefect_get_run_logger()  # type: ignore[no-any-return]
        except Exception:  # noqa: BLE001 - context may be missing outside a run
            pass
    return logger


# ---------------------------------------------------------------------------
# Slack failure notifier (best-effort, never raises)
# ---------------------------------------------------------------------------
def slack_on_failure(message: str, *, webhook_url: str | None = None) -> None:
    """Post ``message`` to a Slack webhook on flow/task failure.

    Resolution order for the URL:
      1. explicit ``webhook_url`` kwarg
      2. ``STOCK1901_SLACK_WEBHOOK_URL`` env var
    A missing URL logs a warning and exits silently — failure notifications
    are best-effort and must not raise inside an exception handler.
    """
    url = webhook_url or os.environ.get("STOCK1901_SLACK_WEBHOOK_URL")
    if not url:
        logger.warning("slack_on_failure: no webhook URL configured; skipping notification")
        return
    payload = {"text": f":rotating_light: stock_rtx4060 flow failure:\n{message}"}
    try:
        import httpx

        resp = httpx.post(url, json=payload, timeout=10.0)
        if not (200 <= resp.status_code < 300):
            logger.warning("slack_on_failure: webhook returned %s", resp.status_code)
    except Exception as exc:  # noqa: BLE001 - failure notifier must never raise
        logger.warning("slack_on_failure: request failed: %s", exc)


# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------
def with_retries(*, retries: int = 3, retry_delay_seconds: int = 60) -> Callable[[F], F]:
    """Return a decorator that retries the wrapped function on exception.

    When Prefect is installed, the wrapped function is additionally registered
    as a ``@task`` with Prefect-native retry semantics so the orchestrator can
    surface retry events in its UI. Without Prefect, the wrapper itself
    implements simple ``time.sleep``-based retry.
    """

    if retries < 0:
        raise ValueError("retries must be >= 0")

    def _decorator(fn: F) -> F:
        if _HAS_PREFECT and _prefect_task is not None:  # pragma: no cover - prefect path
            return _prefect_task(retries=retries, retry_delay_seconds=retry_delay_seconds)(fn)  # type: ignore[no-any-return]

        @functools.wraps(fn)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: BaseException | None = None
            for attempt in range(retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - propagated after retries exhaust
                    last_exc = exc
                    if attempt >= retries:
                        break
                    logger.warning(
                        "task %s attempt %d/%d failed: %s — sleeping %ds",
                        getattr(fn, "__name__", "<callable>"),
                        attempt + 1,
                        retries + 1,
                        exc,
                        retry_delay_seconds,
                    )
                    if retry_delay_seconds > 0:
                        time.sleep(retry_delay_seconds)
            assert last_exc is not None  # for type-checkers
            raise last_exc

        return _wrapper  # type: ignore[return-value]

    return _decorator


__all__ = [
    "flow",
    "task",
    "get_run_logger",
    "slack_on_failure",
    "with_retries",
]
