"""OpenAI-powered event shock gate for stock signal conflict detection.

Detects high-impact market events (HBM, AI memory, customer shipments, analyst
upgrades) via OpenAI's gpt-4o-mini and flags SELL signals that conflict with a
confirmed positive catalyst.

Design principles
-----------------
* OpenAI is an **optional** dependency — when unavailable or errored, the gate
  returns a neutral ``DEGRADED_NO_EVENT_DATA`` result and never blocks inference.
* The gate can only **block** or **downgrade** a signal; it cannot emit a BUY.
* ``new_capital_allowed`` and ``broker_order_execution`` are always ``False``.

Structured output schema (Pydantic, gpt-4o-mini ``response_format``)::

    {
        "category": "HBM",           # one of EVENT_CATEGORIES or "NONE"
        "sentiment_score": 0.87      # float 0..1
    }
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVENT_CATEGORIES: frozenset[str] = frozenset(
    {"HBM", "AI_MEMORY", "CUSTOMER_SHIPMENT", "TARGET_PRICE_UPGRADE", "DISCLOSURE"}
)

DEFAULT_SENTIMENT_THRESHOLD: float = 0.75
DEFAULT_MODEL: str = "gpt-4o-mini"

# Readiness statuses
STATUS_PASS = "PASS"
STATUS_AMBER_CONFLICT = "AMBER_EVENT_SIGNAL_CONFLICT"
STATUS_DEGRADED = "DEGRADED_NO_EVENT_DATA"


# ---------------------------------------------------------------------------
# Internal structured-output schema
# ---------------------------------------------------------------------------


@dataclass
class _EventAnalysis:
    """Result returned by OpenAI event classification."""

    category: str
    sentiment_score: float


def _build_prompt(ticker: str, news_title: str) -> list[dict[str, str]]:
    system = (
        "You are a financial event classifier. "
        "Given a news headline, classify the event into one of these categories: "
        "HBM, AI_MEMORY, CUSTOMER_SHIPMENT, TARGET_PRICE_UPGRADE, DISCLOSURE, NONE. "
        "Also provide a sentiment_score between 0.0 (very negative) and 1.0 (very positive). "
        "Respond ONLY with a JSON object: "
        '{"category": "<CATEGORY>", "sentiment_score": <float>}'
    )
    user = f"Ticker: {ticker}\nHeadline: {news_title}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _call_openai(client: Any, ticker: str, news_title: str) -> tuple[str, float]:
    """Call OpenAI and return (category, sentiment_score).

    Falls back to ``("NONE", 0.0)`` on any parse error.
    """
    import json

    messages = _build_prompt(ticker, news_title)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        max_tokens=64,
        temperature=0,
    )
    raw = response.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
        category = str(data.get("category", "NONE")).upper()
        sentiment = float(data.get("sentiment_score", 0.0))
        sentiment = max(0.0, min(1.0, sentiment))
    except (ValueError, KeyError, TypeError):
        logger.warning("openai_event_shock: failed to parse response: %s", raw)
        category, sentiment = "NONE", 0.0

    return category, sentiment


def _degraded_result() -> dict[str, Any]:
    return {
        "event_shock": False,
        "category": "NONE",
        "sentiment_score": 0.0,
        "readiness_status": STATUS_DEGRADED,
        "blocking_reasons": [],
        "new_capital_allowed": False,
        "broker_order_execution": False,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def check_event_shock(
    *,
    ticker: str,
    news_title: str,
    signal: str,
    openai_client: Any = None,
    sentiment_threshold: float = DEFAULT_SENTIMENT_THRESHOLD,
) -> dict[str, Any]:
    """Evaluate the OpenAI event shock gate for a single news headline.

    Parameters
    ----------
    ticker:
        The stock ticker (e.g. ``"005930.KS"``).
    news_title:
        A single headline to classify.
    signal:
        The current model signal (``"BUY"`` / ``"SELL"`` / ``"HOLD"``).
    openai_client:
        An instantiated ``openai.OpenAI`` client.  When ``None``, the function
        attempts to construct one from ``OPENAI_API_KEY``; if that also fails,
        degraded mode is returned.
    sentiment_threshold:
        Minimum sentiment score to treat as a positive shock (default 0.75).

    Returns
    -------
    dict with keys:
        ``event_shock`` bool,
        ``category`` str,
        ``sentiment_score`` float,
        ``readiness_status`` str,
        ``blocking_reasons`` list[str],
        ``new_capital_allowed`` bool (always False),
        ``broker_order_execution`` bool (always False).
    """
    if openai_client is None:
        try:
            from openai import OpenAI  # type: ignore[import]

            api_key = os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                return _degraded_result()
            openai_client = OpenAI(api_key=api_key)
        except ImportError:
            return _degraded_result()
        except Exception as exc:
            logger.warning("openai_event_shock: client init failed: %s", exc)
            return _degraded_result()

    try:
        category, sentiment = _call_openai(openai_client, ticker, news_title)
    except Exception as exc:
        logger.warning("openai_event_shock: API call failed: %s", exc)
        return _degraded_result()

    event_shock = category in EVENT_CATEGORIES and sentiment >= sentiment_threshold

    blocking_reasons: list[str] = []
    if event_shock and signal == "SELL":
        blocking_reasons.append("EVENT_SHOCK_CONFLICTS_WITH_SELL")

    readiness_status = STATUS_AMBER_CONFLICT if blocking_reasons else STATUS_PASS

    return {
        "event_shock": event_shock,
        "category": category,
        "sentiment_score": round(sentiment, 4),
        "readiness_status": readiness_status,
        "blocking_reasons": blocking_reasons,
        "new_capital_allowed": False,
        "broker_order_execution": False,
    }
