"""Prefect deployment package for stock_rtx4060 (Phase 7).

This package is intentionally OUTSIDE ``src/`` because it ships with the
repository as a runtime artefact for the Prefect agent rather than as a
library distributed via the ``stock_rtx4060`` package.  Each flow is
schedulable via Prefect 2/3 deployments (cron schedule defined in the
flow module). Flows degrade gracefully into plain Python callables when
Prefect is not installed — the CI/test environment does not require it.
"""

from __future__ import annotations

__all__ = ["daily_krx_flow", "daily_us_flow", "research_weekly_flow"]


def __getattr__(name: str):  # pragma: no cover - lazy loader for top-level helpers
    """Lazily import flow modules so a missing optional dep does not poison
    package import."""

    if name == "daily_krx_flow":
        from .daily_krx import daily_krx_flow

        return daily_krx_flow
    if name == "daily_us_flow":
        from .daily_us import daily_us_flow

        return daily_us_flow
    if name == "research_weekly_flow":
        from .research_weekly import research_weekly_flow

        return research_weekly_flow
    raise AttributeError(f"module 'flows' has no attribute {name!r}")
