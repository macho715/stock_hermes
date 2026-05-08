"""Optional alert channel implementations (Slack/Discord webhooks).

Each channel implements the :class:`stock_rtx4060.alert_engine.AlertChannel`
Protocol (a duck-typed ``send(alert) -> bool``).  Heavy/optional dependencies
(``slack_sdk``, ``discord-webhook``) are imported lazily so ``import``-time of
this package never fails when they are absent — the channels fall back to a
plain ``httpx`` POST in that case.
"""

from __future__ import annotations

from .discord import DiscordWebhookChannel
from .slack import SlackWebhookChannel

__all__ = ["SlackWebhookChannel", "DiscordWebhookChannel"]
