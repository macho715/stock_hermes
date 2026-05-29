"""Final bar lock contract — authoritative EOD final-bar metadata for inference gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Source priority tiers
# ---------------------------------------------------------------------------

# Tier 1 — Authoritative: KRX / broker confirmation
AUTHORITATIVE_SOURCES: set[str] = {"KRX_FINAL", "BROKER_FINAL", "KRX_OR_BROKER_FINAL"}

# Tier 2 — Trusted but not authoritative
TRUSTED_EOD_SOURCES: set[str] = {"TRUSTED_EOD_PROVIDER"}

# Tier 3 — Public web (no lock authority)
PUBLIC_WEB_SOURCES: set[str] = {"PUBLIC_WEB"}

# Tier 4 — Cache (no lock authority)
CACHE_SOURCES: set[str] = {"PYKRX:CACHE", "CACHE"}


# ---------------------------------------------------------------------------
# Blocking reasons
# ---------------------------------------------------------------------------

BAR_TYPE_NOT_EOD_FINAL = "BAR_TYPE_NOT_EOD_FINAL"
EOD_FINAL_BAR_NOT_LOCKED = "EOD_FINAL_BAR_NOT_LOCKED"
SOURCE_EVIDENCE_LOCK_MISSING = "SOURCE_EVIDENCE_LOCK_MISSING"
SOURCE_PRIORITY_TOO_LOW = "SOURCE_PRIORITY_TOO_LOW"
EOD_CONFIRMED_FALSE = "EOD_CONFIRMED_FALSE"


# ---------------------------------------------------------------------------
# Readiness statuses
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_AMBER_DATA_LAG = "AMBER_DATA_LAG_EVENT_CONFLICT"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def provider_final_bar_metadata(
    *,
    source: str,
    bar_type: str,
    eod_confirmed: bool,
    source_evidence_lock: bool,
    after_market_close: bool,
    close_diff_pct: float | None = None,
    volume_lag_ratio: float | None = None,
    cache_close: float | None = None,
    cache_volume: float | None = None,
    final_close: float | None = None,
    final_volume: float | None = None,
) -> dict[str, Any]:
    """
    Build the ``final_bar_lock`` metadata dict for a provider result.

    Parameters
    ----------
    source : str
        One of the named sources (e.g. ``"KRX_FINAL"``, ``"PUBLIC_WEB"``).
    bar_type : str
        ``"EOD_FINAL"`` if the bar is confirmed final; ``"EOD_FINAL_UNAVAILABLE"``
        if it could not be obtained; ``"CACHE"`` otherwise.
    eod_confirmed : bool
        True when an authoritative source has confirmed the EOD bar.
    source_evidence_lock : bool
        True when the provider returns traceable evidence (e.g. API timestamp,
        exchange receipt) that the bar is final.
    after_market_close : bool
        Whether the query was made after market close.

    Returns
    -------
    dict
        A flat metadata dict **including** the nested ``final_bar_lock`` key.
        Keys:

        - ``source``, ``source_priority``, ``bar_type``, ``eod_confirmed``
        - ``source_evidence_lock``, ``after_market_close``
        - ``final_bar_lock``: contains ``inference_allowed``,
          ``readiness_status``, ``blocking_reasons``
        - ``cache_vs_final``: present when both cache and final values are
          available (diff > 0)
    """
    source_priority = _source_priority(source)

    blocking_reasons = _blocking_reasons(
        source_priority=source_priority,
        bar_type=bar_type,
        eod_confirmed=eod_confirmed,
        source_evidence_lock=source_evidence_lock,
    )

    inference_allowed = _infer_allowed(
        source_priority=source_priority,
        bar_type=bar_type,
        eod_confirmed=eod_confirmed,
        source_evidence_lock=source_evidence_lock,
    )

    if blocking_reasons:
        readiness_status = STATUS_AMBER_DATA_LAG
    else:
        readiness_status = STATUS_PASS

    result: dict[str, Any] = {
        "source": source,
        "source_priority": source_priority,
        "bar_type": bar_type,
        "eod_confirmed": eod_confirmed,
        "source_evidence_lock": source_evidence_lock,
        "after_market_close": after_market_close,
        "final_bar_lock": {
            "inference_allowed": inference_allowed,
            "readiness_status": readiness_status,
            "blocking_reasons": blocking_reasons,
        },
        # Safety: never accidentally emit broker execution permission
        "broker_order_execution": False,
    }

    # Cache-vs-final diff when both are available
    diff_result = compare_cache_vs_final(
        cache_close=cache_close,
        final_close=final_close,
        cache_volume=cache_volume,
        final_volume=final_volume,
    )
    if diff_result:
        result["cache_vs_final"] = diff_result

    return result


def compare_cache_vs_final(
    *,
    cache_close: float | None = None,
    final_close: float | None = None,
    cache_volume: float | None = None,
    final_volume: float | None = None,
) -> dict[str, Any] | None:
    """
    Compute cache-vs-final diff and emit AMBER_DATA_LAG when thresholds breached.

    Returns None when diff is negligible or inputs are missing.

    Thresholds
    ---------
    close_diff_pct : > 1.0 %  → AMBER
    volume_lag_ratio : > 2.0× → AMBER
    """
    if cache_close is None or final_close is None:
        return None
    if cache_volume is None or final_volume is None:
        return None

    close_diff_pct = abs(final_close - cache_close) / cache_close * 100.0
    volume_lag_ratio = final_volume / cache_volume if cache_volume > 0 else 0.0

    status = "OK"
    amber_reasons: list[str] = []

    if close_diff_pct > 1.0:
        status = "AMBER_DATA_LAG"
        amber_reasons.append("CLOSE_DIFF_PCT_ABOVE_1_PCT")
    if volume_lag_ratio > 2.0:
        status = "AMBER_DATA_LAG"
        amber_reasons.append("VOLUME_LAG_RATIO_ABOVE_2X")

    if status == "OK":
        return None

    return {
        "status": status,
        "close_diff_pct": round(close_diff_pct, 4),
        "volume_lag_ratio": round(volume_lag_ratio, 4),
        "cache_close": cache_close,
        "final_close": final_close,
        "cache_volume": cache_volume,
        "final_volume": final_volume,
        "amber_reasons": amber_reasons,
    }


def _source_priority(source: str) -> int:
    """Return integer priority; lower is more authoritative."""
    if source in AUTHORITATIVE_SOURCES:
        return 1
    if source in TRUSTED_EOD_SOURCES:
        return 2
    if source in PUBLIC_WEB_SOURCES:
        return 3
    if source in CACHE_SOURCES:
        return 4
    return 5  # unknown


def _blocking_reasons(
    source_priority: int,
    bar_type: str,
    eod_confirmed: bool,
    source_evidence_lock: bool,
) -> list[str]:
    reasons: list[str] = []
    if bar_type != "EOD_FINAL":
        reasons.append(BAR_TYPE_NOT_EOD_FINAL)
    if source_priority > 1:
        reasons.append(SOURCE_PRIORITY_TOO_LOW)
    if not eod_confirmed:
        reasons.append(EOD_CONFIRMED_FALSE)
    if not source_evidence_lock:
        reasons.append(SOURCE_EVIDENCE_LOCK_MISSING)
    return reasons


def _infer_allowed(
    source_priority: int,
    bar_type: str,
    eod_confirmed: bool,
    source_evidence_lock: bool,
) -> bool:
    """Only Tier-1/2 with confirmed EOD final bar may allow inference."""
    if source_priority > 1:
        return False
    if bar_type != "EOD_FINAL":
        return False
    if not eod_confirmed:
        return False
    if not source_evidence_lock:
        return False
    return True