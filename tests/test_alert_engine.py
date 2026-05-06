"""Tests for alert_engine module (Stage 2)."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from stock_rtx4060.alert_engine import (
    Alert,
    AlertConfig,
    AlertEngine,
    AlertPriority,
    AlertThresholds,
    ConsoleChannel,
    LarkWebhookChannel,
    TelegramChannel,
    ALERT_TYPE_STOP_APPROACHING,
    ALERT_TYPE_TP_APPROACHING,
    ALERT_TYPE_POSITION_CLOSED,
    ALERT_TYPE_EXPOSURE_WARNING,
    ALERT_TYPE_DRAWDOWN_ALERT,
    ALERT_TYPE_MODEL_QUALITY_WARNING,
    SCHEMA_VERSION,
)
from stock_rtx4060.position_tracker import (
    PositionStatus,
    PortfolioSnapshot,
    TrackedPosition,
)


class TestAlertDataclass:
    """Alert 데이터 클래스 테스트."""

    def test_alert_defaults_timestamp(self):
        alert = Alert(alert_type="TEST", ticker="AAPL", track="S", priority=AlertPriority.HIGH, message="test")
        assert alert.timestamp_utc != ""
        assert "T" in alert.timestamp_utc

    def test_alert_to_dict(self):
        alert = Alert(
            alert_type=ALERT_TYPE_STOP_APPROACHING,
            ticker="AAPL",
            track="S",
            priority=AlertPriority.CRITICAL,
            message="STOP 접근",
            metadata={"distance_pct": 0.025},
        )
        d = alert.to_dict()
        assert d["alert_type"] == ALERT_TYPE_STOP_APPROACHING
        assert d["priority"] == AlertPriority.CRITICAL
        assert d["metadata"]["distance_pct"] == 0.025


class TestConsoleChannel:
    """ConsoleChannel 테스트."""

    def test_console_send_returns_true(self):
        ch = ConsoleChannel()
        alert = Alert(alert_type="TEST", ticker=None, track=None, priority=AlertPriority.LOW, message="hello")
        result = ch.send(alert)
        assert result is True


class TestAlertConfig:
    """AlertConfig 테스트."""

    def test_default_config(self):
        cfg = AlertConfig()
        assert cfg.enabled is True
        assert cfg.lark_webhook_url is None
        assert cfg.thresholds.stop_approaching_pct == 0.03

    def test_from_file_missing(self):
        cfg = AlertConfig.from_file("/nonexistent/path.json")
        assert cfg.enabled is True

    def test_to_file_and_back(self, tmp_path):
        cfg = AlertConfig(
            lark_webhook_url="https://lark.example.com/webhook",
            thresholds=AlertThresholds(stop_approaching_pct=0.05),
        )
        path = tmp_path / "alerts.json"
        cfg.to_file(path)
        loaded = AlertConfig.from_file(path)
        assert loaded.lark_webhook_url == "https://lark.example.com/webhook"
        assert loaded.thresholds.stop_approaching_pct == 0.05


class TestAlertEngine:
    """AlertEngine 핵심 로직 테스트."""

    def _make_snapshot(self, track_s_value: float, track_l_value: float, stop_approaching: list[str] = None, tp_approaching: list[str] = None, aapl_current: float = 183.0) -> PortfolioSnapshot:
        positions = []
        if track_s_value > 0:
            # Use current=183, stop=177 → distance_to_stop_pct = (183-177)/177 = 3.4% > 3% → no STOP_APPROACHING
            p = TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5)
            p.mark_open(current_price=aapl_current, timestamp_utc="2026-05-01T10:00:00Z")
            positions.append(p)
        if track_l_value > 0:
            p = TrackedPosition(ticker="MSFT", track="L", entry_date="2026-05-01", entry_price=415.0, quantity=5, stop=375.0, tp1=450.0, tp2=498.0)
            p.mark_open(current_price=415.0, timestamp_utc="2026-05-01T10:00:00Z")
            positions.append(p)

        snapshot = PortfolioSnapshot.from_positions(positions)
        # Override manually to control test conditions
        snapshot.stop_approaching_tickers = stop_approaching or []
        snapshot.tp_approaching_tickers = tp_approaching or []
        return snapshot

    def test_stop_approaching_alert(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=1000.0, track_l_value=0, stop_approaching=["AAPL"])
        emitted = engine.check_and_alert(snapshot)

        stop_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_STOP_APPROACHING]
        assert len(stop_alerts) == 1
        assert stop_alerts[0].ticker == "AAPL"
        assert stop_alerts[0].priority == AlertPriority.CRITICAL

    def test_tp_approaching_alert(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=1000.0, track_l_value=0, tp_approaching=["AAPL"])
        emitted = engine.check_and_alert(snapshot)

        tp_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_TP_APPROACHING]
        assert len(tp_alerts) == 1
        assert tp_alerts[0].ticker == "AAPL"
        assert tp_alerts[0].priority == AlertPriority.HIGH

    def test_model_auc_warning(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=0, track_l_value=0)
        emitted = engine.check_and_alert(snapshot, model_auc=0.50)

        auc_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_MODEL_QUALITY_WARNING]
        assert len(auc_alerts) == 1
        assert "AUC" in auc_alerts[0].message
        assert auc_alerts[0].priority == AlertPriority.HIGH

    def test_oof_coverage_warning(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=0, track_l_value=0)
        emitted = engine.check_and_alert(snapshot, oof_coverage=0.40)

        cov_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_MODEL_QUALITY_WARNING and "OOF" in a.message]
        assert len(cov_alerts) == 1
        assert cov_alerts[0].priority == AlertPriority.HIGH

    def test_no_alerts_when_clean(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=1000.0, track_l_value=1000.0)
        emitted = engine.check_and_alert(snapshot)
        # No stop/tp approaching, exposure within limits, no model warnings
        critical_high = [a for a in emitted if a.priority in (AlertPriority.CRITICAL, AlertPriority.HIGH)]
        assert len(critical_high) == 0

    def test_position_close_detection(self):
        engine = AlertEngine(AlertConfig())
        # First cycle: position open
        p = TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5)
        p.mark_open(current_price=185.0, timestamp_utc="2026-05-01T10:00:00Z")
        snapshot1 = PortfolioSnapshot.from_positions([p])
        engine.check_and_alert(snapshot1)

        # Second cycle: position closed by TP2
        p.update(current_price=205.0, timestamp_utc="2026-05-01T14:00:00Z")
        snapshot2 = PortfolioSnapshot.from_positions([p])
        emitted = engine.check_and_alert(snapshot2)

        close_alerts = [a for a in emitted if a.alert_type == ALERT_TYPE_POSITION_CLOSED]
        assert len(close_alerts) == 1
        assert close_alerts[0].ticker == "AAPL"

    def test_alert_history(self):
        engine = AlertEngine(AlertConfig())
        snapshot = self._make_snapshot(track_s_value=1000.0, track_l_value=0, stop_approaching=["AAPL"])
        engine.check_and_alert(snapshot)
        history = engine.alert_history(limit=10)
        assert len(history) >= 1

    def test_disabled_engine_no_emits(self):
        cfg = AlertConfig(enabled=False)
        engine = AlertEngine(cfg)
        snapshot = self._make_snapshot(track_s_value=1000.0, track_l_value=0, stop_approaching=["AAPL"])
        emitted = engine.check_and_alert(snapshot)
        assert len(emitted) == 0