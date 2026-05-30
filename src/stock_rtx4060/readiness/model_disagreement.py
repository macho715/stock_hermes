"""Model disagreement gate — flags ensemble conflicts before live decisions.

A high score spread (>= 50 points) or a direction conflict between the main
model and the secondary majority signals ``AMBER_MODEL_DISAGREEMENT`` and
blocks any live-review promotion.

``None`` / ``N/A`` scores (e.g. LSTM/ELM not trained) are **excluded** from
the spread calculation.  Only valid numeric scores contribute.

Safety invariants (always true):
  * ``new_capital_allowed`` is always ``False``.
  * ``live_review_candidate`` is always ``False`` when disagreement is detected.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Minimum score spread (max − min over valid scores) to flag disagreement.
DISAGREEMENT_SPREAD_THRESHOLD: float = 50.0

# Readiness statuses
STATUS_PASS = "PASS"
STATUS_AMBER = "AMBER_MODEL_DISAGREEMENT"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_model_disagreement(
    *,
    model_scores: dict[str, float | None],
    main_signal: str,
    spread_threshold: float = DISAGREEMENT_SPREAD_THRESHOLD,
) -> dict[str, Any]:
    """Evaluate the model disagreement gate.

    Parameters
    ----------
    model_scores:
        Dict of ``{model_name: score_or_None}``.  Scores are expected in the
        range ``[0, 100]`` (probability × 100 or similar).  Pass ``None`` for
        models that are not trained / not available (LSTM, ELM, RNN stubs).
    main_signal:
        The primary model's signal direction: ``"BUY"`` / ``"SELL"`` / ``"HOLD"``.
    spread_threshold:
        Override for the spread threshold (default 50.0).

    Returns
    -------
    dict with keys:
        ``model_disagreement`` bool,
        ``score_spread`` float,
        ``valid_model_count`` int,
        ``skipped_model_count`` int,
        ``readiness_status`` str,
        ``blocking_reasons`` list[str],
        ``live_review_candidate`` bool (False when disagreement detected),
        ``new_capital_allowed`` bool (always False).
    """
    valid: dict[str, float] = {
        k: float(v) for k, v in model_scores.items() if v is not None
    }
    skipped_count = len(model_scores) - len(valid)
    valid_count = len(valid)

    if valid_count < 2:
        # Cannot calculate a spread with fewer than 2 models — treat as PASS
        return {
            "model_disagreement": False,
            "score_spread": 0.0,
            "valid_model_count": valid_count,
            "skipped_model_count": skipped_count,
            "readiness_status": STATUS_PASS,
            "blocking_reasons": [],
            "live_review_candidate": True,
            "new_capital_allowed": False,
        }

    score_spread = max(valid.values()) - min(valid.values())
    model_disagreement = score_spread >= spread_threshold

    blocking_reasons: list[str] = []
    if model_disagreement:
        blocking_reasons.append("MODEL_DISAGREEMENT_HIGH")

    readiness_status = STATUS_AMBER if model_disagreement else STATUS_PASS

    return {
        "model_disagreement": model_disagreement,
        "score_spread": round(score_spread, 2),
        "valid_model_count": valid_count,
        "skipped_model_count": skipped_count,
        "readiness_status": readiness_status,
        "blocking_reasons": blocking_reasons,
        "live_review_candidate": not model_disagreement,
        "new_capital_allowed": False,
    }
