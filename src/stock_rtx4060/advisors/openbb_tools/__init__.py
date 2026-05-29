"""OpenBB tool-use integration for LLM advisors.

Exposes OpenBB data endpoints as Anthropic tool_use functions so advisors
can query real-time market data during inference.

Feature flag: ``OPENBB_TOOLS_ENABLED=true`` (default: false).
Graceful: all tools return ``{"status": "unavailable"}`` when openbb is not installed.
PIT guard: ``end_date`` is clamped to ``as_of`` to prevent look-ahead bias.
"""

from .agentic_loop import run_tool_loop
from .tool_executor import ToolExecutor
from .tool_schemas import (
    GET_COMPANY_NEWS,
    GET_FUNDAMENTAL_METRICS,
    GET_MACRO_INDICATORS,
    GET_PRICE_HISTORY,
    MACRO_TOOLS,
    NEWS_TOOLS,
)

__all__ = [
    "GET_PRICE_HISTORY",
    "GET_COMPANY_NEWS",
    "GET_FUNDAMENTAL_METRICS",
    "GET_MACRO_INDICATORS",
    "NEWS_TOOLS",
    "MACRO_TOOLS",
    "ToolExecutor",
    "run_tool_loop",
]
