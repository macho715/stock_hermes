"""Registry hook for RD-Agent discovered factors.

This module bridges the RD-Agent discovery pipeline and the :class:`FactorRegistry`:

1. :func:`validate_and_stage` loads factor classes from a completed discovery
   session, runs them through the validator, and stages those that pass in an
   internal pending table.

2. :func:`approve_and_register` is called by the ops approval step
   (``factor-approve`` CLI).  It moves one or more staged factors into the
   ``FactorRegistry`` and optionally logs metadata to MLflow.

The ``RDAGENT_APPROVAL_REQUIRED`` environment variable controls the gate:

* ``RDAGENT_APPROVAL_REQUIRED=true``  — :func:`approve_and_register` must be
  called before a factor can appear in the registry.  If the env var is set but
  :func:`approve_and_register` has not been called, the factor is invisible to
  ``factor_compute_task`` (D5 controls gate).

* ``RDAGENT_APPROVAL_REQUIRED=false`` — factors are registered immediately
  after validation (auto-approval).  This is only appropriate for development.

Example
-------
::

    # In the daily flow after RD-Agent finishes a session:
    from stock_rtx4060.factors.rd_agent.registry_hook import validate_and_stage

    result = validate_and_stage(
        session_id = "sess_20260529_a",
        panel       = ohlcv_panel,
        fwd_returns = series_of_forward_returns,
    )
    print(result.passed_names)   # factors cleared validation

    # Ops reviews and approves:
    from stock_rtx4060.factors.rd_agent.registry_hook import approve_and_register
    approve_and_register("sess_20260529_a", factor_names=["rd_mom_vol", "rd_size反转"])
"""

from __future__ import annotations

import os
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from .loader import load_discovered_factors
from .provenance import log_factor_approved
from .validator import ValidationResult, validate_discovered_factor

# ---------------------------------------------------------------------------
# Staging area — holds validated (but not yet approved) factor classes.
# Keyed by session_id so multiple sessions can coexist.
# ---------------------------------------------------------------------------
_STAGED: dict[str, dict[str, tuple[type, ValidationResult]]] = {}

_APPROVAL_REQUIRED = os.getenv("RDAGENT_APPROVAL_REQUIRED", "true").lower() in (
    "true",
    "1",
    "yes",
)


def validate_and_stage(
    session_id: str,
    panel: pd.DataFrame,
    fwd_returns: pd.Series,
    *,
    min_abs_ic: float = 0.03,
    min_ir: float = 0.3,
    max_corr_with_existing: float = 0.7,
    min_half_life_days: int = 3,
) -> dict[str, ValidationResult]:
    """Load discovered factors, validate them, and stage the passing ones.

    Factors that clear every gate are stored in an internal staging table
    keyed by ``session_id``.  They remain invisible to the rest of the system
    until :func:`approve_and_register` is called (when
    ``RDAGENT_APPROVAL_REQUIRED=true``).

    Parameters
    ----------
    session_id:
        RD-Agent session identifier.  Factor Python files are expected under
        ``discovered/{session_id}/``.
    panel:
        OHLCV panel used to drive validation.
    fwd_returns:
        Forward return series aligned to the panel index; used to compute IC
        and IR during validation.
    min_abs_ic, min_ir, max_corr_with_existing, min_half_life_days:
        Validation thresholds.  See :func:`validate_discovered_factor`.

    Returns
    -------
    dict[str, ValidationResult]
        Mapping from factor name to its :class:`ValidationResult`.  All
        discovered factors are present in the dict; the ``passed`` field
        indicates whether they cleared the gates.

    Raises
    ------
    RuntimeError
        When ``RDAGENT_APPROVAL_REQUIRED=true`` and no factors passed
        validation (there is nothing to stage).
    """
    factor_classes = load_discovered_factors(session_id)
    if not factor_classes:
        return {}

    results: dict[str, ValidationResult] = {}
    passed: dict[str, tuple[type, ValidationResult]] = {}

    for name, factor_cls in factor_classes:
        try:
            factor_instance = factor_cls()
        except Exception:  # pragma: no cover — skip broken constructors
            results[name] = ValidationResult(passed=False, reasons=["constructor raised"])
            continue

        vr = validate_discovered_factor(
            factor_instance,
            panel,
            fwd_returns,
            min_abs_ic=min_abs_ic,
            min_ir=min_ir,
            max_corr_with_existing=max_corr_with_existing,
            min_half_life_days=min_half_life_days,
        )
        results[name] = vr
        if vr.passed:
            passed[name] = (factor_cls, vr)

    if _APPROVAL_REQUIRED and not passed:
        raise RuntimeError(
            f"[registry_hook] RDAGENT_APPROVAL_REQUIRED=true but no factors "
            f"passed validation in session {session_id!r}; refusing to stage."
        )

    if passed:
        _STAGED.setdefault(session_id, {})[session_id]  # ensure session key exists
        # Merge into existing session entry (supports calling validate_and_stage
        # multiple times for the same session — e.g. re-validation after edits).
        _STAGED[session_id].update(passed)

    return results


