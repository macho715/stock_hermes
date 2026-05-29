"""Docker-based RD-Agent factor mining runner.

This module wraps the ``rdagent fin_factor`` CLI inside a Docker container,
matching the design in plan.md §D2 (Docker subprocess pattern for Windows
compatibility).

Environment variables
--------------------
RDAGENT_ENABLED       Set ``true`` to activate Docker-based mining.
RDAGENT_DOCKER_IMAGE  Docker image (default: ``microsoft/rdagent:latest``).
RDAGENT_BUDGET_USD    Budget cap per run (default: ``10.0``).
RDAGENT_CYCLES        Number of cycles (default: ``2``).
RDAGENT_TIMEOUT_MIN   Timeout in minutes (default: ``30``, cap: ``60``).

Returns
-------
list[Path]
    Paths to newly-created factor ``.py`` modules under ``discovered/{session_id}/``.
    Empty list if Docker is unavailable or the run did not produce files.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import NamedTuple

from ...observability import get_logger

_LOGGER = get_logger("factors.rd_agent.docker_runner")


class _RunResult(NamedTuple):
    """Parsed output from a single RD-Agent Docker run."""

    cycles_complete: int
    new_factor_files: list[Path]
    budget_spent: float
    session_id: str


# ---------------------------------------------------------------------------
# Environment / defaults
# ---------------------------------------------------------------------------

def _is_rdagent_enabled() -> bool:
    """Re-read RDAGENT_ENABLED on every call so tests can patch it dynamically."""
    return os.getenv("RDAGENT_ENABLED", "false").lower() in ("1", "true", "yes")


_ENABLED: bool = _is_rdagent_enabled()
_DOCKER_IMAGE: str = os.getenv("RDAGENT_DOCKER_IMAGE", "microsoft/rdagent:latest")
_BUDGET_USD: float = float(os.getenv("RDAGENT_BUDGET_USD", "10.0"))
_CYCLES: int = int(os.getenv("RDAGENT_CYCLES", "2"))
_TIMEOUT_MIN: int = int(os.getenv("RDAGENT_TIMEOUT_MIN", "30"))
# Hard cap of 60 min per NFR-4
_TIMEOUT_MIN = min(_TIMEOUT_MIN, 60)

# Output location relative to this module
_REPO_ROOT = Path(__file__).resolve().parents[4]  # src/stock_rtx4060/factors/rd_agent → repo root
_DISCOVERED_DIR = _REPO_ROOT / "src" / "stock_rtx4060" / "factors" / "discovered"


# ---------------------------------------------------------------------------
# Docker availability check
# ---------------------------------------------------------------------------

def _docker_is_running() -> bool:
    """Return True if the Docker daemon is reachable."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Output parsing helpers
# ---------------------------------------------------------------------------

