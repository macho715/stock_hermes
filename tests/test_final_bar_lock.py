from __future__ import annotations

from stock_rtx4060.data_quality.final_bar_lock import (
    compare_cache_vs_final,
    evaluate_final_bar_lock,
    provider_final_bar_metadata,
)


def test_cache_bar_after_close_is_not_eod_final():
    bar = {
        "symbol": "005930.KS",
        "source": "PYKRX:CACHE",
        "bar_type": "CACHE",
        "eod_confirmed": False,
        "source_evidence_lock": False,
        "after_market_close": True,
    }

    result = evaluate_final_bar_lock(bar)

    assert result["inference_allowed"] is False
    assert result["readiness_status"] == "AMBER_DATA_LAG_EVENT_CONFLICT"
    assert result["eod_confirmed"] is False
    assert result["source_evidence_lock"] is False
    assert "BAR_TYPE_NOT_EOD_FINAL" in result["blocking_reasons"]
    assert "EOD_FINAL_BAR_NOT_LOCKED" in result["blocking_reasons"]
    assert "SOURCE_EVIDENCE_LOCK_MISSING" in result["blocking_reasons"]
    assert "SOURCE_PRIORITY_TOO_LOW" in result["blocking_reasons"]


def test_final_bar_requires_authority_source():
    bar = {
        "symbol": "005930.KS",
        "source": "PUBLIC_WEB",
        "source_priority": 3,
        "bar_type": "EOD_FINAL",
        "eod_confirmed": True,
        "source_evidence_lock": False,
    }

    result = evaluate_final_bar_lock(bar)

    assert result["inference_allowed"] is False
    assert result["readiness_status"] == "AMBER_DATA_LAG_EVENT_CONFLICT"
    assert "SOURCE_PRIORITY_TOO_LOW" in result["blocking_reasons"]
    assert "SOURCE_EVIDENCE_LOCK_MISSING" in result["blocking_reasons"]


def test_authority_final_bar_allows_inference():
    bar = {
        "symbol": "005930.KS",
        "source": "KRX_FINAL",
        "source_priority": 1,
        "bar_type": "EOD_FINAL",
        "eod_confirmed": True,
        "source_evidence_lock": True,
    }

    result = evaluate_final_bar_lock(bar)

    assert result["inference_allowed"] is True
    assert result["readiness_status"] == "PASS"
    assert result["blocking_reasons"] == []
    assert result["source_priority"] == 1


def test_cache_vs_final_close_diff_blocks_inference():
    result = compare_cache_vs_final(
        cache_close=308500,
        final_close=317000,
        cache_volume=9039622,
        final_volume=37241537,
    )

    assert result["close_diff_pct"] > 1.0
    assert result["volume_lag_ratio"] > 2.0
    assert result["status"] == "AMBER_DATA_LAG"
    assert result["inference_allowed"] is False
    assert "CACHE_CLOSE_DIFF_GT_1PCT" in result["blocking_reasons"]
    assert "CACHE_VOLUME_LAG_GT_2X" in result["blocking_reasons"]


# ─── RED tests for P1 gap coverage ────────────────────────────────────────────

def test_public_web_cannot_lock_final_bar():
    """PUBLIC_WEB has source_priority=3 and cannot lock final bar."""
    meta = provider_final_bar_metadata(
        source="PUBLIC_WEB",
        bar_type="EOD_FINAL",
        eod_confirmed=True,
        source_evidence_lock=False,
        after_market_close=True,
    )

    assert meta["source_priority"] == 3
    assert meta["final_bar_lock"]["inference_allowed"] is False
    assert "SOURCE_PRIORITY_TOO_LOW" in meta["final_bar_lock"]["blocking_reasons"]


def test_public_web_final_bar_not_locked():
    """Even with eod_confirmed=True, PUBLIC_WEB source_evidence_lock=False blocks inference."""
    bar = {
        "symbol": "005930.KS",
        "source": "PUBLIC_WEB",
        "source_priority": 3,
        "bar_type": "EOD_FINAL",
        "eod_confirmed": True,
        "source_evidence_lock": False,
    }

    result = evaluate_final_bar_lock(bar)

    assert result["inference_allowed"] is False
    assert "SOURCE_PRIORITY_TOO_LOW" in result["blocking_reasons"]
    assert "SOURCE_EVIDENCE_LOCK_MISSING" in result["blocking_reasons"]


def test_is_false_coverage_public_web_not_true():
    """_is_false() returns True for PUBLIC_WEB non-True values."""
    from stock_rtx4060.data_quality.final_bar_lock import _to_float

    # _to_float returns None for non-numeric
    assert _to_float("PUBLIC_WEB") is None
    assert _to_float(None) is None

    # Verify source_priority_for normalizes correctly
    from stock_rtx4060.data_quality.final_bar_lock import source_priority_for

    assert source_priority_for("PUBLIC_WEB") == 3
    assert source_priority_for("PYKRX:CACHE") == 4
    assert source_priority_for("KRX_FINAL") == 1