def approve_and_register(
    session_id: str,
    factor_names: list[str],
    *,
    approved_by: str = "operator",
    budget_spent_usd: float = 0.0,
    cycles_run: int = 0,
    budget_limit_usd: float = 0.0,
) -> list[str]:
    """Register one or more staged factors after ops approval.

    When ``RDAGENT_APPROVAL_REQUIRED=true`` (the default), this function must
    be called for a factor to become visible in the :class:`FactorRegistry`.
    Factors not named in ``factor_names`` remain in staging and can be approved
    in a later call.

    Each registered factor is also logged to MLflow (if available) as a
    parameter entry under run ``rd_agent/{session_id}``.

    Parameters
    ----------
    session_id:
        Session that produced the factors.
    factor_names:
        Subset of staged factor names to approve and register.  Factors that
        were not staged (either because they failed validation or the session
        has not been validated) are silently skipped.
    approved_by:
        Identifier of the approver (e.g. ``"operator"`` or a username).
    budget_spent_usd, cycles_run, budget_limit_usd:
        Provenance values passed through to the audit log entry.
    approved_by

    Returns
    -------
    list[str]
        Names of factors that were successfully registered.
    """
    if _APPROVAL_REQUIRED:
        pass  # gate is open — proceed
    else:
        # Auto-approval mode: factors were already registered inside
        # validate_and_stage; nothing to do.
        return []

    staged = _STAGED.get(session_id, {})

    from ..factor_zoo import FactorRegistry

    registry = FactorRegistry()
    registered: list[str] = []
    today = date.today().isoformat()

    for name in factor_names:
        entry = staged.get(name)
        if entry is None:
            # Not staged — skip silently (could have been filtered out or
            # never loaded).
            continue

        factor_cls, vr = entry

        # Instantiate and register with replace=False (existing entries are
        # preserved; the ops team must explicitly request replacement).
        try:
            factor_instance = factor_cls()
        except Exception:  # pragma: no cover — constructor already succeeded once
            continue

        # Attach RD-Agent provenance fields on the meta so the registry
        # carries the full lineage.
        meta = factor_instance.meta
        object.__setattr__(meta, "source", "rd_agent")
        object.__setattr__(meta, "discovery_session_id", session_id)
        object.__setattr__(meta, "discovery_date", today)
        object.__setattr__(meta, "budget_usd", budget_spent_usd)
        object.__setattr__(meta, "ic_at_discovery", vr.ic)

        registry.register(factor_instance, replace=False)
        registered.append(name)

        _log_to_mlflow(session_id, name, vr.ic, budget_spent_usd, today)

    # Prune successfully registered factors from staging.
    for name in registered:
        staged.pop(name, None)

    # Audit log — one event per approval call.
    if registered:
        log_factor_approved(
            session_id=session_id,
            cycles_run=cycles_run,
            budget_spent_usd=budget_spent_usd,
            budget_limit_usd=budget_limit_usd,
            new_factor_files=registered,
            approved_by=approved_by,
        )

    return registered


def _log_to_mlflow(
    session_id: str,
    factor_name: str,
    ic: float,
    budget_usd: float,
    discovery_date: str,
) -> None:
    """Log factor registration metadata to MLflow if available."""
    try:
        import mlflow
    except ImportError:
        return

    run_name = f"rd_agent/{session_id}"
    with mlflow.start_run(run_name=run_name, log_system_info=False):
        mlflow.log_params({
            f"factor.{factor_name}.source": "rd_agent",
            f"factor.{factor_name}.session_id": session_id,
            f"factor.{factor_name}.discovery_date": discovery_date,
            f"factor.{factor_name}.budget_usd": budget_usd,
            f"factor.{factor_name}.ic_at_discovery": ic,
        })