def _parse_budget_spent(raw: str) -> float:
    """Extract ``budget_spent`` from stdout/stderr.

    RD-Agent prints something like ``budget_spent=$3.42`` or ``budget_spent: 3.42``.
    """
    m = re.search(r"budget[_\s]spent[\s=:]*\$?([0-9.]+)", raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # Fallback: try to find any dollar amount followed by "spent"
    m2 = re.search(r"\$\s*([0-9.]+).*?spent", raw, re.IGNORECASE)
    if m2:
        return float(m2.group(1))
    return 0.0


def _parse_cycles_complete(raw: str) -> int:
    """Extract ``cycles_complete`` from stdout/stderr.

    RD-Agent prints ``cycles_complete=2`` or similar.
    """
    m = re.search(r"cycles[_\s]complete[_\s=:]*([0-9]+)", raw, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


def _discover_new_files(session_dir: Path, pre_existing: set[Path]) -> list[Path]:
    """Return sorted list of newly-created factor ``.py`` files in session_dir."""
    if not session_dir.is_dir():
        return []
    new = sorted(p for p in session_dir.glob("*.py") if p.resolve() not in pre_existing)
    return new


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_docker_factor_mining(
    *,
    budget_usd: float | None = None,
    cycles: int | None = None,
    docker_image: str | None = None,
    timeout_min: int | None = None,
) -> list[Path]:
    """Run RD-Agent inside a Docker container and return discovered factor paths.

    Graceful degradation
    --------------------
    If Docker is not installed / the daemon is not running, this function
    logs a warning and returns an empty list — it never raises an exception.

    Budget enforcement
    -------------------
    If the parsed ``budget_spent`` exceeds ``budget_usd``, a warning is logged
    but the run continues (the container may still produce useful output).

    Parameters
    ----------
    budget_usd : float, optional
        Override the env-var / default budget cap.
    cycles : int, optional
        Override the env-var / default cycle count.
    docker_image : str, optional
        Override the Docker image name.
    timeout_min : int, optional
        Override the timeout in minutes (capped at 60 internally).

    Returns
    -------
    list[Path]
        Paths to newly-created factor ``.py`` files under ``discovered/{session_id}/``.
    """
    if not _is_rdagent_enabled():
        _LOGGER.info("RDAGENT_ENABLED=false — skipping Docker factor mining")
        return []

    if not _docker_is_running():
        _LOGGER.warning(
            "Docker daemon is not reachable — skipping factor mining. "
            "Install Docker Desktop or ensure the daemon is running."
        )
        return []

    # Resolve parameters (env > arg > default)
    budget = budget_usd if budget_usd is not None else _BUDGET_USD
    n_cycles = cycles if cycles is not None else _CYCLES
    image = docker_image if docker_image is not None else _DOCKER_IMAGE
    timeout = min(timeout_min, 60) if timeout_min is not None else _TIMEOUT_MIN

    # Session ID for output directory
    session_id = f"rd_{time.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    output_dir = _DISCOVERED_DIR / session_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Snapshot existing files to diff against
    pre_existing = {p.resolve() for p in output_dir.glob("*.py")}

    # Build docker command (plan.md §D2)
    config_path = _REPO_ROOT / "src" / "stock_rtx4060" / "factors" / "rd_agent" / "config" / "stock1901.yaml"
    cmd = [
        "docker", "run", "--rm",
        "--user", "root",  # avoid permission issues on Windows-mounted dirs
        "-v", f"{_REPO_ROOT}:{_REPO_ROOT}",
        "-w", str(_REPO_ROOT),
        image,
        "rdagent", "fin_factor",
        "--config", str(config_path),
        "--budget-usd", str(budget),
        "--cycles", str(n_cycles),
    ]

    _LOGGER.info(
        "[RD-Agent] starting Docker run — image=%s budget=%.2f cycles=%d timeout=%dm session=%s",
        image, budget, n_cycles, timeout, session_id,
    )

    full_output = ""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None

        # Stream output with timeout
        start = time.monotonic()
        deadline = start + timeout * 60

        for line in proc.stdout:
            full_output += line
            # Keep this compatible with both stdlib logging and loguru.
            _LOGGER.debug(f"[rdagent] {line.rstrip()}")

            if time.monotonic() > deadline:
                proc.kill()
                proc.wait()
                _LOGGER.warning(
                    "[RD-Agent] timeout exceeded (%d min) — killing container", timeout
                )
                return []

        exit_code = proc.wait()

    except OSError as exc:
        _LOGGER.error("[RD-Agent] failed to start Docker: %s", exc)
        return []

    # Parse results from full_output
    budget_spent = _parse_budget_spent(full_output)
    cycles_complete = _parse_cycles_complete(full_output)

    if budget_spent > budget:
        _LOGGER.warning(
            "[RD-Agent] budget exceeded: spent $%.2f > limit $%.2f — continuing",
            budget_spent, budget,
        )

    if exit_code != 0:
        _LOGGER.warning(
            "[RD-Agent] container exited with code %d — treating as partial run. "
            "Output snippet: %s",
            exit_code,
            full_output[:500],
        )

    # Discover new files
    new_files = _discover_new_files(output_dir, pre_existing)

    _LOGGER.info(
        "[RD-Agent] completed — session=%s cycles=%d budget_spent=%.2f new_files=%d",
        session_id, cycles_complete, budget_spent, len(new_files),
    )

    return new_files


if __name__ == "__main__":
    # Simple smoke test
    result = run_docker_factor_mining()
    print(f"Discovered factors: {result}")
