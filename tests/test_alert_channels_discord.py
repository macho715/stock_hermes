"""Phase 7: tests for DiscordWebhookChannel — payload shape + httpx fallback."""
from __future__ import annotations

import sys
from typing import Any

import pytest

from stock_rtx4060.alert_engine import Alert, AlertPriority
from stock_rtx4060.alert_engine_channels.discord import DiscordWebhookChannel, _build_payload


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        alert_type="DRAWDOWN_ALERT",
        ticker=None,
        track="S",
        priority=AlertPriority.HIGH,
        message="Track-S drawdown 6%",
    )


def test_payload_shape_matches_discord_webhook_spec(sample_alert):
    payload = _build_payload(sample_alert)
    assert "content" in payload  # max 2000 chars per Discord webhook spec
    assert isinstance(payload["content"], str)
    assert len(payload["content"]) <= 2000
    assert "embeds" in payload and isinstance(payload["embeds"], list)
    embed = payload["embeds"][0]
    assert "title" in embed
    assert "description" in embed
    assert "color" in embed and isinstance(embed["color"], int)
    assert "fields" in embed
    field_names = {f["name"] for f in embed["fields"]}
    assert {"Track", "Priority", "Type"}.issubset(field_names)


def test_payload_truncates_overlong_content():
    alert = Alert(
        alert_type="LONG",
        ticker=None,
        track=None,
        priority=AlertPriority.LOW,
        message="x" * 5000,
    )
    payload = _build_payload(alert)
    assert len(payload["content"]) <= 2000


def test_send_via_httpx_posts_payload(monkeypatch, sample_alert):
    sent: dict[str, Any] = {}

    class _Resp:
        status_code = 204  # Discord returns 204 No Content on success

    class _FakeHttpx:
        @staticmethod
        def post(url, *, json, timeout):
            sent["url"] = url
            sent["json"] = json
            return _Resp()

    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpx)
    monkeypatch.setitem(sys.modules, "discord_webhook", None)

    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/123/abc")
    assert ch.send(sample_alert) is True
    assert sent["url"] == "https://discord.com/api/webhooks/123/abc"
    assert sent["json"]["content"]
    assert isinstance(sent["json"]["embeds"], list)


def test_send_returns_false_on_5xx(monkeypatch, sample_alert):
    class _Resp:
        status_code = 503

    class _FakeHttpx:
        @staticmethod
        def post(*_a, **_k):
            return _Resp()

    monkeypatch.setitem(sys.modules, "httpx", _FakeHttpx)
    monkeypatch.setitem(sys.modules, "discord_webhook", None)
    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/123/abc")
    assert ch.send(sample_alert) is False


def test_send_returns_false_when_disabled(sample_alert):
    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/x/y", enabled=False)
    assert ch.send(sample_alert) is False


def test_send_returns_false_when_blank_url(sample_alert):
    ch = DiscordWebhookChannel("")
    assert ch.send(sample_alert) is False


def test_send_swallows_httpx_exception(monkeypatch, sample_alert):
    class _Boom:
        @staticmethod
        def post(*_a, **_k):
            raise RuntimeError("dns fail")

    monkeypatch.setitem(sys.modules, "httpx", _Boom)
    monkeypatch.setitem(sys.modules, "discord_webhook", None)
    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/x/y")
    assert ch.send(sample_alert) is False


def test_send_uses_discord_webhook_lib_when_available(monkeypatch, sample_alert):
    """Exercise the discord_webhook code path via a stub module."""
    captured: dict[str, Any] = {"fields": []}

    class _StubEmbed:
        def __init__(self, *, title="", description="", color=0):
            captured["embed_title"] = title
            captured["embed_description"] = description
            captured["embed_color"] = color

        def add_embed_field(self, *, name, value, inline=True):
            captured["fields"].append((name, value, inline))

    class _StubWebhook:
        def __init__(self, *, url, content=""):
            captured["url"] = url
            captured["content"] = content
            captured["embeds"] = []

        def add_embed(self, embed):
            captured["embeds"].append(embed)

        def execute(self):
            class _Resp:
                status_code = 200

            return _Resp()

    import types

    stub = types.ModuleType("discord_webhook")
    stub.DiscordEmbed = _StubEmbed  # type: ignore[attr-defined]
    stub.DiscordWebhook = _StubWebhook  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "discord_webhook", stub)

    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/123/abc")
    assert ch.send(sample_alert) is True
    assert captured["url"] == "https://discord.com/api/webhooks/123/abc"
    assert captured["fields"]


def test_send_swallows_discord_webhook_exception(monkeypatch, sample_alert):
    class _StubWebhook:
        def __init__(self, *_a, **_k):
            raise RuntimeError("invalid url")

    import types

    stub = types.ModuleType("discord_webhook")
    stub.DiscordEmbed = object  # type: ignore[attr-defined]
    stub.DiscordWebhook = _StubWebhook  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "discord_webhook", stub)

    ch = DiscordWebhookChannel("https://discord.com/api/webhooks/123/abc")
    assert ch.send(sample_alert) is False
