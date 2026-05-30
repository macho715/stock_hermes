"""Tests for the OpenAI event shock gate (FR-104 through FR-106)."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from stock_rtx4060.advisors.openai_event_shock import (
    STATUS_AMBER_CONFLICT,
    STATUS_DEGRADED,
    STATUS_PASS,
    check_event_shock,
)


# ---------------------------------------------------------------------------
# Test helpers — mock OpenAI client
# ---------------------------------------------------------------------------


def _make_openai_client(category: str, sentiment: float) -> Any:
    """Return a mock OpenAI client that returns given category/sentiment."""
    content = json.dumps({"category": category, "sentiment_score": sentiment})
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    completion = SimpleNamespace(choices=[choice])
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    return client


def _make_error_client() -> Any:
    """Return a mock that raises on every API call."""
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("API down")
    return client


# ---------------------------------------------------------------------------
# FR-104: HBM event + SELL → AMBER_EVENT_SIGNAL_CONFLICT
# ---------------------------------------------------------------------------


class TestHBMEventWithSell:
    def test_hbm_event_and_sell_returns_amber_conflict(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung ships HBM4E 12-layer samples to global AI customers",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 0.87),
        )
        assert result["event_shock"] is True
        assert result["readiness_status"] == STATUS_AMBER_CONFLICT
        assert "EVENT_SHOCK_CONFLICTS_WITH_SELL" in result["blocking_reasons"]

    def test_ai_memory_event_and_sell_triggers_conflict(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM for AI servers — massive shipment confirmed",
            signal="SELL",
            openai_client=_make_openai_client("AI_MEMORY", 0.90),
        )
        assert result["event_shock"] is True
        assert result["readiness_status"] == STATUS_AMBER_CONFLICT

    def test_customer_shipment_and_sell_triggers_conflict(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung confirms HBM4 sample delivery to Nvidia",
            signal="SELL",
            openai_client=_make_openai_client("CUSTOMER_SHIPMENT", 0.80),
        )
        assert result["event_shock"] is True
        assert result["readiness_status"] == STATUS_AMBER_CONFLICT

    def test_below_sentiment_threshold_not_flagged_as_shock(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung announces minor supply update",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 0.60),  # < 0.75
        )
        assert result["event_shock"] is False
        assert result["readiness_status"] == STATUS_PASS

    def test_none_category_not_flagged(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung Q2 results in line with estimates",
            signal="SELL",
            openai_client=_make_openai_client("NONE", 0.50),
        )
        assert result["event_shock"] is False
        assert result["readiness_status"] == STATUS_PASS


# ---------------------------------------------------------------------------
# FR-105: OpenAI unavailable → DEGRADED_NO_EVENT_DATA (no block)
# ---------------------------------------------------------------------------


class TestDegradedMode:
    def test_api_error_returns_degraded_not_blocked(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E shipment",
            signal="SELL",
            openai_client=_make_error_client(),
        )
        assert result["event_shock"] is False
        assert result["readiness_status"] == STATUS_DEGRADED
        assert result["blocking_reasons"] == []

    def test_no_api_key_returns_degraded(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            result = check_event_shock(
                ticker="005930.KS",
                news_title="Samsung HBM4E",
                signal="SELL",
                openai_client=None,
            )
        assert result["readiness_status"] == STATUS_DEGRADED

    def test_degraded_mode_never_blocks(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E",
            signal="SELL",
            openai_client=_make_error_client(),
        )
        # Degraded must not block inference
        assert result["event_shock"] is False
        assert "EVENT_SHOCK_CONFLICTS_WITH_SELL" not in result["blocking_reasons"]


# ---------------------------------------------------------------------------
# FR-106: event shock does NOT force BUY / capital
# ---------------------------------------------------------------------------


class TestEventShockSafetyInvariants:
    def test_no_buy_signal_emitted(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E ships to AI customers",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 0.90),
        )
        assert result.get("signal") != "BUY"

    def test_new_capital_always_false(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E ships",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 0.90),
        )
        assert result["new_capital_allowed"] is False

    def test_broker_order_always_false(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E ships",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 0.90),
        )
        assert result["broker_order_execution"] is False

    def test_buy_signal_with_hbm_event_passes(self):
        """BUY signal is not blocked even when an event shock is detected."""
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E ships to AI customers",
            signal="BUY",
            openai_client=_make_openai_client("HBM", 0.90),
        )
        # event_shock=True but no blocking reason because signal is BUY
        assert result["event_shock"] is True
        assert "EVENT_SHOCK_CONFLICTS_WITH_SELL" not in result["blocking_reasons"]

    def test_sentiment_clamped_to_valid_range(self):
        result = check_event_shock(
            ticker="005930.KS",
            news_title="Samsung HBM4E",
            signal="SELL",
            openai_client=_make_openai_client("HBM", 1.5),  # > 1.0
        )
        assert 0.0 <= result["sentiment_score"] <= 1.0
