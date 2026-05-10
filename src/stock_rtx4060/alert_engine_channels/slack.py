"""Slack webhook channel for the alert engine.

Uses :mod:`slack_sdk` when available, falls back to plain ``httpx`` POST
otherwise.  Implements the :class:`stock_rtx4060.alert_engine.AlertChannel`
Protocol (``send(alert) -> bool``).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type-only use
    from ..alert_engine import Alert

logger = logging.getLogger(__name__)

_PRIORITY_EMOJI = {
    "CRITICAL": ":rotating_light:",
    "HIGH": ":warning:",
    "MEDIUM": ":bell:",
    "LOW": ":information_source:",
}

_PRIORITY_COLOR = {
    "CRITICAL": "#d62728",
    "HIGH": "#ff7f0e",
    "MEDIUM": "#1f77b4",
    "LOW": "#2ca02c",
}


def _build_payload(alert: Alert) -> dict[str, Any]:
    """Construct the Slack webhook payload (Incoming Webhooks spec).

    See https://api.slack.com/messaging/webhooks for the schema. We include the
    ``text`` fallback (required by the spec) plus a richer ``attachments`` block
    so a coloured side-bar reflects the priority level.
    """
    emoji = _PRIORITY_EMOJI.get(alert.priority, ":mega:")
    color = _PRIORITY_COLOR.get(alert.priority, "#808080")

    fallback_lines = [
        f"{emoji} *[{alert.priority}] {alert.alert_type}*",
        alert.message,
    ]
    if alert.ticker:
        fallback_lines.append(f"Ticker: {alert.ticker} ({alert.track or '-'})")
    fallback_lines.append(f"At {alert.timestamp_utc[:19]}Z")
    text = "\n".join(fallback_lines)

    fields: list[dict[str, Any]] = []
    if alert.ticker:
        fields.append({"title": "Ticker", "value": str(alert.ticker), "short": True})
    if alert.track:
        fields.append({"title": "Track", "value": str(alert.track), "short": True})
    fields.append({"title": "Priority", "value": str(alert.priority), "short": True})
    fields.append({"title": "Type", "value": str(alert.alert_type), "short": True})

    payload: dict[str, Any] = {
        "text": text,
        "attachments": [
            {
                "color": color,
                "title": f"{alert.alert_type}",
                "text": alert.message,
                "fields": fields,
                "ts": None,  # Slack accepts numeric epoch; leaving null is allowed
                "footer": "stock_rtx4060 alert_engine",
            }
        ],
    }
    return payload


class SlackWebhookChannel:
    """Slack Incoming Webhook alert channel.

    Parameters
    ----------
    webhook_url:
        Full Slack incoming webhook URL.
    enabled:
        Master toggle. When ``False``, ``send`` returns ``False`` immediately.
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(self, webhook_url: str, *, enabled: bool = True, timeout: float = 10.0):
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.timeout = timeout

    def send(self, alert: Alert) -> bool:
        if not self.enabled or not self.webhook_url:
            return False
        payload = _build_payload(alert)
        # Try slack_sdk first if available; otherwise fall through to httpx.
        try:
            from slack_sdk.webhook import WebhookClient  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001 - optional dep
            return self._send_via_httpx(payload)
        try:
            client = WebhookClient(self.webhook_url)
            resp = client.send(text=payload["text"], attachments=payload.get("attachments"))
            status = int(getattr(resp, "status_code", 0) or 0)
            return 200 <= status < 300
        except Exception as exc:  # noqa: BLE001 - keep alert pipeline alive
            logger.warning("Slack webhook (slack_sdk) failed: %s", exc)
            return False

    def _send_via_httpx(self, payload: dict[str, Any]) -> bool:
        try:
            import httpx
        except Exception as exc:  # noqa: BLE001 - httpx is part of base deps but stay safe
            logger.warning("httpx unavailable for Slack webhook fallback: %s", exc)
            return False
        try:
            resp = httpx.post(self.webhook_url, json=payload, timeout=self.timeout)
            return 200 <= resp.status_code < 300
        except Exception as exc:  # noqa: BLE001
            logger.warning("Slack webhook (httpx) failed: %s", exc)
            return False


__all__ = ["SlackWebhookChannel"]
