"""RED tests for KRX_FINAL / BROKER_FINAL authoritative final-bar provider paths."""

import pandas as pd

from stock_rtx4060.data_providers import load_ohlcv_with_provider
from stock_rtx4060.data_quality.final_bar_lock import (
    compare_cache_vs_final,
    provider_final_bar_metadata,
)


# ---------------------------------------------------------------------------
# Test 1 — KRX final provider marks authoritative EOD final
# ---------------------------------------------------------------------------


def test_krx_final_provider_marks_authoritative_eod_final(monkeypatch):
    """KRX_FINAL source_priority=1, bar_type=EOD_FINAL, eod_confirmed=True."""
    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="krx_final",
        after_market_close=True,
    )

    assert result.metadata is not None
    assert result.metadata["source_priority"] == 1
    assert result.metadata["bar_type"] == "EOD_FINAL"
    assert result.metadata["eod_confirmed"] is True
    assert result.metadata["source_evidence_lock"] is True
    assert result.metadata["final_bar_lock"]["inference_allowed"] is True
    assert result.metadata["final_bar_lock"]["readiness_status"] == "PASS"


# ---------------------------------------------------------------------------
# Test 2 — Broker final provider marks authoritative EOD final
# ---------------------------------------------------------------------------


def test_broker_final_provider_marks_authoritative_eod_final(monkeypatch):
    """BROKER_FINAL source_priority=1, bar_type=EOD_FINAL, eod_confirmed=True."""
    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="broker_final",
        after_market_close=True,
    )

    assert result.metadata is not None
    assert result.metadata["source_priority"] == 1
    assert result.metadata["bar_type"] == "EOD_FINAL"
    assert result.metadata["eod_confirmed"] is True
    assert result.metadata["source_evidence_lock"] is True


# ---------------------------------------------------------------------------
# Test 3 — Public web cannot lock final bar
# ---------------------------------------------------------------------------


def test_public_web_provider_cannot_lock_final_bar():
    """PUBLIC_WEB source_priority=3; inference_allowed=False."""
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


# ---------------------------------------------------------------------------
# Test 4 — Missing KRX final bar blocks inference
# ---------------------------------------------------------------------------


def test_krx_final_missing_bar_blocks_inference(monkeypatch):
    """KRX_FINAL with as_of=2099 returns eod_confirmed=False and blocks inference."""
    import stock_rtx4060.data_providers as dp
    from stock_rtx4060.data_providers import ProviderResult

    def fake_empty(*args, **kwargs):
        # Returns empty bar → eod_confirmed=False path
        return ProviderResult(
            frame=pd.DataFrame(),
            provider_requested="krx_final",
            provider_used="krx_final",
            source="KRX_FINAL",
            metadata=dp.provider_final_bar_metadata(
                source="KRX_FINAL",
                bar_type="EOD_FINAL_UNAVAILABLE",
                eod_confirmed=False,
                source_evidence_lock=False,
                after_market_close=True,
            ),
        )

    monkeypatch.setattr(dp, "_load_authoritative_final_ohlcv", fake_empty)

    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="krx_final",
        after_market_close=True,
        as_of="2099-01-01",
    )

    assert result.metadata["eod_confirmed"] is False
    assert result.metadata["source_evidence_lock"] is False
    assert result.metadata["final_bar_lock"]["inference_allowed"] is False


# ---------------------------------------------------------------------------
# Test 5 — Cache vs final diff is reported
# ---------------------------------------------------------------------------


def test_cache_vs_final_diff_reported():
    """compare_cache_vs_final returns AMBER_DATA_LAG with correct diff metrics."""
    result = compare_cache_vs_final(
        cache_close=308500,
        final_close=317000,
        cache_volume=9039622,
        final_volume=37241537,
    )

    assert result["status"] == "AMBER_DATA_LAG"
    assert result["close_diff_pct"] > 1.0
    assert result["volume_lag_ratio"] > 2.0


# ---------------------------------------------------------------------------
# Test 6 — KRX_FINAL after_market_close=True sets bar_type=EOD_FINAL
# ---------------------------------------------------------------------------


def test_krx_final_after_market_close_true_sets_eod_final(monkeypatch):
    """With after_market_close=True the metadata bar_type should be EOD_FINAL."""
    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="krx_final",
        after_market_close=True,
    )

    assert result.metadata is not None
    assert result.metadata["bar_type"] == "EOD_FINAL"
    assert result.metadata["after_market_close"] is True


# ---------------------------------------------------------------------------
# Test 7 — broker_final sets broker_order_execution=False (hard safety block)
# ---------------------------------------------------------------------------


def test_broker_final_never_sets_broker_order_execution(monkeypatch):
    """BROKER_FINAL provider must never emit broker_order_execution=true."""
    result = load_ohlcv_with_provider(
        "005930.KS",
        "5y",
        data_provider="broker_final",
        after_market_close=True,
    )

    assert result.metadata.get("broker_order_execution") is not True