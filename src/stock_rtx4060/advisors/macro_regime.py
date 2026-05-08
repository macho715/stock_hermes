"""Macro regime classifier.

Pulls a small panel of macro indicators (FRED ``T10Y2Y``, ``VIXCLS``,
``DTWEXBGS`` for the dollar index, plus equity / FX overlays from the
caller's context) and asks Claude to label the regime.

When the data is unavailable the agent returns the neutral mapping
(``score = 0.0``, ``confidence = 0.0``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .base import AdvisoryOutput
from .claude_client import ClaudeClient
from .news_sentiment import _clip, _parse_advisor_json
from .prompts import load_prompt, render

logger = logging.getLogger(__name__)

REGIME_TO_SCORE = {"risk_on": 0.30, "neutral": 0.0, "risk_off": -0.30}


@dataclass
class MacroRegimeAgent:
    name: str = "macro_regime"
    client: ClaudeClient = field(default_factory=ClaudeClient)
    panel_fetcher: Any = None  # callable() -> dict, override in tests

    async def analyze(self, ticker: str, context: dict[str, Any]) -> AdvisoryOutput:
        as_of = datetime.now(timezone.utc).isoformat(timespec="seconds")
        panel = self._build_panel(context)
        if not panel:
            return AdvisoryOutput(
                agent=self.name,
                ticker=ticker,
                score=0.0,
                confidence=0.0,
                rationale="macro data unavailable",
                citations=[],
                prompt_hash="",
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
            )

        system_tpl = load_prompt("macro_system")
        user_tpl = load_prompt("macro_user")
        rendered_user = render(user_tpl, {"as_of": as_of, "panel": panel})

        result = await self.client.acall(
            system=system_tpl,
            messages=[{"role": "user", "content": rendered_user}],
        )
        parsed = _parse_advisor_json(result.text)
        regime = str(parsed.get("regime", "")).strip().lower()
        if regime not in REGIME_TO_SCORE:
            # the model may emit a score directly — fall back to that
            score = _clip(parsed.get("score", 0.0), -1.0, 1.0)
            regime = "risk_on" if score > 0.05 else "risk_off" if score < -0.05 else "neutral"
        else:
            llm_score = parsed.get("score")
            if llm_score is None:
                score = REGIME_TO_SCORE[regime]
            else:
                # Trust the LLM's number but clamp into the regime sign.
                clipped = _clip(llm_score, -1.0, 1.0)
                if regime == "risk_on":
                    score = max(REGIME_TO_SCORE[regime], clipped) if clipped > 0 else REGIME_TO_SCORE[regime]
                elif regime == "risk_off":
                    score = min(REGIME_TO_SCORE[regime], clipped) if clipped < 0 else REGIME_TO_SCORE[regime]
                else:
                    score = 0.0
        confidence = _clip(parsed.get("confidence", 0.5), 0.0, 1.0)
        rationale = str(parsed.get("rationale", regime))[:1024]
        citations = [str(c) for c in (parsed.get("citations") or list(panel.keys()))]
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

    # ------------------------------------------------------------------

    def _build_panel(self, context: dict[str, Any]) -> dict[str, Any]:
        injected = context.get("macro_panel")
        if isinstance(injected, dict) and injected:
            return dict(injected)
        if self.panel_fetcher is not None:
            try:
                panel = self.panel_fetcher()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("macro panel fetch failed: %s", exc)
                return {}
            if isinstance(panel, dict):
                return panel
        return self._fetch_default_panel()

    def _fetch_default_panel(self) -> dict[str, Any]:  # pragma: no cover - network
        try:
            import pandas_datareader.data as pdr  # type: ignore[import-not-found]
        except ImportError:
            return {}
        try:
            t10y2y = float(pdr.DataReader("T10Y2Y", "fred").iloc[-1, 0])
            vix = float(pdr.DataReader("VIXCLS", "fred").iloc[-1, 0])
            dxy = float(pdr.DataReader("DTWEXBGS", "fred").iloc[-1, 0])
        except Exception as exc:
            logger.debug("FRED fetch failed: %s", exc)
            return {}
        return {
            "t10y2y": t10y2y,
            "vix": vix,
            "dxy": dxy,
            "kospi_trend_pct": None,
            "spy_trend_pct": None,
            "krwusd": None,
        }


__all__ = ["MacroRegimeAgent", "REGIME_TO_SCORE"]
