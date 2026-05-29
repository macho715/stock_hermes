"""Tests for OpenBB tool executor: PIT guard, truncation, graceful fallback."""

from __future__ import annotations

import asyncio
import json
import unittest.mock as mock

from stock_rtx4060.advisors.openbb_tools.tool_executor import (
    RESULT_MAX_CHARS,
    ToolExecutor,
    _enforce_pit,
    _truncate,
)

# ---------------------------------------------------------------------------
# _enforce_pit
# ---------------------------------------------------------------------------

def test_enforce_pit_returns_none_when_no_as_of():
    params = {"symbol": "AAPL", "end_date": "2030-01-01"}
    assert _enforce_pit(params, None) is None


def test_enforce_pit_blocks_future_end_date():
    params = {"symbol": "AAPL", "end_date": "2026-06-01"}
    result = _enforce_pit(params, "2026-05-29")
    assert result is not None
    data = json.loads(result)
    assert data["status"] == "blocked"
    assert "2026-06-01" in data["reason"]


def test_enforce_pit_passes_past_end_date():
    params = {"symbol": "AAPL", "end_date": "2026-05-01"}
    result = _enforce_pit(params, "2026-05-29")
    assert result is None


def test_enforce_pit_injects_end_date_when_missing():
    params = {"symbol": "AAPL", "start_date": "2026-05-01"}
    _enforce_pit(params, "2026-05-29")
    assert params.get("end_date") == "2026-05-29"


def test_enforce_pit_equal_date_is_allowed():
    params = {"symbol": "AAPL", "end_date": "2026-05-29"}
    result = _enforce_pit(params, "2026-05-29")
    assert result is None


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

def test_truncate_short_string_unchanged():
    s = "hello"
    assert _truncate(s, max_chars=100) == "hello"


def test_truncate_long_string_cut():
    s = "x" * 3000
    result = _truncate(s, max_chars=RESULT_MAX_CHARS)
    assert len(result) <= RESULT_MAX_CHARS + 3  # +3 for ellipsis


def test_truncate_appends_ellipsis():
    s = "y" * 5000
    result = _truncate(s, max_chars=100)
    assert result.endswith("…")


# ---------------------------------------------------------------------------
# ToolExecutor.dispatch — graceful fallback (openbb not installed)
# ---------------------------------------------------------------------------

def test_executor_graceful_no_openbb():
    """When openbb is not importable, returns unavailable status."""
    executor = ToolExecutor()
    with mock.patch(
        "stock_rtx4060.advisors.openbb_tools.tool_executor._try_import_openbb",
        return_value=None,
    ):
        result_str, cost = asyncio.run(
            executor.dispatch("get_price_history", {"symbol": "AAPL"})
        )
    data = json.loads(result_str)
    assert data["status"] == "unavailable"
    assert cost == 0.0


def test_executor_pit_guard_blocks_future_date():
    executor = ToolExecutor(as_of="2026-05-29")
    result_str, _ = asyncio.run(executor.dispatch(
        "get_price_history",
        {"symbol": "AAPL", "end_date": "2026-06-15"},
    ))
    data = json.loads(result_str)
    assert data["status"] == "blocked"


def test_executor_unknown_tool_returns_error():
    executor = ToolExecutor()
    mock_obb = mock.MagicMock()
    with mock.patch(
        "stock_rtx4060.advisors.openbb_tools.tool_executor._try_import_openbb",
        return_value=mock_obb,
    ):
        result_str, _ = asyncio.run(
            executor.dispatch("totally_unknown_tool", {"symbol": "X"})
        )
    data = json.loads(result_str)
    assert data["status"] == "error"
    assert "unknown tool" in data["error"]


def test_executor_result_is_valid_json():
    executor = ToolExecutor()
    with mock.patch(
        "stock_rtx4060.advisors.openbb_tools.tool_executor._try_import_openbb",
        return_value=None,
    ):
        result_str, _ = asyncio.run(
            executor.dispatch("get_company_news", {"symbol": "MSFT"})
        )
    data = json.loads(result_str)
    assert isinstance(data, dict)


def test_executor_result_within_max_chars():
    executor = ToolExecutor()
    huge_data = {"status": "ok", "data": ["x" * 500] * 20}

    def _huge_dispatch(name, params):
        return json.dumps(huge_data)

    with mock.patch.object(executor, "_sync_dispatch", side_effect=_huge_dispatch):
        result_str, _ = asyncio.run(
            executor.dispatch("get_price_history", {"symbol": "AAPL"})
        )
    assert len(result_str) <= RESULT_MAX_CHARS + 3


def test_executor_macro_graceful_no_datareader():
    """Macro indicators gracefully handles missing pandas_datareader."""
    executor = ToolExecutor()
    import sys
    orig = sys.modules.get("pandas_datareader")
    sys.modules["pandas_datareader"] = None  # type: ignore[assignment]
    sys.modules["pandas_datareader.data"] = None  # type: ignore[assignment]
    try:
        result_str, _ = asyncio.run(executor.dispatch("get_macro_indicators", {}))
        data = json.loads(result_str)
        assert data["status"] in ("unavailable", "error", "ok")
    finally:
        if orig is None:
            sys.modules.pop("pandas_datareader", None)
            sys.modules.pop("pandas_datareader.data", None)
        else:
            sys.modules["pandas_datareader"] = orig
