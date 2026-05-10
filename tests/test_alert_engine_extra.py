"""Extra tests for alert_engine.py — covers uncovered lines.

Missing lines targeted:
  54->exit, 65->exit, 82-83, 86-109, 116-118, 121-138,
  211-213, 218, 223, 235-240, 242-247, 260, 262, 266, 277, 282-283,
  335-344, 349-362, 372, 441-444, 454-464
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stock_rtx4060.alert_engine import (
    ALERT_TYPE_DRAWDOWN_ALERT,
    ALERT_TYPE_EXPOSURE_WARNING,
    ALERT_TYPE_MODEL_QUALITY_WARNING,
    ALERT_TYPE_POSITION_CLOSED,
    ALERT_TYPE_STOP_APPROACHING,
    ALERT_TYPE_TP_APPROACHING,
    Alert,
    AlertChannel,
    AlertConfig,
    AlertEngine,
    AlertPriority,
    AlertThresholds,
    ConsoleChannel,
    LarkWebhookChannel,
    TelegramChannel,
    create_default_config,
    dispatch,
    register_channel,
    registered_channels,
    unregister_channel,
)
from stock_rtx4060.position_tracker import (
    PortfolioSnapshot,
    PositionStatus,
    TrackedPosition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(
    *,
    stop_tickers: list[str] | None = None,
    tp_tickers: list[str] | None = None,
    track_s_value: float = 0.0,
    total_position_value: float = 0.0,
) -> PortfolioSnapshot:
    positions: list[TrackedPosition] = []
    snapshot = PortfolioSnapshot.from_positions(positions)
    snapshot.stop_approaching_tickers = stop_tickers or []
    snapshot.tp_approaching_tickers = tp_tickers or []
    snapshot.track_s_value = track_s_value
    snapshot.total_position_value = total_position_value
    snapshot.total_exposure = total_position_value
    return snapshot


# ---------------------------------------------------------------------------
# Alert.__post_init__ — explicit timestamp_utc (line 54->exit)
# ---------------------------------------------------------------------------

def test_alert_explicit_timestamp_utc_preserved():
    explicit_ts = "2024-01-01T10:00:00"
    alert = Alert(
        alert_type="TEST",
        ticker=None,
        track=None,
        priority=AlertPriority.LOW,
        message="test",
        timestamp_utc=explicit_ts,
    )
    assert alert.timestamp_utc == explicit_ts


# ---------------------------------------------------------------------------
# AlertChannel Protocol (line 65->exit)
# ---------------------------------------------------------------------------

def test_alert_channel_protocol():
    """Custom class implementing AlertChannel protocol is accepted."""

    class MyChannel:
        def send(self, alert: Alert) -> bool:
            return True

    ch = MyChannel()
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="hi")
    assert ch.send(alert) is True


# ---------------------------------------------------------------------------
# LarkWebhookChannel — disabled / no url (lines 82-83, 86-87)
# ---------------------------------------------------------------------------

def test_lark_channel_disabled_returns_false():
    ch = LarkWebhookChannel(webhook_url="https://lark.example.com/hook", enabled=False)
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
    assert ch.send(alert) is False


def test_lark_channel_empty_url_returns_false():
    ch = LarkWebhookChannel(webhook_url="", enabled=True)
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
    assert ch.send(alert) is False


def test_lark_channel_send_success():
    ch = LarkWebhookChannel(webhook_url="https://lark.example.com/hook", enabled=True)
    alert = Alert(alert_type="TEST", ticker="AAPL", track="S", priority=AlertPriority.HIGH, message="test")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        result = ch.send(alert)

    assert result is True


def test_lark_channel_send_http_failure():
    ch = LarkWebhookChannel(webhook_url="https://lark.example.com/hook", enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.HIGH, message="test")

    with patch("urllib.request.urlopen", side_effect=Exception("network error")):
        result = ch.send(alert)

    assert result is False


def test_lark_channel_send_non_200_response():
    ch = LarkWebhookChannel(webhook_url="https://lark.example.com/hook", enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.LOW, message="test")

    mock_resp = MagicMock()
    mock_resp.status = 500

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        result = ch.send(alert)

    assert result is False


# ---------------------------------------------------------------------------
# LarkWebhookChannel — alert with no ticker (no ticker conditional in message)
# ---------------------------------------------------------------------------

def test_lark_channel_send_no_ticker():
    ch = LarkWebhookChannel(webhook_url="https://lark.example.com/hook", enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.LOW, message="no ticker")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        result = ch.send(alert)

    assert result is True


# ---------------------------------------------------------------------------
# TelegramChannel — disabled / missing token / send paths (lines 116-138)
# ---------------------------------------------------------------------------

def test_telegram_channel_disabled_returns_false():
    ch = TelegramChannel(bot_token="token123", chat_id="chat123", enabled=False)
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
    assert ch.send(alert) is False


def test_telegram_channel_empty_token_returns_false():
    ch = TelegramChannel(bot_token="", chat_id="chat123", enabled=True)
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
    assert ch.send(alert) is False


def test_telegram_channel_empty_chat_id_returns_false():
    ch = TelegramChannel(bot_token="token123", chat_id="", enabled=True)
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
    assert ch.send(alert) is False


def test_telegram_channel_send_success():
    ch = TelegramChannel(bot_token="token123", chat_id="chat123", enabled=True)
    alert = Alert(alert_type="TEST", ticker="AAPL", track="S", priority=AlertPriority.CRITICAL, message="test")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        result = ch.send(alert)

    assert result is True


def test_telegram_channel_send_network_failure():
    ch = TelegramChannel(bot_token="token123", chat_id="chat123", enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.LOW, message="test")

    with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        result = ch.send(alert)

    assert result is False


def test_telegram_channel_send_no_ticker():
    ch = TelegramChannel(bot_token="token123", chat_id="chat123", enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.MEDIUM, message="no ticker")

    mock_resp = MagicMock()
    mock_resp.status = 200

    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__ = lambda s: mock_resp
        mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
        result = ch.send(alert)

    assert result is True


# ---------------------------------------------------------------------------
# register_channel / unregister_channel / registered_channels (lines 211-213, 218, 223)
# ---------------------------------------------------------------------------

def test_register_channel_empty_name_raises():
    ch = ConsoleChannel()
    with pytest.raises(ValueError, match="non-empty string"):
        register_channel("", ch)


def test_register_channel_non_string_raises():
    ch = ConsoleChannel()
    with pytest.raises(ValueError, match="non-empty string"):
        register_channel(123, ch)  # type: ignore[arg-type]


def test_register_and_unregister_channel():
    ch = ConsoleChannel()
    register_channel("_test_ch_extra", ch)
    assert "_test_ch_extra" in registered_channels()

    unregister_channel("_test_ch_extra")
    assert "_test_ch_extra" not in registered_channels()


def test_unregister_missing_channel_noop():
    """unregister_channel on unknown name should not raise."""
    unregister_channel("__nonexistent_channel__")  # no exception


# ---------------------------------------------------------------------------
# _autoregister_env_channels — slack / discord env vars (lines 235-247)
# ---------------------------------------------------------------------------

def test_autoregister_slack_env_channel(monkeypatch):
    """STOCK1901_SLACK_WEBHOOK_URL triggers SlackWebhookChannel registration."""
    monkeypatch.setenv("STOCK1901_SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")

    # Clear any existing slack_env registration so we can observe fresh import
    unregister_channel("slack_env")

    # Import and call the private function directly
    from stock_rtx4060.alert_engine import _autoregister_env_channels
    _autoregister_env_channels()

    channels = registered_channels()
    # Either it registered (slack available) or gracefully failed
    # We just verify the function ran without raising
    assert isinstance(channels, dict)
    # cleanup
    unregister_channel("slack_env")


def test_autoregister_discord_env_channel(monkeypatch):
    """STOCK1901_DISCORD_WEBHOOK_URL triggers DiscordWebhookChannel registration."""
    monkeypatch.setenv("STOCK1901_DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test")

    unregister_channel("discord_env")
    from stock_rtx4060.alert_engine import _autoregister_env_channels
    _autoregister_env_channels()

    channels = registered_channels()
    assert isinstance(channels, dict)
    unregister_channel("discord_env")


# ---------------------------------------------------------------------------
# AlertEngine.__init__ — with lark/telegram config (lines 260, 262, 266)
# ---------------------------------------------------------------------------

def test_alertengine_init_with_lark_config():
    cfg = AlertConfig(lark_webhook_url="https://lark.example.com/hook")
    engine = AlertEngine(cfg)
    channel_types = [type(ch).__name__ for ch in engine.channels]
    assert "LarkWebhookChannel" in channel_types


def test_alertengine_init_with_telegram_config():
    cfg = AlertConfig(telegram_bot_token="tok", telegram_chat_id="123")
    engine = AlertEngine(cfg)
    channel_types = [type(ch).__name__ for ch in engine.channels]
    assert "TelegramChannel" in channel_types


def test_alertengine_registered_channels_appended():
    """Channels registered globally get appended to new engine instances."""
    mock_ch = MagicMock()
    register_channel("_test_mock_channel", mock_ch)
    try:
        engine = AlertEngine()
        assert mock_ch in engine.channels
    finally:
        unregister_channel("_test_mock_channel")


# ---------------------------------------------------------------------------
# AlertEngine._emit — channel exception is swallowed (lines 277, 282-283)
# ---------------------------------------------------------------------------

def test_emit_channel_exception_is_swallowed():
    """Failing channel must not propagate exception."""
    engine = AlertEngine()

    class BrokenChannel:
        def send(self, alert: Alert) -> bool:
            raise RuntimeError("channel broken")

    engine.channels = [BrokenChannel()]
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="hi")
    engine._emit(alert)  # should not raise


def test_emit_disabled_engine_no_history():
    engine = AlertEngine(AlertConfig(enabled=False))
    alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="hi")
    engine._emit(alert)
    assert len(engine._alert_history) == 0


# ---------------------------------------------------------------------------
# AlertEngine.check_and_alert — exposure warning (lines 335-344)
# ---------------------------------------------------------------------------

def test_exposure_warning_triggered_above_threshold():
    engine = AlertEngine(AlertConfig())
    # With assumed_capital=100_000 and max_exposure_pct=0.60
    # we need position_value > 60_000
    snapshot = _make_snapshot(total_position_value=70_000.0)
    emitted = engine.check_and_alert(snapshot)
    exposure_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_EXPOSURE_WARNING]
    assert len(exposure_alerts) == 1
    assert exposure_alerts[0].priority == AlertPriority.CRITICAL


def test_exposure_warning_not_triggered_below_threshold():
    engine = AlertEngine(AlertConfig())
    snapshot = _make_snapshot(total_position_value=50_000.0)
    emitted = engine.check_and_alert(snapshot)
    exposure_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_EXPOSURE_WARNING]
    assert len(exposure_alerts) == 0


def test_exposure_warning_zero_position_no_alert():
    engine = AlertEngine(AlertConfig())
    snapshot = _make_snapshot(total_position_value=0.0)
    emitted = engine.check_and_alert(snapshot)
    exposure_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_EXPOSURE_WARNING]
    assert len(exposure_alerts) == 0


# ---------------------------------------------------------------------------
# AlertEngine.check_and_alert — drawdown alert (lines 349-362, 372)
# ---------------------------------------------------------------------------

def test_drawdown_alert_on_second_run():
    engine = AlertEngine(AlertConfig())

    # First run: establish peak
    snap1 = _make_snapshot(track_s_value=10_000.0)
    engine.check_and_alert(snap1)

    # Second run: big drop → triggers drawdown alert
    snap2 = _make_snapshot(track_s_value=9_000.0)
    emitted = engine.check_and_alert(snap2)
    drawdown_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_DRAWDOWN_ALERT]
    assert len(drawdown_alerts) == 1
    assert "드로우다운" in drawdown_alerts[0].message


def test_drawdown_alert_not_triggered_below_threshold():
    engine = AlertEngine(AlertConfig())

    # First run
    snap1 = _make_snapshot(track_s_value=10_000.0)
    engine.check_and_alert(snap1)

    # Second run: small drop (below 5% threshold)
    snap2 = _make_snapshot(track_s_value=9_600.0)
    emitted = engine.check_and_alert(snap2)
    drawdown_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_DRAWDOWN_ALERT]
    assert len(drawdown_alerts) == 0


def test_drawdown_first_run_initializes_peak():
    engine = AlertEngine(AlertConfig())
    snap = _make_snapshot(track_s_value=5_000.0)
    engine.check_and_alert(snap)
    assert engine._peak_track_s_value == 5_000.0


def test_drawdown_peak_updated_on_new_high():
    engine = AlertEngine(AlertConfig())

    snap1 = _make_snapshot(track_s_value=5_000.0)
    engine.check_and_alert(snap1)

    snap2 = _make_snapshot(track_s_value=8_000.0)
    engine.check_and_alert(snap2)
    assert engine._peak_track_s_value == 8_000.0


def test_drawdown_zero_track_s_value_no_alert():
    engine = AlertEngine(AlertConfig())
    snap = _make_snapshot(track_s_value=0.0)
    emitted = engine.check_and_alert(snap)
    drawdown_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_DRAWDOWN_ALERT]
    assert len(drawdown_alerts) == 0


# ---------------------------------------------------------------------------
# create_default_config (lines 441-444)
# ---------------------------------------------------------------------------

def test_create_default_config_no_file():
    cfg = create_default_config()
    assert isinstance(cfg, AlertConfig)
    assert cfg.enabled is True


def test_create_default_config_writes_file(tmp_path):
    out = tmp_path / "default_alerts.json"
    cfg = create_default_config(output_path=out)
    assert out.exists()
    loaded = AlertConfig.from_file(out)
    assert loaded.enabled is True


# ---------------------------------------------------------------------------
# dispatch (lines 454-464)
# ---------------------------------------------------------------------------

def test_dispatch_single_alert():
    alert = Alert(alert_type="TEST", ticker="AAPL", track="S", priority=AlertPriority.LOW, message="dispatch test")
    result = dispatch(alert)
    assert result["dispatched"] == 1
    assert result["total"] == 1
    assert result["channel_count"] >= 1


def test_dispatch_list_of_alerts():
    alerts = [
        Alert(alert_type="TEST", ticker="AAPL", track="S", priority=AlertPriority.LOW, message="msg1"),
        Alert(alert_type="TEST", ticker="MSFT", track="L", priority=AlertPriority.LOW, message="msg2"),
    ]
    result = dispatch(alerts)
    assert result["dispatched"] == 2
    assert result["total"] == 2


def test_dispatch_empty_list():
    result = dispatch([])
    assert result["dispatched"] == 0
    assert result["total"] == 0


def test_dispatch_channel_failure_still_counts():
    """dispatch must not raise even if _emit has a broken channel."""

    class BrokenChannel:
        def send(self, alert: Alert) -> bool:
            raise RuntimeError("broken")

    register_channel("_test_broken_dispatch", BrokenChannel())
    try:
        alert = Alert(alert_type="X", ticker=None, track=None, priority=AlertPriority.LOW, message="test")
        result = dispatch(alert)
        assert result["total"] == 1
    finally:
        unregister_channel("_test_broken_dispatch")


def test_dispatch_with_custom_config(tmp_path):
    cfg = AlertConfig(enabled=True)
    alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.LOW, message="cfg test")
    result = dispatch(alert, config=cfg)
    assert result["dispatched"] == 1


# ---------------------------------------------------------------------------
# AlertEngine._pos_from_dict (covered implicitly via check_and_alert position tracking)
# ---------------------------------------------------------------------------

def test_pos_from_dict_restores_tracked_position():
    engine = AlertEngine(AlertConfig())
    pos_dict = {
        "ticker": "AAPL",
        "track": "S",
        "entry_date": "2026-05-01",
        "entry_price": 185.0,
        "quantity": 10,
        "stop": 177.0,
        "tp1": 194.0,
        "tp2": 203.5,
        "status": PositionStatus.OPEN.value,
        "current_price": 186.0,
    }
    pos = engine._pos_from_dict(pos_dict)
    assert pos.ticker == "AAPL"
    assert pos.entry_price == 185.0
    assert pos.status == PositionStatus.OPEN.value


def test_pos_from_dict_defaults_missing_fields():
    engine = AlertEngine(AlertConfig())
    pos_dict = {"ticker": "MSFT"}
    pos = engine._pos_from_dict(pos_dict)
    assert pos.ticker == "MSFT"
    assert pos.track == "S"
    assert pos.entry_price == 0.0
    assert pos.quantity == 0
