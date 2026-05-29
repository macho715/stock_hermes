"""Wrapper around Microsoft RD-Agent for automated factor mining.

Delegates to ``docker_runner.run_docker_factor_mining()`` for execution.
Returns an empty list and emits a warning when RDAGENT_ENABLED=false or
Docker is unavailable, so CI can carry on without the heavy dependency.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from ...observability import get_logger
from .docker_runner import run_docker_factor_mining

_LOGGER = get_logger("factors.rd_agent.runner")


def run_factor_mining(
    universe: Iterable[str],
    cycles: int,
    budget_usd: float,
    output_dir: Path = Path("src/stock_rtx4060/factors/discovered"),
) -> list[Path]:
    """Run RD-Agent factor mining via Docker and return paths of newly produced factor modules.

    Parameters
    ----------
    universe:
        Tickers RD-Agent should mine factors for.  Passed through to the Docker runner.
    cycles:
        Number of evolution cycles to run (each cycle == hypothesis -> factor ->
        backtest -> feedback loop in RD-Agent terminology).
    budget_usd:
        Hard cap on LLM spend — RD-Agent honours this via its accountant.
    output_dir:
        Ignored (kept for API compatibility).  The Docker runner uses its own
        session-based output directory under ``discovered/{session_id}/``.

    Returns
    -------
    list[Path]
        Paths to newly created factor ``.py`` modules.  Empty list if
        RDAGENT_ENABLED=false or Docker is unavailable.
    """
    # Check RDAGENT_ENABLED flag for graceful degradation
    # Ensure output directory exists (delegated runner also creates it, but we
    # guarantee it here so callers can rely on the directory being present)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    enabled = os.environ.get("RDAGENT_ENABLED", "").lower()
    if enabled not in ("1", "true", "yes"):
        universe_list = list(universe)
        _LOGGER.warning(
            "RDAGENT_ENABLED=%s — skipping factor mining. "
            "Set RDAGENT_ENABLED=true to enable. "
            "universe=%s cycles=%d budget=%.2f",
            enabled,
            universe_list,
            cycles,
            budget_usd,
        )
        return []

    # Delegate to Docker-based runner (handles Docker availability check internally)
    try:
        new_files = run_docker_factor_mining(
            budget_usd=budget_usd,
            cycles=cycles,
        )
        _LOGGER.info("RD-Agent produced %d new factor module(s)", len(new_files))
        return new_files
    except Exception as exc:  # noqa: BLE001 - the wrapper must never crash callers
        _LOGGER.exception("RD-Agent factor mining failed: %s", exc)
        return []
