"""Anthropic tool_use JSON schemas for OpenBB data endpoints.

Four tools are defined:
* ``get_price_history``       — OHLCV daily price data
* ``get_company_news``        — recent news headlines
* ``get_fundamental_metrics`` — valuation / margin ratios
* ``get_macro_indicators``    — VIX, yield curve, DXY

Tool descriptions follow the Anthropic guideline of including a
"When to use" clause so the model calls the right tool at the right time.
"""

from __future__ import annotations

GET_PRICE_HISTORY: dict = {
    "name": "get_price_history",
    "description": (
        "Fetch daily OHLCV price history for a stock symbol. "
        "Use when you need recent price trends, volatility, or momentum analysis. "
        "Returns up to 60 trading days of data. "
        "Do NOT use for real-time intraday prices."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. 'AAPL', '005930.KS'.",
            },
            "start_date": {
                "type": "string",
                "description": (
                    "Start date in YYYY-MM-DD format. "
                    "Maximum 60 trading days before today. "
                    "Defaults to 30 days ago if omitted."
                ),
            },
        },
        "required": ["symbol"],
    },
}

GET_COMPANY_NEWS: dict = {
    "name": "get_company_news",
    "description": (
        "Fetch recent news headlines for a stock symbol. "
        "Use when you need to assess current sentiment, corporate events, "
        "earnings announcements, or regulatory news. "
        "Returns up to 15 most recent articles with title, date, and summary."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. 'AAPL', '005930.KS'.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of articles to return (1–15). Default: 10.",
                "minimum": 1,
                "maximum": 15,
            },
        },
        "required": ["symbol"],
    },
}

GET_FUNDAMENTAL_METRICS: dict = {
    "name": "get_fundamental_metrics",
    "description": (
        "Fetch key fundamental metrics for a stock: P/E ratio, P/B ratio, "
        "debt_to_equity, gross_margin, operating_margin, ROE, ROA, dividend_yield. "
        "Use when evaluating valuation or financial health relative to historical norms. "
        "Do NOT use for price/momentum analysis — use get_price_history instead."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. 'AAPL'.",
            },
            "period": {
                "type": "string",
                "enum": ["annual", "quarter"],
                "description": "Reporting period. Default: 'annual'.",
            },
        },
        "required": ["symbol"],
    },
}

GET_MACRO_INDICATORS: dict = {
    "name": "get_macro_indicators",
    "description": (
        "Fetch macro economic indicators: VIX (market fear), T10Y2Y (yield curve spread), "
        "DXY (US dollar index). "
        "Use when assessing the macro regime context for a trade thesis. "
        "Call this before forming a directional opinion on risk assets."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "indicators": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["vix", "t10y2y", "dxy"],
                },
                "description": (
                    "Which indicators to fetch. "
                    "Default: ['vix', 't10y2y']."
                ),
            },
        },
        "required": [],
    },
}

# Curated tool sets for each advisor type
NEWS_TOOLS: list[dict] = [GET_COMPANY_NEWS, GET_PRICE_HISTORY]
MACRO_TOOLS: list[dict] = [GET_MACRO_INDICATORS, GET_PRICE_HISTORY]
ALL_TOOLS: list[dict] = [
    GET_PRICE_HISTORY,
    GET_COMPANY_NEWS,
    GET_FUNDAMENTAL_METRICS,
    GET_MACRO_INDICATORS,
]

__all__ = [
    "GET_PRICE_HISTORY",
    "GET_COMPANY_NEWS",
    "GET_FUNDAMENTAL_METRICS",
    "GET_MACRO_INDICATORS",
    "NEWS_TOOLS",
    "MACRO_TOOLS",
    "ALL_TOOLS",
]
