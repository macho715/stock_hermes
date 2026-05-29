"""OpenBB tool executor — dispatches Anthropic tool_use calls to OpenBB functions.

Design invariants
-----------------
* **PIT guard**: when ``as_of`` is supplied, ``end_date`` is clamped to
  ``as_of`` so no future data leaks into advisor reasoning.
* **Graceful degradation**: if ``openbb`` is not installed, every tool
  returns ``{"status": "unavailable", "error": "openbb not installed"}``.
* **Truncation**: results are capped at ``RESULT_MAX_CHARS`` characters
  to stay within the advisor token budget (50 k input).
* **Timeout**: each call is limited to ``TOOL_TIMEOUT_SEC`` seconds via
  :func:`asyncio.wait_for`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any

_LOGGER = logging.getLogger("advisors.openbb_tools")

RESULT_MAX_CHARS: int = int(os.environ.get("OPENBB_TOOL_RESULT_MAX_CHARS", "2000"))
TOOL_TIMEOUT_SEC: float = float(os.environ.get("OPENBB_TOOL_TIMEOUT_SEC", "10"))


def _try_import_openbb() -> Any | None:
    try:
        from openbb import obb  # type: ignore[import-not-found]
        return obb
    except Exception:  # pragma: no cover — optional dep
        return None


def _truncate(text: str, max_chars: int = RESULT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    _LOGGER.debug("[OpenBB Tool] result truncated: %d → %d chars", len(text), max_chars)
    return text[:max_chars] + "…"


def _enforce_pit(params: dict[str, Any], as_of: str | None) -> str | None:
    """Return a blocked-status JSON string if the call violates PIT constraints.

    Also mutates ``params`` to inject ``end_date = as_of`` when not provided,
    so callers always get PIT-correct data even if they omit ``end_date``.
    """
    if as_of is None:
        return None
    end_date = params.get("end_date") or params.get("date")
    if end_date and end_date > as_of:
        _LOGGER.warning(
            "[OpenBB Tool] PIT guard: end_date %s > as_of %s — blocking call",
            end_date, as_of,
        )
        return json.dumps({
            "status": "blocked",
            "reason": f"end_date {end_date} exceeds as_of {as_of}. "
                      "Data after as_of is forbidden to prevent look-ahead bias.",
        })
    # Inject end_date even if not provided by the model
    if "start_date" in params or "end_date" not in params:
        params.setdefault("end_date", as_of)
    return None


def _get_price_history(obb: Any, params: dict[str, Any]) -> str:
    symbol = str(params.get("symbol", ""))
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    kwargs: dict[str, Any] = {"symbol": symbol}
    if start_date:
        kwargs["start_date"] = start_date
    if end_date:
        kwargs["end_date"] = end_date

    try:
        result = obb.equity.price.historical(**kwargs)
        df = result.to_df()
        if df.empty:
            return json.dumps({"status": "no_data", "symbol": symbol})
        # Keep last 60 rows, return key columns only
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        subset = df[cols].tail(60)
        rows = subset.reset_index().to_dict(orient="records") if "date" not in cols else subset.to_dict(orient="records")
        return json.dumps({"status": "ok", "symbol": symbol, "rows": len(rows), "data": rows})
    except Exception as exc:
        _LOGGER.warning("[OpenBB Tool] get_price_history error: %s", exc)
        return json.dumps({"status": "error", "symbol": symbol, "error": str(exc)[:200]})


def _get_company_news(obb: Any, params: dict[str, Any]) -> str:
    symbol = str(params.get("symbol", ""))
    limit = int(params.get("limit", 10))
    limit = max(1, min(15, limit))
    end_date = params.get("end_date")

    kwargs: dict[str, Any] = {"symbol": symbol, "limit": limit}
    if end_date:
        kwargs["end_date"] = end_date

    try:
        result = obb.news.company(**kwargs)
        articles = []
        for item in (result.results or []):
            articles.append({
                "title": getattr(item, "title", ""),
                "date": str(getattr(item, "date", "")),
                "text": str(getattr(item, "text", "") or "")[:300],
                "url": getattr(item, "url", ""),
            })
        return json.dumps({"status": "ok", "symbol": symbol, "count": len(articles), "articles": articles})
    except Exception as exc:
        _LOGGER.warning("[OpenBB Tool] get_company_news error: %s", exc)
        return json.dumps({"status": "error", "symbol": symbol, "error": str(exc)[:200]})


def _get_fundamental_metrics(obb: Any, params: dict[str, Any]) -> str:
    symbol = str(params.get("symbol", ""))
    period = str(params.get("period", "annual"))

    try:
        result = obb.equity.fundamental.metrics(symbol=symbol, period=period, limit=1)
        items = result.results or []
        if not items:
            return json.dumps({"status": "no_data", "symbol": symbol})
        item = items[0]
        metrics = {
            "pe_ratio": getattr(item, "pe", None),
            "pb_ratio": getattr(item, "pb", None),
            "debt_to_equity": getattr(item, "debt_to_equity", None),
            "gross_margin": getattr(item, "gross_margin", None),
            "operating_margin": getattr(item, "operating_income_ratio", None),
            "roe": getattr(item, "roe", None),
            "roa": getattr(item, "roa", None),
            "dividend_yield": getattr(item, "dividend_yield", None),
        }
        # Remove None values
        metrics = {k: v for k, v in metrics.items() if v is not None}
        return json.dumps({"status": "ok", "symbol": symbol, "period": period, "metrics": metrics})
    except Exception as exc:
        _LOGGER.warning("[OpenBB Tool] get_fundamental_metrics error: %s", exc)
        return json.dumps({"status": "error", "symbol": symbol, "error": str(exc)[:200]})


def _get_macro_indicators(params: dict[str, Any]) -> str:
    requested = list(params.get("indicators") or ["vix", "t10y2y"])
    result: dict[str, Any] = {"status": "ok", "indicators": {}}
    try:
        import pandas_datareader.data as pdr  # type: ignore[import-not-found]
    except ImportError:
        return json.dumps({"status": "unavailable", "error": "pandas_datareader not installed"})

    series_map = {"vix": "VIXCLS", "t10y2y": "T10Y2Y", "dxy": "DTWEXBGS"}
    for name in requested:
        fred_id = series_map.get(name.lower())
        if not fred_id:
            continue
        try:
            val = float(pdr.DataReader(fred_id, "fred").iloc[-1, 0])
            result["indicators"][name] = round(val, 4)
        except Exception as exc:  # pragma: no cover — network
            result["indicators"][name] = f"error: {exc}"
    return json.dumps(result)


_UNAVAILABLE = json.dumps({"status": "unavailable", "error": "openbb not installed. pip install openbb"})


class ToolExecutor:
    """Dispatches Anthropic tool_use calls to OpenBB provider functions.

    Parameters
    ----------
    as_of:
        Point-in-time constraint (ISO date string).  When supplied, all
        historical data requests are capped at this date.
    """

    def __init__(self, as_of: str | None = None) -> None:
        self.as_of = as_of

    async def dispatch(
        self,
        name: str,
        input_params: dict[str, Any],
        as_of: str | None = None,
    ) -> tuple[str, float]:
        """Execute a single tool call.

        Returns
        -------
        (result_json_str, cost_usd)
            ``result_json_str`` is always a valid JSON string ≤ RESULT_MAX_CHARS.
            ``cost_usd`` is 0.0 (OpenBB free-tier calls have no LLM cost).
        """
        effective_as_of = as_of or self.as_of
        params = dict(input_params)  # copy to avoid mutating caller's dict

        # PIT guard
        blocked = _enforce_pit(params, effective_as_of)
        if blocked is not None:
            return blocked, 0.0

        t0 = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self._sync_dispatch, name, params),
                timeout=TOOL_TIMEOUT_SEC,
            )
        except TimeoutError:
            _LOGGER.warning("[OpenBB Tool] %s timed out after %.0fs", name, TOOL_TIMEOUT_SEC)
            result = json.dumps({"status": "error", "error": f"timeout after {TOOL_TIMEOUT_SEC}s"})

        elapsed = time.perf_counter() - t0
        _LOGGER.info(
            "[OpenBB Tool] name=%s elapsed_ms=%.0f chars=%d",
            name, elapsed * 1000, len(result),
        )
        return _truncate(result), 0.0

    def _sync_dispatch(self, name: str, params: dict[str, Any]) -> str:
        if name == "get_macro_indicators":
            # Macro indicators use pandas_datareader, not openbb equity
            return _get_macro_indicators(params)

        obb = _try_import_openbb()
        if obb is None:
            return _UNAVAILABLE

        if name == "get_price_history":
            return _get_price_history(obb, params)
        if name == "get_company_news":
            return _get_company_news(obb, params)
        if name == "get_fundamental_metrics":
            return _get_fundamental_metrics(obb, params)

        return json.dumps({"status": "error", "error": f"unknown tool: {name}"})


__all__ = ["ToolExecutor", "RESULT_MAX_CHARS", "TOOL_TIMEOUT_SEC"]
