"""OpenAI API client for NotebookLM News Intelligence Layer.

Uses OpenAI Responses API + Structured Outputs to produce a stable
``notebook_analysis`` JSON that STOCKPRED's LLM advisor can consume.

Feature flag: ``LLM_ADVISOR_PROVIDER=openai`` (default: anthropic/minimax)
Model: ``OPENAI_ADVISOR_MODEL`` (default: gpt-4o)

Why Responses API + Structured Outputs:
- Responses API is the latest unified interface for model invocation,
  tool/function calling, and external data integration.
- Structured Outputs enforces JSON Schema compliance — critical for
  dashboard stability where free-form text is not acceptable.

Usage:
    from stock_rtx4060.advisors.openai_client import (
        OpenAINewsAnalyzer, NotebookAnalysis
    )
    analyzer = OpenAINewsAnalyzer()
    result: NotebookAnalysis = analyzer.analyze(
        ticker="AAPL", market="US",
        headlines=["Apple reports record Q1...", "iPhone sales beat estimates..."],
        notebook_summary="NotebookLM: AI demand remains strong..."
    )
"""

from __future__ import annotations

import logging
import os
from typing import Any

_LOGGER = logging.getLogger("advisors.openai_client")

# ---------------------------------------------------------------------------
# Pydantic schema for notebook_analysis (Structured Output enforcement)
# ---------------------------------------------------------------------------
try:
    from pydantic import BaseModel, Field

    class NotebookAnalysis(BaseModel):
        """Structured output schema for NotebookLM + OpenAI joint stock analysis."""

        summary: str = Field(
            description="2-3문장 종합 뉴스 분석. 호재/악재 핵심만."
        )
        bullish_factors: list[str] = Field(
            description="호재 요인 목록 (1~5개). 각각 한 문장."
        )
        bearish_factors: list[str] = Field(
            description="악재 요인 목록 (0~5개). 각각 한 문장."
        )
        ticker_relevance: float = Field(
            ge=0.0, le=1.0,
            description="뉴스가 해당 종목과 얼마나 직접 관련되는지 (0=무관, 1=직접관련)"
        )
        sentiment_score: float = Field(
            ge=-1.0, le=1.0,
            description="종합 감성 점수 (-1=강한 하락, 0=중립, +1=강한 상승)"
        )
        market_impact: str = Field(
            description="예상 시장 영향: LOW|MEDIUM|MEDIUM_HIGH|HIGH|CRITICAL"
        )
        confidence: float = Field(
            ge=0.0, le=1.0,
            description="분석 신뢰도 (뉴스 수, 관련성 기반)"
        )
        recommended_llm_instruction: str = Field(
            description=(
                "stock_1901 LLM advisor에게 전달할 지침. "
                "예: '긍정 편향으로 처리하되 모멘텀 지표 교차 검증 권장'"
            )
        )
        source_ids: list[str] = Field(
            default_factory=list,
            description="분석에 사용된 NotebookLM source_id 목록"
        )

    _PYDANTIC_AVAILABLE = True

except ImportError:  # pragma: no cover
    NotebookAnalysis = None  # type: ignore[assignment, misc]
    _PYDANTIC_AVAILABLE = False


# ---------------------------------------------------------------------------
# OpenAI Responses API client
# ---------------------------------------------------------------------------

