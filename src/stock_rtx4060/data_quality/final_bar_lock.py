"""EOD final bar source-lock checks for post-close inference."""

from __future__ import annotations

from typing import Any

SOURCE_PRIORITY = {
    "KRX_FINAL": 1,
    "BROKER_FINAL": 1,
    "KRX_OR_BROKER_FINAL": 1,
    "TRUSTED_EOD_PROVIDER": 2,
    "PUBLIC_WEB": 3,
    "PYKRX:CACHE": 4,
    "PYKRX_CACHE": 4,
    "CACHE": 4,
}

READINESS_BLOCKED = "AMBER_DATA_LAG_EVENT_CONFLICT"


def source_priority_for(source: Any) -> int:
    text = str(source or "").strip().upper().replace("-", "_").replace(" ", "_")
    return SOURCE_PRIORITY.get(text, 99)


def evaluate_final_bar_lock(bar: dict[str, Any]) -> dict[str, Any]:
    source = str(bar.get("source") or "").strip()
    source_priority = int(bar.get("source_priority") or source_priority_for(source))
    bar_type = str(bar.get("bar_type") or "").strip().upper()
    eod_confirmed = bar.get("eod_confirmed") is True
    source_evidence_lock = bar.get("source_evidence_lock") is True

    reasons: list[str] = []
    if bar_type != "EOD_FINAL":
        reasons.append("BAR_TYPE_NOT_EOD_FINAL")
    if not eod_confirmed:
        reasons.append("EOD_FINAL_BAR_NOT_LOCKED")
    if not source_evidence_lock:
        reasons.append("SOURCE_EVIDENCE_LOCK_MISSING")
    if source_priority > 2:
        reasons.append("SOURCE_PRIORITY_TOO_LOW")

    inference_allowed = not reasons
    return {
        "inference_allowed": inference_allowed,
        "readiness_status": "PASS" if inference_allowed else READINESS_BLOCKED,
        "blocking_reasons": reasons,
        "bar_type": bar_type,
        "source": source,
        "source_priority": source_priority,
        "eod_confirmed": eod_confirmed,
        "source_evidence_lock": source_evidence_lock,
    }


def compare_cache_vs_final(
    *,
    cache_close: float | int | None,
    final_close: float | int | None,
    cache_volume: float | int | None,
    final_volume: float | int | None,
) -> dict[str, Any]:
    cache_close_value = _to_float(cache_close)
    final_close_value = _to_float(final_close)
    cache_volume_value = _to_float(cache_volume)
    final_volume_value = _to_float(final_volume)

    close_diff_pct = 0.0
    if cache_close_value and final_close_value:
        close_diff_pct = abs(final_close_value - cache_close_value) / cache_close_value * 100.0

    volume_lag_ratio = 0.0
    if cache_volume_value and final_volume_value:
        volume_lag_ratio = final_volume_value / cache_volume_value

    reasons: list[str] = []
    if close_diff_pct > 1.0:
        reasons.append("CACHE_CLOSE_DIFF_GT_1PCT")
    if volume_lag_ratio > 2.0:
        reasons.append("CACHE_VOLUME_LAG_GT_2X")

    return {
        "status": "AMBER_DATA_LAG" if reasons else "PASS",
        "inference_allowed": not reasons,
        "close_diff_pct": round(close_diff_pct, 4),
        "volume_lag_ratio": round(volume_lag_ratio, 4),
        "blocking_reasons": reasons,
    }


def provider_final_bar_metadata(
    *,
    source: str,
    bar_type: str,
    eod_confirmed: bool,
    source_evidence_lock: bool,
    after_market_close: bool = False,
) -> dict[str, Any]:
    source_priority = source_priority_for(source)
    lock = evaluate_final_bar_lock(
        {
            "source": source,
            "source_priority": source_priority,
            "bar_type": bar_type,
            "eod_confirmed": eod_confirmed,
            "source_evidence_lock": source_evidence_lock,
            "after_market_close": after_market_close,
        }
    )
    return {
        "bar_type": str(bar_type or "").strip().upper(),
        "source_priority": source_priority,
        "eod_confirmed": eod_confirmed,
        "source_evidence_lock": source_evidence_lock,
        "after_market_close": after_market_close,
        "final_bar_lock": lock,
    }


def _to_float(value: float | int | None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
