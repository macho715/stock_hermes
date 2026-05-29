"""Tests for the Anthropic tool_use agentic loop."""

from __future__ import annotations

import asyncio
import json
import unittest.mock as mock

from stock_rtx4060.advisors.openbb_tools.agentic_loop import (
    _extract_text_blocks,
    _serialize_content,
    run_tool_loop,
)
from stock_rtx4060.advisors.openbb_tools.tool_executor import ToolExecutor

# ---------------------------------------------------------------------------
# _serialize_content
# ---------------------------------------------------------------------------

def test_serialize_content_dict_passthrough():
    block = {"type": "text", "text": "hello"}
    result = _serialize_content([block])
    assert result == [block]


def test_serialize_content_model_dump():
    block = mock.MagicMock()
    block.model_dump.return_value = {"type": "text", "text": "world"}
    result = _serialize_content([block])
    assert result == [{"type": "text", "text": "world"}]


def test_serialize_content_empty():
    assert _serialize_content([]) == []


# ---------------------------------------------------------------------------
# _extract_text_blocks
# ---------------------------------------------------------------------------

def test_extract_text_from_dict_blocks():
    content = [
        {"type": "text", "text": "Hello "},
        {"type": "tool_use", "name": "x", "input": {}},
        {"type": "text", "text": "world"},
    ]
    assert _extract_text_blocks(content) == "Hello world"


def test_extract_text_from_sdk_blocks():
    b1 = mock.MagicMock()
    b1.type = "text"
    b1.text = "answer"
    b2 = mock.MagicMock()
    b2.type = "tool_use"
    assert _extract_text_blocks([b1, b2]) == "answer"


def test_extract_text_empty_content():
    assert _extract_text_blocks([]) == ""
    assert _extract_text_blocks(None) == ""


# ---------------------------------------------------------------------------
# run_tool_loop helpers
# ---------------------------------------------------------------------------

def _make_end_turn_response(text="final answer"):
    resp = mock.MagicMock()
    resp.stop_reason = "end_turn"
    block = mock.MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    resp.usage.input_tokens = 100
    resp.usage.output_tokens = 50
    resp.usage.cache_read_input_tokens = 0
    resp.usage.cache_creation_input_tokens = 0
    return resp


def _make_tool_use_response(tool_name="get_company_news", tool_id="tu_1"):
    resp = mock.MagicMock()
    resp.stop_reason = "tool_use"
    block = mock.MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = {"symbol": "AAPL"}
    resp.content = [block]
    resp.usage.input_tokens = 80
    resp.usage.output_tokens = 20
    resp.usage.cache_read_input_tokens = 0
    resp.usage.cache_creation_input_tokens = 0
    return resp


# ---------------------------------------------------------------------------
# run_tool_loop tests (using asyncio.run to match project conventions)
# ---------------------------------------------------------------------------

def test_loop_end_turn_immediately():
    client = mock.AsyncMock()
    client.messages.create = mock.AsyncMock(return_value=_make_end_turn_response("done"))
    executor = ToolExecutor()

    text, tin, tout, cost = asyncio.run(run_tool_loop(
        client, messages=[], model="m", system=None,
        tools=[], executor=executor,
    ))
    assert text == "done"
    assert tin > 0
    assert tout > 0


def test_loop_single_tool_then_end_turn():
    responses = [
        _make_tool_use_response("get_company_news", "tu_1"),
        _make_end_turn_response("sentiment: bullish"),
    ]
    client = mock.AsyncMock()
    client.messages.create = mock.AsyncMock(side_effect=responses)

    executor = mock.AsyncMock(spec=ToolExecutor)
    executor.dispatch = mock.AsyncMock(
        return_value=(json.dumps({"status": "ok", "articles": []}), 0.0)
    )

    text, tin, tout, _ = asyncio.run(run_tool_loop(
        client, messages=[], model="m", system=None,
        tools=[{"name": "get_company_news"}], executor=executor,
    ))
    assert text == "sentiment: bullish"
    executor.dispatch.assert_called_once()


def test_loop_max_rounds_guard():
    """Loop should stop after max_tool_rounds even if model keeps requesting tools."""
    tool_resp = _make_tool_use_response()
    client = mock.AsyncMock()
    client.messages.create = mock.AsyncMock(return_value=tool_resp)

    executor = mock.AsyncMock(spec=ToolExecutor)
    executor.dispatch = mock.AsyncMock(return_value=('{"status":"ok"}', 0.0))

    asyncio.run(run_tool_loop(
        client, messages=[], model="m", system=None,
        tools=[{"name": "get_company_news"}], executor=executor,
        max_tool_rounds=3,
    ))
    assert executor.dispatch.call_count <= 3


def test_loop_tool_result_appended_to_messages():
    messages: list = []
    responses = [
        _make_tool_use_response("get_price_history", "tu_99"),
        _make_end_turn_response("ok"),
    ]
    client = mock.AsyncMock()
    client.messages.create = mock.AsyncMock(side_effect=responses)

    executor = mock.AsyncMock(spec=ToolExecutor)
    executor.dispatch = mock.AsyncMock(return_value=('{"status":"ok","data":[]}', 0.0))

    asyncio.run(run_tool_loop(
        client, messages=messages, model="m", system=None,
        tools=[{"name": "get_price_history"}], executor=executor,
    ))

    roles = [m["role"] for m in messages]
    assert "assistant" in roles
    assert "user" in roles
    user_msg = next(m for m in messages if m["role"] == "user")
    content = user_msg["content"]
    assert any(
        (isinstance(b, dict) and b.get("type") == "tool_result")
        for b in content
    )


def test_loop_returns_text_as_str():
    client = mock.AsyncMock()
    client.messages.create = mock.AsyncMock(return_value=_make_end_turn_response("hello"))
    executor = ToolExecutor()

    text, _, _, _ = asyncio.run(run_tool_loop(
        client, messages=[], model="m", system=None,
        tools=[], executor=executor,
    ))
    assert isinstance(text, str)
