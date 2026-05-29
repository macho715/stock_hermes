"""Base contracts for the advisor layer.

Two public symbols:

* :class:`AdvisoryOutput` — frozen dataclass returned by every agent.
* :class:`Advisor` — :class:`typing.Protocol` describing the async ``analyze``
  call.

The dataclass enforces the score / confidence ranges in ``__post_init__`` so
that downstream consumers (the orchestrator, the Black-Litterman bridge)
can rely on bounded values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AdvisoryOutput:
    """Single advisor verdict.

    Attributes
    ----------
    agent
        Human-readable name of the agent that produced the output.
    ticker
        Ticker symbol (e.g. ``"AAPL"``).
    score
        Sentiment / advisory score in ``[-1, +1]``.
    confidence
        Confidence in ``[0, 1]``.  ``0`` means "no opinion".
    rationale
        Free-form natural-language explanation.
    citations
        Source URLs / IDs supporting the rationale.
    prompt_hash
        SHA-256 of the rendered prompt — logged with every call so prompts
        are versioned and reproducible.
    tokens_in / tokens_out
        Total input / output tokens charged to the call.  Cache reads are
        included in ``tokens_in``.
    cost_usd
        Computed cost in USD (input + output, including cache pricing).
    """

    agent: str
    ticker: str
    score: float
    confidence: float
    rationale: str
    citations: list[str]
    prompt_hash: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    # [AMH Memory Layer — W4 FR-1] additive optional fields; default="" preserves
    # backward compatibility — all existing call-sites need not change.
    regime_label: str = ""           # "risk_on" | "neutral" | "risk_off" | ""
    logical_proposition: str = ""    # STL Protocol output (NewsSentiment agent only)

    def __post_init__(self) -> None:
        if not -1.0 <= float(self.score) <= 1.0:
            raise ValueError(f"score must be in [-1, +1], got {self.score!r}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence!r}")
        if int(self.tokens_in) < 0 or int(self.tokens_out) < 0:
            raise ValueError("token counts must be non-negative")
        if float(self.cost_usd) < 0.0:
            raise ValueError("cost_usd must be non-negative")


@runtime_checkable
class Advisor(Protocol):
    """Protocol every advisor agent must satisfy."""

    name: str

    async def analyze(self, ticker: str, context: dict[str, Any]) -> AdvisoryOutput: ...


__all__ = ["AdvisoryOutput", "Advisor"]
