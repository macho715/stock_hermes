"""
Alert Engine — 알림 발송 시스템

Stage 2 of 5-stage investment system upgrade.
설정 기반 플러그인 구조: Lark, Telegram, Email, Console.
읽기 전용. 주문 실행 없음.
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from .position_tracker import PortfolioSnapshot, TrackedPosition, PositionStatus

SCHEMA_VERSION = "alert_engine.v1"
logger = logging.getLogger(__name__)


class AlertPriority(str):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


ALERT_TYPE_STOP_APPROACHING = "STOP_APPROACHING"
ALERT_TYPE_TP_APPROACHING = "TP_APPROACHING"
ALERT_TYPE_POSITION_CLOSED = "POSITION_CLOSED"
ALERT_TYPE_NEW_POSITION = "NEW_POSITION"
ALERT_TYPE_DRAWDOWN_ALERT = "DRAWDOWN_ALERT"
ALERT_TYPE_EXPOSURE_WARNING = "EXPOSURE_WARNING"
ALERT_TYPE_DAILY_SUMMARY = "DAILY_SUMMARY"
ALERT_TYPE_MODEL_QUALITY_WARNING = "MODEL_QUALITY_WARNING"


@dataclass
class Alert:
    alert_type: str
    ticker: str | None
    track: str | None
    priority: str
    message: str
    timestamp_utc: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.timestamp_utc:
            self.timestamp_utc = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class AlertChannel(Protocol):
    """알림 채널 프로토콜."""

    def send(self, alert: Alert) -> bool: ...


class ConsoleChannel:
    """Console 출력 채널 — 항상 활성화."""

    def send(self, alert: Alert) -> bool:
        emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🔔", "LOW": "ℹ️"}.get(alert.priority, "📣")
        ts = alert.timestamp_utc[11:19]
        print(f"[{ts}] {emoji} [{alert.priority}] {alert.alert_type} | {alert.message}")
        return True


class LarkWebhookChannel:
    """Lark (飞书) Webhook 채널."""

    def __init__(self, webhook_url: str, enabled: bool = True):
        self.webhook_url = webhook_url
        self.enabled = enabled

    def send(self, alert: Alert) -> bool:
        if not self.enabled or not self.webhook_url:
            return False
        try:
            import urllib.request

            payload = {
                "msg_type": "interactive",
                "card": {
                    "tag": "markdown",
                    "content": f"**{alert.priority}** `{alert.alert_type}`\n\n{alert.message}\n\n⏰ {alert.timestamp_utc[:19]}Z\n{f'📌 Ticker: {alert.ticker} ({alert.track})' if alert.ticker else ''}",
                },
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning("Lark webhook failed: %s", exc)
            return False


class TelegramChannel:
    """Telegram Bot API 채널."""

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled

    def send(self, alert: Alert) -> bool:
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False
        try:
            import urllib.request

            emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "🔔", "LOW": "ℹ️"}.get(alert.priority, "📣")
            text = f"{emoji} *{alert.alert_type}*\n\n{alert.message}\n\n⏰ {alert.timestamp_utc[:19]}Z\n{f'📌 Ticker: {alert.ticker} ({alert.track})' if alert.ticker else ''}"
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False


@dataclass
class AlertThresholds:
    stop_approaching_pct: float = 0.03
    tp_approaching_pct: float = 0.03
    max_exposure_pct: float = 0.60
    drawdown_alert_pct: float = 0.05
    track_s_drawdown_alert_pct: float = 0.05
    model_auc_min: float = 0.55
    model_oof_coverage_min: float = 0.50


@dataclass
class AlertConfig:
    enabled: bool = True
    lark_webhook_url: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    email_smtp_host: str | None = None
    email_smtp_port: int = 587
    email_from: str | None = None
    email_to: str | None = None
    thresholds: AlertThresholds = field(default_factory=AlertThresholds)
    alert_enabled: bool = True  # legacy compatibility

    @classmethod
    def from_file(cls, path: str | Path) -> "AlertConfig":
        p = Path(path)
        if not p.exists():
            return cls()
        data = json.loads(p.read_text(encoding="utf-8"))
        thresholds_data = data.get("thresholds", {})
        thresholds = AlertThresholds(**{k: v for k, v in thresholds_data.items() if k in AlertThresholds.__dataclass_fields__})
        return cls(
            enabled=data.get("alert_enabled", True),
            lark_webhook_url=data.get("lark_webhook_url"),
            telegram_bot_token=data.get("telegram_bot_token"),
            telegram_chat_id=data.get("telegram_chat_id"),
            email_smtp_host=data.get("email_smtp_host"),
            email_smtp_port=data.get("email_smtp_port", 587),
            email_from=data.get("email_from"),
            email_to=data.get("email_to"),
            thresholds=thresholds,
        )

    def to_file(self, path: str | Path) -> None:
        data = {
            "alert_enabled": self.enabled,
            "lark_webhook_url": self.lark_webhook_url,
            "telegram_bot_token": self.telegram_bot_token,
            "telegram_chat_id": self.telegram_chat_id,
            "email_smtp_host": self.email_smtp_host,
            "email_smtp_port": self.email_smtp_port,
            "email_from": self.email_from,
            "email_to": self.email_to,
            "thresholds": asdict(self.thresholds),
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class AlertEngine:
    """알림 엔진 — Position Tracker 상태 감시 및 알림 발송."""

    def __init__(self, config: AlertConfig | None = None):
        self.config = config or AlertConfig()
        self.channels: list[AlertChannel] = [ConsoleChannel()]
        if self.config.lark_webhook_url:
            self.channels.append(LarkWebhookChannel(self.config.lark_webhook_url))
        if self.config.telegram_bot_token and self.config.telegram_chat_id:
            self.channels.append(TelegramChannel(self.config.telegram_bot_token, self.config.telegram_chat_id))
        self._previous_positions: dict[str, TrackedPosition] = {}
        self._peak_portfolio_value: float = 0.0
        self._alert_history: list[Alert] = []
        self._engine_run_count: int = 0
        self._last_snapshot_track_s_value: float = 0.0
        self._peak_track_s_value: float = 0.0

    def _emit(self, alert: Alert) -> None:
        """알림을 모든 채널에 발송."""
        if not self.config.enabled:
            return
        self._alert_history.append(alert)
        for ch in self.channels:
            try:
                ch.send(alert)
            except Exception as exc:
                logger.warning("Channel %s failed: %s", type(ch).__name__, exc)

    def check_and_alert(
        self,
        snapshot: PortfolioSnapshot,
        model_auc: float | None = None,
        oof_coverage: float | None = None,
    ) -> list[Alert]:
        """Position 스냅샷을 검사하고 알림이 필요한 항목 발송. 반환: 발송된 알림 리스트."""
        if not self.config.enabled:
            return []
        emitted: list[Alert] = []
        th = self.config.thresholds

        # Track portfolio peak for drawdown detection
        current_total = snapshot.total_position_value
        if current_total > self._peak_portfolio_value:
            self._peak_portfolio_value = current_total

        # 1. STOP_APPROACHING
        for ticker in snapshot.stop_approaching_tickers:
            alert = Alert(
                alert_type=ALERT_TYPE_STOP_APPROACHING,
                ticker=ticker,
                track="S",
                priority=AlertPriority.CRITICAL,
                message=f"🚨 {ticker} STOP 접근 중 — 即時 확인 필요",
                metadata={"ticker": ticker, "track": "S"},
            )
            self._emit(alert)
            emitted.append(alert)

        # 2. TP_APPROACHING
        for ticker in snapshot.tp_approaching_tickers:
            alert = Alert(
                alert_type=ALERT_TYPE_TP_APPROACHING,
                ticker=ticker,
                track="S",
                priority=AlertPriority.HIGH,
                message=f"🟢 {ticker} TP2 접근 중 — 利確 준비",
                metadata={"ticker": ticker},
            )
            self._emit(alert)
            emitted.append(alert)

        # 3. EXPOSURE_WARNING
        if snapshot.total_exposure > 0 and snapshot.total_position_value > 0:
            exposure_ratio = snapshot.total_position_value / snapshot.total_exposure if snapshot.total_exposure > 0 else 0
            # total_exposure == total_position_value in this context
            # We check against max_exposure_pct with total_capital assumption of 100k
            assumed_capital = 100_000.0
            exposure_pct = snapshot.total_position_value / assumed_capital
            if exposure_pct > th.max_exposure_pct:
                alert = Alert(
                    alert_type=ALERT_TYPE_EXPOSURE_WARNING,
                    ticker=None,
                    track=None,
                    priority=AlertPriority.CRITICAL,
                    message=f"⚠️ 노출 비율 초과: {exposure_pct:.1%} (최대 {th.max_exposure_pct:.1%})",
                    metadata={"exposure_pct": exposure_pct, "max_exposure_pct": th.max_exposure_pct},
                )
                self._emit(alert)
                emitted.append(alert)

        # 4. DRAWDOWN_ALERT (Track-S drawdown from peak Track-S value)
        # Only check after first full run
        if self._engine_run_count > 0 and snapshot.track_s_value > 0:
            if snapshot.track_s_value > self._peak_track_s_value:
                self._peak_track_s_value = snapshot.track_s_value
            drawdown = (self._peak_track_s_value - snapshot.track_s_value) / self._peak_track_s_value if self._peak_track_s_value > 0 else 0.0
            if drawdown > th.track_s_drawdown_alert_pct:
                alert = Alert(
                    alert_type=ALERT_TYPE_DRAWDOWN_ALERT,
                    ticker=None,
                    track="S",
                    priority=AlertPriority.HIGH,
                    message=f"📉 Track-S 드로우다운: {drawdown:.2%} (최대 {th.track_s_drawdown_alert_pct:.2%})",
                    metadata={"drawdown_pct": drawdown, "peak_value": self._peak_track_s_value, "current_value": snapshot.track_s_value},
                )
                self._emit(alert)
                emitted.append(alert)
        elif snapshot.track_s_value > 0:
            # First run: initialize peak
            self._peak_track_s_value = max(self._peak_track_s_value, snapshot.track_s_value)

        # 5. POSITION_CLOSED events — detect from status changes
        for pos_dict in snapshot.positions:
            ticker = pos_dict["ticker"]
            prev = self._previous_positions.get(ticker)
            if prev and prev.status not in (PositionStatus.OPEN.value, PositionStatus.UNINITIALIZED.value, PositionStatus.STOP_APPROACHING.value, PositionStatus.TP_APPROACHING.value):
                continue  # already closed
            current_status = pos_dict["status"]
            if current_status in (PositionStatus.CLOSED_BY_STOP.value, PositionStatus.CLOSED_BY_TP1.value, PositionStatus.CLOSED_BY_TP2.value, PositionStatus.CLOSED_BY_TP2.value, PositionStatus.MANUAL_CLOSE.value):
                close_reason = pos_dict.get("close_reason", "unknown")
                emoji = "🔴" if "STOP" in current_status else "🟢"
                alert = Alert(
                    alert_type=ALERT_TYPE_POSITION_CLOSED,
                    ticker=ticker,
                    track=pos_dict.get("track"),
                    priority=AlertPriority.HIGH,
                    message=f"{emoji} {ticker} 포지션 종료 — {current_status} (사유: {close_reason})",
                    metadata=pos_dict,
                )
                self._emit(alert)
                emitted.append(alert)

        # 6. MODEL_QUALITY_WARNING
        if model_auc is not None and model_auc < th.model_auc_min:
            alert = Alert(
                alert_type=ALERT_TYPE_MODEL_QUALITY_WARNING,
                ticker=None,
                track=None,
                priority=AlertPriority.HIGH,
                message=f"⚠️ 모델 품질 저하 — AUC: {model_auc:.3f} (최소: {th.model_auc_min:.3f})",
                metadata={"model_auc": model_auc, "min_auc": th.model_auc_min},
            )
            self._emit(alert)
            emitted.append(alert)

        if oof_coverage is not None and oof_coverage < th.model_oof_coverage_min:
            alert = Alert(
                alert_type=ALERT_TYPE_MODEL_QUALITY_WARNING,
                ticker=None,
                track=None,
                priority=AlertPriority.HIGH,
                message=f"⚠️ OOF 커버리지 저하 — {oof_coverage:.1%} (최소: {th.model_oof_coverage_min:.1%})",
                metadata={"oof_coverage": oof_coverage, "min_coverage": th.model_oof_coverage_min},
            )
            self._emit(alert)
            emitted.append(alert)

        # 7. DAILY_SUMMARY — every call is a refresh cycle
        # (suppress low-priority for now to avoid noise)
        # We track previous positions for next cycle
        self._previous_positions = {p["ticker"]: self._pos_from_dict(p) for p in snapshot.positions}
        self._engine_run_count += 1
        return emitted

    def _pos_from_dict(self, d: dict) -> TrackedPosition:
        """dict에서 TrackedPosition 복원 (for state tracking)."""
        return TrackedPosition(
            ticker=d["ticker"],
            track=d.get("track", "S"),
            entry_date=d.get("entry_date", ""),
            entry_price=d.get("entry_price", 0.0),
            quantity=d.get("quantity", 0),
            stop=d.get("stop", 0.0),
            tp1=d.get("tp1", 0.0),
            tp2=d.get("tp2", 0.0),
            status=d.get("status", PositionStatus.UNINITIALIZED.value),
            current_price=d.get("current_price", 0.0),
        )

    def alert_history(self, limit: int = 100) -> list[Alert]:
        return self._alert_history[-limit:]


def create_default_config(output_path: str | Path | None = None) -> AlertConfig:
    """기본 알림 설정 파일 생성."""
    config = AlertConfig()
    if output_path:
        config.to_file(output_path)
    return config


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Alert Engine — Stage 2")
    parser.add_argument("--config", type=str, default="config/alerts.json", help="Alert config JSON path")
    parser.add_argument("--portfolio-json", type=str, default=None, help="Load portfolio snapshot from JSON")
    parser.add_argument("--watch", action="store_true", help="Watch mode — check periodically")
    parser.add_argument("--interval", type=int, default=300, help="Refresh interval in seconds")
    parser.add_argument("--model-auc", type=float, default=None, help="Model AUC for quality check")
    parser.add_argument("--oof-coverage", type=float, default=None, help="OOF coverage for quality check")
    args = parser.parse_args()

    config = AlertConfig.from_file(args.config) if Path(args.config).exists() else AlertConfig()
    engine = AlertEngine(config)

    if args.portfolio_json:
        import tempfile
        from .position_tracker import load_positions_from_recommendation_json, refresh_positions, PortfolioSnapshot

        positions = load_positions_from_recommendation_json(args.portfolio_json)
        positions = refresh_positions(positions)
        snapshot = PortfolioSnapshot.from_positions(positions)
    else:
        from datetime import datetime, timezone
        from .position_tracker import TrackedPosition, PortfolioSnapshot

        positions = [
            TrackedPosition(ticker="AAPL", track="S", entry_date="2026-05-01", entry_price=185.0, quantity=10, stop=177.0, tp1=194.0, tp2=203.5),
            TrackedPosition(ticker="MSFT", track="L", entry_date="2026-05-01", entry_price=415.0, quantity=5, stop=375.0, tp1=450.0, tp2=498.0),
        ]
        for p in positions:
            p.mark_open(current_price=p.entry_price, timestamp_utc=datetime.now(timezone.utc).isoformat())
        snapshot = PortfolioSnapshot.from_positions(positions)

    if args.watch:
        print(f"Watching alerts, refreshing every {args.interval}s. Ctrl+C to stop.")
        import time

        while True:
            if args.portfolio_json:
                positions = load_positions_from_recommendation_json(args.portfolio_json)
                positions = refresh_positions(positions)
                snapshot = PortfolioSnapshot.from_positions(positions)
            emitted = engine.check_and_alert(snapshot, model_auc=args.model_auc, oof_coverage=args.oof_coverage)
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] Checked — {len(emitted)} alerts emitted")
            time.sleep(args.interval)
    else:
        emitted = engine.check_and_alert(snapshot, model_auc=args.model_auc, oof_coverage=args.oof_coverage)
        print(f"Alert check complete — {len(emitted)} alerts emitted")
        if emitted:
            for a in emitted:
                print(f"  {a.priority} {a.alert_type}: {a.message[:80]}")