class OpenAINewsAnalyzer:
    """Analyzes stock news using OpenAI Responses API + Structured Outputs.

    Produces a ``NotebookAnalysis`` object that is injected into the
    STOCKPRED advisor context as ``context["notebook_analysis"]``.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        self._model = model or os.environ.get("OPENAI_ADVISOR_MODEL", "gpt-4o")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError as exc:
                raise RuntimeError(
                    "openai package is not installed. "
                    "Run: pip install openai>=2.0"
                ) from exc
        return self._client

    def analyze(
        self,
        ticker: str,
        market: str,
        headlines: list[str],
        notebook_summary: str = "",
        source_ids: list[str] | None = None,
        company_name: str = "",
    ) -> dict[str, Any]:
        """Run OpenAI Structured Output analysis and return notebook_analysis dict.

        Parameters
        ----------
        ticker:
            Stock ticker symbol (e.g. "AAPL", "005930").
        market:
            Market identifier ("US" or "KRX").
        headlines:
            List of raw news headlines collected from RSS/scraper.
        notebook_summary:
            Optional summary text already extracted from NotebookLM.
        source_ids:
            NotebookLM source_ids for traceability.
        company_name:
            Company display name for better context.

        Returns
        -------
        dict matching notebook_analysis JSON schema.
        Fallback dict with ``error`` key if OpenAI call fails.
        """
        if not self._api_key:
            _LOGGER.warning("[OpenAI] OPENAI_API_KEY not set — skipping analysis")
            return self._fallback(ticker, "no_api_key")

        if not headlines and not notebook_summary:
            _LOGGER.info("[OpenAI] no input for %s — returning neutral", ticker)
            return self._neutral(ticker, source_ids or [])

        prompt = self._build_prompt(
            ticker, market, company_name, headlines, notebook_summary
        )

        try:
            return self._call_responses_api(prompt, ticker, source_ids or [])
        except Exception as exc:
            _LOGGER.error("[OpenAI] analysis failed for %s: %s", ticker, exc)
            return self._fallback(ticker, str(exc))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        ticker: str,
        market: str,
        company_name: str,
        headlines: list[str],
        notebook_summary: str,
    ) -> str:
        name_ctx = f" ({company_name})" if company_name else ""
        nb_ctx = (
            f"\n\nNotebookLM 사전 분석:\n{notebook_summary}"
            if notebook_summary
            else ""
        )
        headline_text = "\n".join(f"- {h}" for h in headlines[:10])
        return (
            f"종목: {ticker}{name_ctx} ({market} 시장)\n\n"
            f"최신 뉴스 헤드라인:\n{headline_text}"
            f"{nb_ctx}\n\n"
            f"위 정보를 바탕으로 {ticker} 종목의 투자 관련 뉴스 영향을 분석하라. "
            f"분석은 투자 판단 참고 정보이며 실제 매매 지시가 아님을 전제한다."
        )

    def _call_responses_api(
        self, prompt: str, ticker: str, source_ids: list[str]
    ) -> dict[str, Any]:
        """Call OpenAI Responses API with Pydantic Structured Outputs."""
        client = self._get_client()

        if not _PYDANTIC_AVAILABLE or NotebookAnalysis is None:
            raise RuntimeError("pydantic is required for Structured Outputs")

        _LOGGER.info("[OpenAI] calling %s for %s", self._model, ticker)
        response = client.responses.parse(
            model=self._model,
            instructions=(
                "당신은 주식 뉴스 분석 전문가다. "
                "제공된 뉴스를 바탕으로 종목 투자 영향을 분석하고 "
                "JSON 형식으로 구조화된 결과를 반환한다. "
                "투자 판단 참고 정보이며 매매 지시가 아님을 항상 전제한다."
            ),
            input=prompt,
            text_format=NotebookAnalysis,
        )

        parsed: NotebookAnalysis = response.output_parsed
        result = parsed.model_dump()
        result["source_ids"] = source_ids
        result["analysis_source"] = "openai_api"
        result["provider"] = "openai"
        result["model"] = self._model
        result["error"] = None
        _LOGGER.info(
            "[OpenAI] %s: sentiment=%.2f impact=%s confidence=%.2f",
            ticker, result["sentiment_score"],
            result["market_impact"], result["confidence"]
        )
        return result

    @staticmethod
    def _neutral(ticker: str, source_ids: list[str]) -> dict[str, Any]:
        return {
            "summary": f"{ticker} 관련 분석 가능한 뉴스가 없습니다.",
            "bullish_factors": [],
            "bearish_factors": [],
            "ticker_relevance": 0.0,
            "sentiment_score": 0.0,
            "market_impact": "LOW",
            "confidence": 0.0,
            "recommended_llm_instruction": "뉴스 없음. 기술지표 중심 판단 권장.",
            "source_ids": source_ids,
            "error": None,
        }

    @staticmethod
    def _fallback(ticker: str, reason: str) -> dict[str, Any]:
        return {
            "summary": "",
            "bullish_factors": [],
            "bearish_factors": [],
            "ticker_relevance": 0.0,
            "sentiment_score": 0.0,
            "market_impact": "LOW",
            "confidence": 0.0,
            "recommended_llm_instruction": "",
            "source_ids": [],
            "error": f"openai_analysis_failed:{reason}",
        }


# ---------------------------------------------------------------------------
# Provider factory — integrates with existing ClaudeClient pattern
# ---------------------------------------------------------------------------

def is_openai_provider() -> bool:
    """Return True when LLM_ADVISOR_PROVIDER=openai."""
    return os.environ.get("LLM_ADVISOR_PROVIDER", "anthropic").strip().lower() == "openai"


def get_openai_analyzer() -> OpenAINewsAnalyzer | None:
    """Return OpenAINewsAnalyzer when configured, else None."""
    if not is_openai_provider():
        return None
    return OpenAINewsAnalyzer()
