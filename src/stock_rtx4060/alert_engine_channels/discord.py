"""Discord webhook channel for the alert engine.

Uses :mod:`discord_webhook` when available, falls back to plain ``httpx`` POST
otherwise.  Implements :class:`stock_rtx4060.alert_engine.AlertChannel`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type-only import
    from ..alert_engine import Alert

logger = logging.getLogger(__name__)

# Discord embed colours are 24-bit ints (0xRRGGBB).
_PRIORITY_COLOR = {
    "CRITICAL": 0xD62728,
    "HIGH": 0xFF7F0E,
    "MEDIUM": 0x1F77B4,
    "LOW": 0x2CA02C,
}

_PRIORITY_EMOJI = {
    "CRITICAL": ":rotating_light:",
    "HIGH": ":warning:",
    "MEDIUM": ":bell:",
    "LOW": ":information_source:",
}


def _build_payload(alert: "Alert") -> dict[str, Any]:
    """Construct the Discord webhook payload.

    Discord webhook spec — see https://discord.com/developers/docs/resources/webhook#execute-webhook
    A webhook execute body accepts ``content`` (max 2000 chars) and ``embeds``
    (rich block array). We populate both for client compatibility.
    """
    emoji = _PRIORITY_EMOJI.get(alert.priority, ":mega:")
    color = _PRIORITY_COLOR.get(alert.priority, 0x808080)

    content = f"{emoji} **[{alert.priority}] {alert.alert_type}** — {alert.message}"
    if len(content) > 1900:  # leave headroom for the 2000-char Discord limit
        content = content[:1897] + "..."

    fields: list[dict[str, Any]] = []
    if alert.ticker:
        fields.append({"name": "Ticker", "value": str(alert.ticker), "inline": True})
    if alert.track:
        fields.append({"name": "Track", "value": str(alert.track), "inline": True})
    fields.append({"name": "Priority", "value": str(alert.priority), "inline": True})
    fields.append({"name": "Type", "value": str(alert.alert_type), "inline": True})

    embed: dict[str, Any] = {
        "title": str(alert.alert_type),
        "description": alert.message,
        "color": color,
        "timestamp": alert.timestamp_utc,
        "fields": fields,
        "footer": {"text": "stock_rtx4060 alert_engine"},
    }
    return {"content": content, "embeds": [embed]}


class DiscordWebhookChannel:
    """Discord webhook alert channel.

    Parameters
    ----------
    webhook_url:
        Full Discord webhook URL (``https://discord.com/api/webhooks/...``).
    enabled:
        Master toggle.
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(self, webhook_url: str, *, enabled: bool = True, timeout: float = 10.0):
        self.webhook_url = webhook_url
        self.enabled = enabled
        self.timeout = timeout

    def send(self, alert: "Alert") -> bool:
        if not self.enabled or not self.webhook_url:
            return False
        payload = _build_payload(alert)
        try:
            from discord_webhook import DiscordEmbed, DiscordWebhook  # type: ignore[import-not-found]
        except Exception:  # noqa: BLE001 - optional dep
            return self._send_via_httpx(payload)
        try:
            webhook = DiscordWebhook(url=self.webhook_url, content=payload.get("content", ""))
            for embed_data in payload.get("embeds", []):
                embed = DiscordEmbed(
                    title=embed_data.get("title", ""),
                    description=embed_data.get("description", ""),
                    color=embed_data.get("color", 0x808080),
                )
                for f in embed_data.get("fields", []):
                    embed.add_embed_field(name=f["name"], value=f["value"], inline=f.get("inline", True))
                webhook.add_embed(embed)
            resp = webhook.execute()
            status = int(getattr(resp, "status_code", 0) or 0)
            return 200 <= status < 300
        except Exception as exc:  # noqa: BLE001
            logger.warning("Discord webhook (discord_webhook) failed: %s", exc)
            return False

    def _send_via_httpx(self, payload: dict[str, Any]) -> bool:
        try:
            import httpx
        except Exception as exc:  # noqa: BLE001
            logger.warning("httpx unavailable for Discord webhook fallback: %s", exc)
            return False
        try:
            resp = httpx.post(self.webhook_url, json=payload, timeout=self.timeout)
            return 200 <= resp.status_code < 300
        except Exception as exc:  # noqa: BLE001
            logger.warning("Discord webhook (httpx) failed: %s", exc)
            return False


__all__ = ["DiscordWebhookChannel"]
