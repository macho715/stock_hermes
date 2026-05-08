"""Wrapper around Microsoft RD-Agent for automated factor mining.

If ``rdagent`` is not installed in the active environment, ``run_factor_mining``
returns an empty list and emits a single warning log line so CI can carry on
without the heavy dependency.  When ``rdagent`` *is* available, we hand off to
its ``factor_loop`` interface and collect the produced Python source files
from ``output_dir``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ...observability import get_logger

_LOGGER = get_logger("factors.rd_agent.runner")


def _try_import_rdagent() -> object | None:
    try:
        import rdagent  # type: ignore[import-not-found]

        return rdagent
    except Exception:  # noqa: BLE001 - surface optional dep absence gracefully
        return None


def run_factor_mining(
    universe: Iterable[str],
    cycles: int,
    budget_usd: float,
    output_dir: Path = Path("src/stock_rtx4060/factors/discovered"),
) -> list[Path]:
    """Run RD-Agent factor mining and return paths of newly produced factor modules.

    Parameters
    ----------
    universe:
        Tickers RD-Agent should mine factors for.  Forwarded to its config.
    cycles:
        Number of evolution cycles to run (each cycle == hypothesis -> factor ->
        backtest -> feedback loop in RD-Agent terminology).
    budget_usd:
        Hard cap on LLM spend — RD-Agent honours this via its accountant.
    output_dir:
        Directory into which the wrapper expects RD-Agent to drop generated
        ``.py`` factor modules.  Created if missing.

    Returns
    -------
    list[Path]
        Newly created files (compared against the directory snapshot taken
        before the run).  Empty list if RD-Agent is not installed.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    universe_list = list(universe)

    rdagent = _try_import_rdagent()
    if rdagent is None:
        _LOGGER.warning(
            "rdagent not installed — skipping factor mining "
            "(install with `pip install rdagent` to enable). "
            "universe=%s cycles=%d budget=%.2f",
            universe_list,
            cycles,
            budget_usd,
        )
        return []

    pre_existing = {p.resolve() for p in output_dir.glob("*.py")}
    try:
        # NOTE: RD-Agent's public API has evolved; we use the documented
        # factor-loop entrypoint.  When it changes, only this block needs
        # to be updated — the rest of our pipeline reads files off disk.
        factor_loop = getattr(rdagent, "factor_loop", None)
        if factor_loop is None:
            # TODO: fall back to the CLI driver `python -m rdagent.app.qlib_rd_loop.factor`
            _LOGGER.warning("rdagent.factor_loop missing in installed version; consider updating rdagent")
            return []
        factor_loop(
            universe=universe_list,
            cycles=int(cycles),
            budget_usd=float(budget_usd),
            output_dir=str(output_dir),
        )
    except Exception as exc:  # noqa: BLE001 - the wrapper must never crash callers
        _LOGGER.exception("RD-Agent factor mining failed: %s", exc)
        return []

    after = {p.resolve() for p in output_dir.glob("*.py")}
    new_files = sorted(after - pre_existing)
    _LOGGER.info("RD-Agent produced %d new factor module(s)", len(new_files))
    return new_files
