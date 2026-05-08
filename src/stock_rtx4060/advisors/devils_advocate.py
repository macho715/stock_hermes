"""Devil's advocate agent.

The contract: this advisor *only* surfaces risks.  The output score is
clamped to ``[-1, 0]`` — even an apparently bullish LLM response is
floored to zero.  The agent never confirms a long thesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .base import AdvisoryOutput
from .claude_client import ClaudeClient
from .news_sentiment import _clip, _parse_advisor_json
from .prompts import load_prompt, render


@dataclass
class DevilsAdvocateAgent:
    name: str = "devils_advocate"
    client: ClaudeClient = field(default_factory=ClaudeClient)

    async def analyze(self, ticker: str, context: dict[str, Any]) -> AdvisoryOutput:
        as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")
        factors = dict(context.get("factors") or {})
        shap = dict(context.get("shap") or {})
        bull_summary = str(context.get("bull_summary") or "")

        system_tpl = load_prompt("devils_system")
        user_tpl = load_prompt("devils_user")
        rendered_user = render(
            user_tpl,
            {"ticker": ticker, "as_of": as_of, "factors": factors, "shap": shap, "bull_summary": bull_summary},
        )

        result = await self.client.acall(
            system=system_tpl,
            messages=[{"role": "user", "content": rendered_user}],
        )
        parsed = _parse_advisor_json(result.text)
        # Score is clamped to [-1, 0]: a contrarian agent never confirms.
        raw_score = _clip(parsed.get("score", 0.0), -1.0, 1.0)
        score = min(0.0, raw_score)
        confidence = _clip(parsed.get("confidence", 0.0), 0.0, 1.0)
        rationale = str(parsed.get("rationale", ""))[:1024]
        citations = [str(c) for c in (parsed.get("citations") or [])]
        return AdvisoryOutput(
            agent=self.name,
            ticker=ticker,
            score=float(score),
            confidence=float(confidence),
            rationale=rationale,
            citations=citations,
            prompt_hash=result.prompt_hash,
            tokens_in=int(result.tokens_in),
            tokens_out=int(result.tokens_out),
            cost_usd=float(result.cost_usd),
        )


__all__ = ["DevilsAdvocateAgent"]
