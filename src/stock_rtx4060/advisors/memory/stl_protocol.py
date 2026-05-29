"""STL Protocol — Sentiment-To-Logic proposition extraction.

Converts the free-form ``rationale`` text from ``NewsSentimentAgent`` into
a structured logical proposition of the form:

    "IF <condition> THEN <direction> WITH <confidence_float>"

Examples
--------
Input rationale: "VIX spiked above 25; earnings season fears dominate"
Output: "IF VIX>25 THEN bearish WITH 0.7"

Extraction strategy:
1. Try to parse a JSON ``"proposition"`` key from the rationale if the
   model already formatted one (preferred path).
2. Fall back to a regex scan for the canonical phrase pattern.
3. Return empty string on failure — callers must handle gracefully.

No LLM call is made; extraction is purely local regex / JSON parsing.
"""
from __future__ import annotations

import json
import re

# Canonical format accepted by the parser
_PROPOSITION_RE = re.compile(
    r"""IF\s+(?P<cond>[^T]+?)\s+THEN\s+(?P<dir>bullish|bearish|neutral)\s+WITH\s+(?P<conf>[01]?\.\d+)""",
    re.IGNORECASE,
)

# JSON key names we look for inside the rationale when it embeds JSON
_JSON_KEYS = ("proposition", "stl_proposition", "logical_proposition")


class STLProtocol:
    """Extracts an IF-THEN-WITH proposition from an advisor rationale string."""

    @staticmethod
    def extract(rationale: str) -> str:
        """Return a canonical proposition string or empty string on failure.

        Parameters
        ----------
        rationale:
            Free-form or JSON-embedded text from ``NewsSentimentAgent``.
        """
        if not rationale:
            return ""

        # 1. Try JSON extraction
        prop = _extract_from_json(rationale)
        if prop:
            return prop

        # 2. Try regex scan
        m = _PROPOSITION_RE.search(rationale)
        if m:
            cond = m.group("cond").strip()
            direction = m.group("dir").lower()
            conf = m.group("conf")
            return f"IF {cond} THEN {direction} WITH {conf}"

        return ""

    @staticmethod
    def validate(proposition: str) -> bool:
        """Return True if *proposition* matches the canonical IF-THEN-WITH format."""
        return bool(_PROPOSITION_RE.match(proposition.strip()))


def _extract_from_json(text: str) -> str:
    """Try to parse *text* as JSON and extract a known proposition key."""
    # find JSON block (possibly embedded in markdown)
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        return ""
    try:
        data = json.loads(json_match.group())
    except (json.JSONDecodeError, ValueError):
        return ""
    for key in _JSON_KEYS:
        val = data.get(key, "")
        if val and isinstance(val, str):
            return str(val).strip()
    return ""


__all__ = ["STLProtocol"]
