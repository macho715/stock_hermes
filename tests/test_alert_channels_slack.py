"""Phase 7: tests for SlackWebhookChannel — payload shape + httpx fallback."""
from __future__ import annotations

import sys
from typing import Any

import pytest

from stock_rtx4060.alert_engine import Alert, AlertPriority
from stock_rtx4060.alert_engine_channels.slack import SlackWebhookChannel, _build_payload


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        alert_type="STOP_APPROACHING",
        ticker="AAPL",
        track="S",
        priority=AlertPriority.CRITICAL,
        message="AAPL near stop loss",
        metadata={"distance_pct": 0.025},
    )


def test_payload_contains_required_slack_fields(sample_alert):
    payload = _build_payload(sample_alert)
    assert "text" in payload  # required by Slack incoming webhook spec
    assert isinstance(payload["text"], str) and payload["text"]
    assert "attachments" in payload and isinstance(payload["attachments"], list)
    assert len(payload["attachments"]) == 1
    att = payload["attachments"][0]
    assert "color" in att
    assert "title" in att
    assert "fields" in att and any(f["title"] == "Ticker" for f in att["fields"])
    assert "STOP_APPROACHING" in payload["text"]
    assert "CRITICAL" in payload["text"]


def test_payload_omits_ticker_field_when_none():
    alert = Alert(alert_type="DAILY_SUMMARY", ticker=None, track=None, priority=AlertPriority.LOW, message="ok")
    payload = _build_payload(alert)
    field_titles = {f["title"] for f in payload["attachments"][0]["fields"]}
    assert "Ticker" not in field_titles
    assert "Priority" in field_titles


def test_send_via_httpx_posts_correct_payload(monkeypatch, sample_alert):
    sent: dict[str, Any] = {}

    class _FakeResp:
        status_code = 200

    class _FakeHttpx:
        @staticmethod
        def post(url, *, json, timeout):
            sent["url"] = url
            sent["json"] = json
            sent["timeout"] = timeout
            return _FakeResp()

    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpx)
    # Force the slack_sdk path to fall through to httpx by removing slack_sdk
    monkeypatch.setitem(sys.modules, "slack_sdk", None)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", None)

    ch = SlackWebhookChannel("https://hooks.slack.test/services/X/Y/Z")
    assert ch.send(sample_alert) is True
    assert sent["url"] == "https://hooks.slack.test/services/X/Y/Z"
    assert "text" in sent["json"]
    assert "attachments" in sent["json"]
    assert sent["timeout"] == 10.0


def test_send_via_httpx_returns_false_on_4xx(monkeypatch, sample_alert):
    class _Resp:
        status_code = 401

    class _FakeHttpx:
        @staticmethod
        def post(*_a, **_k):
            return _Resp()

    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpx)
    monkeypatch.setitem(sys.modules, "slack_sdk", None)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", None)
    ch = SlackWebhookChannel("https://hooks.slack.test/x")
    assert ch.send(sample_alert) is False


def test_send_returns_false_when_disabled(sample_alert):
    ch = SlackWebhookChannel("https://hooks.slack.test/x", enabled=False)
    assert ch.send(sample_alert) is False


def test_send_returns_false_when_url_blank(sample_alert):
    ch = SlackWebhookChannel("")
    assert ch.send(sample_alert) is False


def test_send_swallows_httpx_exception(monkeypatch, sample_alert):
    class _Boom:
        @staticmethod
        def post(*_a, **_k):
            raise RuntimeError("conn refused")

    monkeypatch.setitem(sys.modules, "httpx", _Boom)
    monkeypatch.setitem(sys.modules, "slack_sdk", None)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", None)
    ch = SlackWebhookChannel("https://hooks.slack.test/x")
    assert ch.send(sample_alert) is False


def test_send_uses_slack_sdk_when_available(monkeypatch, sample_alert):
    """Exercise the slack_sdk code path via a stub module."""
    captured: dict[str, Any] = {}

    class _StubResp:
        status_code = 200

    class _StubClient:
        def __init__(self, url):
            captured["url"] = url

        def send(self, *, text, attachments):
            captured["text"] = text
            captured["attachments"] = attachments
            return _StubResp()

    import types

    webhook_mod = types.ModuleType("slack_sdk.webhook")
    webhook_mod.WebhookClient = _StubClient  # type: ignore[attr-defined]
    sdk_mod = types.ModuleType("slack_sdk")
    sdk_mod.webhook = webhook_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "slack_sdk", sdk_mod)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", webhook_mod)

    ch = SlackWebhookChannel("https://hooks.slack.test/services/X/Y/Z")
    assert ch.send(sample_alert) is True
    assert captured["url"] == "https://hooks.slack.test/services/X/Y/Z"
    assert "STOP_APPROACHING" in captured["text"]
    assert captured["attachments"]


def test_send_swallows_slack_sdk_exception(monkeypatch, sample_alert):
    class _BoomClient:
        def __init__(self, *_a, **_k):
            raise RuntimeError("bad url")

    import types

    webhook_mod = types.ModuleType("slack_sdk.webhook")
    webhook_mod.WebhookClient = _BoomClient  # type: ignore[attr-defined]
    sdk_mod = types.ModuleType("slack_sdk")
    sdk_mod.webhook = webhook_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "slack_sdk", sdk_mod)
    monkeypatch.setitem(sys.modules, "slack_sdk.webhook", webhook_mod)

    ch = SlackWebhookChannel("https://hooks.slack.test/x")
    assert ch.send(sample_alert) is False
