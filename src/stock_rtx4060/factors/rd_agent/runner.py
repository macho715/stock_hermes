"""Wrapper around Microsoft RD-Agent for automated factor mining.

Supports two execution modes:
- ``RDAGENT_MODE=native``  → calls ``rdagent fin_factor`` CLI directly on Windows
- ``RDAGENT_MODE=docker``  → delegates to docker_runner.run_docker_factor_mining()

When RDAGENT_ENABLED=false or the selected mode is unavailable, this module
returns an empty list and emits a warning — CI can carry on without the heavy
dependency."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from datetime import date as Date
from pathlib import Path
from typing import Any

from ...observability import get_logger
from .docker_runner import run_docker_factor_mining

_LOGGER = get_logger("factors.rd_agent.runner")


def run_factor_mining(
    universe: Iterable[str],
    cycles: int,
    budget_usd: float,
    output_dir: Path = Path("src/stock_rtx4060/factors/discovered"),
    *,
    run_date: str | None = None,
    prepare_qlib: bool = True,
    synthetic: bool = False,
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

    universe_list = list(universe)
    if prepare_qlib:
        _prepare_qlib_data(universe_list, run_date=run_date, synthetic=synthetic)

    if os.environ.get("RDAGENT_DRY_RUN", "false").lower() in ("1", "true", "yes"):
        _LOGGER.info(
            "RDAGENT_DRY_RUN=true — completed RD-Agent dry-run path without Docker. "
            "universe=%s cycles=%d budget=%.2f",
            universe_list,
            cycles,
            budget_usd,
        )
        return []

    # Determine execution mode: native CLI > WSL2 fallback > Docker
    mode = os.environ.get("RDAGENT_MODE", "").lower()
    if not mode or mode == "auto":
        # Auto-detect: try native rdagent CLI first, fall back to Docker
        if _native_rdagent_available():
            mode = "native"
        else:
            mode = "docker"

    if mode == "native":
        return _run_native_rdagent(
            budget_usd=budget_usd,
            cycles=cycles,
            universe=universe_list,
        )

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


def _native_rdagent_available() -> bool:
    """Return True if the ``rdagent`` CLI is on PATH and responds to --version."""
    try:
        result = subprocess.run(
            ["rdagent", "--version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _run_native_rdagent(
    budget_usd: float,
    cycles: int,
    universe: list[str],
) -> list[Path]:
    """Run rdagent fin_factor via native Windows CLI and return discovered factor paths.

    Parameters
    ----------
    budget_usd : float
        Budget cap per LLM call (rdagent honours this via its accountant).
    cycles : int
        Number of evolution cycles.
    universe : list[str]
        Tickers to mine factors for.

    Returns
    -------
    list[Path]
        Paths to newly created factor ``.py`` modules under ``discovered/{session_id}/``.
        Empty list on any failure.
    """
    _LOGGER.info(
            "[RD-Agent/NATIVE] starting Windows CLI — budget=%.2f cycles=%d universe=%s",
            budget_usd, cycles, universe,
        )

    try:
        proc = subprocess.Popen(
            [
                "rdagent", "fin_factor",
                "--budget-usd", str(budget_usd),
                "--cycles", str(cycles),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None

        full_output = ""
        for line in proc.stdout:
            full_output += line
            _LOGGER.debug(f"[rdagent] {line.rstrip()}")

        exit_code = proc.wait()

        # Parse result summary
        from .docker_runner import _parse_budget_spent, _parse_cycles_complete
        budget_spent = _parse_budget_spent(full_output)
        cycles_complete = _parse_cycles_complete(full_output)

        if exit_code != 0:
            _LOGGER.warning(
                "[RD-Agent/NATIVE] exited with code %d — treating as partial run. "
                "Output snippet: %s",
                exit_code, full_output[:500],
            )

        _LOGGER.info(
            "[RD-Agent/NATIVE] completed — cycles=%d budget_spent=%.2f",
            cycles_complete, budget_spent,
        )

        # TODO: discover new factor .py files — placeholder for now
        return []

    except OSError as exc:
        _LOGGER.error("[RD-Agent/NATIVE] failed to start rdagent: %s", exc)
        return []


def _prepare_qlib_data(
    universe: list[str],
    *,
    run_date: str | None = None,
    synthetic: bool = False,
) -> dict[str, Any]:
    """Prepare Qlib CSV/bin data for RD-Agent, returning a JSON-friendly summary."""

    actual_date = run_date or str(Date.today())
    try:
        if synthetic:
            from .qlib_exporter import convert_csv_to_qlib_bin, export_synthetic_ohlcv_to_qlib_csv

            rows = export_synthetic_ohlcv_to_qlib_csv(universe, actual_date)
            bin_converted = convert_csv_to_qlib_bin() if rows else False
        else:
            from .qlib_exporter import export_ohlcv_to_qlib

            rows = export_ohlcv_to_qlib(universe, actual_date, convert_bin=True)
            bin_converted = bool(rows)
        _LOGGER.info("Qlib export prepared %d ticker(s) for RD-Agent", len(rows))
        return {"run_date": actual_date, "rows": rows, "skipped": False, "synthetic": synthetic, "bin_converted": bin_converted}
    except Exception as exc:  # noqa: BLE001 - keep mining wrapper fail-soft
        _LOGGER.warning("Qlib export preparation failed; continuing RD-Agent flow: %s", exc)
        return {"run_date": actual_date, "rows": {}, "skipped": True, "error": str(exc)}
