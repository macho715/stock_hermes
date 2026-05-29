"""Tests for ClaudeClient.acall_with_tools()."""

from __future__ import annotations

import asyncio
import unittest.mock as mock

from stock_rtx4060.advisors.claude_client import _OPENBB_TOOLS_ENABLED, CallResult, ClaudeClient
from stock_rtx4060.advisors.openbb_tools.tool_schemas import NEWS_TOOLS


def test_openbb_tools_enabled_flag_is_bool():
    assert isinstance(_OPENBB_TOOLS_ENABLED, bool)


def test_acall_with_tools_disabled_delegates_to_acall(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.claude_client._OPENBB_TOOLS_ENABLED", False
    )
    client = ClaudeClient()
    acall_mock = mock.AsyncMock(return_value=mock.MagicMock(
        spec=CallResult,
        text="result", tokens_in=10, tokens_out=5,
        cost_usd=0.0, prompt_hash="ph", model="m",
        raw_message=None, cache_read_tokens=0, cache_creation_tokens=0,
    ))
    with mock.patch.object(client, "acall", acall_mock):
        asyncio.run(client.acall_with_tools(
            system="sys", messages=[{"role": "user", "content": "hi"}],
            tools=NEWS_TOOLS,
        ))
    acall_mock.assert_called_once()


def test_acall_with_tools_enabled_uses_loop(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.claude_client._OPENBB_TOOLS_ENABLED", True
    )
    client = ClaudeClient(model="claude-opus-4-7")

    loop_mock = mock.AsyncMock(return_value=("answer text", 100, 40, 0.0))
    with mock.patch(
        "stock_rtx4060.advisors.openbb_tools.agentic_loop.run_tool_loop",
        loop_mock,
    ):
        with mock.patch.object(client, "_ensure_async", return_value=mock.AsyncMock()):
            result = asyncio.run(client.acall_with_tools(
                system="sys",
                messages=[{"role": "user", "content": "analyze AAPL"}],
                tools=NEWS_TOOLS,
                as_of="2026-05-29",
            ))
    assert result.text == "answer text"
    assert result.tokens_in == 100
    assert result.tokens_out == 40


def test_acall_with_tools_returns_call_result_type(monkeypatch):
    monkeypatch.setattr(
        "stock_rtx4060.advisors.claude_client._OPENBB_TOOLS_ENABLED", True
    )
    client = ClaudeClient(model="claude-opus-4-7")

    with mock.patch(
        "stock_rtx4060.advisors.openbb_tools.agentic_loop.run_tool_loop",
        mock.AsyncMock(return_value=("text", 50, 20, 0.001)),
    ):
        with mock.patch.object(client, "_ensure_async", return_value=mock.AsyncMock()):
            result = asyncio.run(client.acall_with_tools(
                system=None,
                messages=[],
                tools=[],
            ))
    import stock_rtx4060.advisors.claude_client as cc_mod

    assert isinstance(result, cc_mod.CallResult)


def test_acall_with_tools_disabled_passes_tools_to_acall(monkeypatch):
    """When disabled, tools= is forwarded to acall() so existing callers see no change."""
    monkeypatch.setattr(
        "stock_rtx4060.advisors.claude_client._OPENBB_TOOLS_ENABLED", False
    )
    client = ClaudeClient()
    acall_mock = mock.AsyncMock(return_value=mock.MagicMock(
        spec=CallResult, text="x", tokens_in=1, tokens_out=1,
        cost_usd=0.0, prompt_hash="", model="m",
        raw_message=None, cache_read_tokens=0, cache_creation_tokens=0,
    ))
    with mock.patch.object(client, "acall", acall_mock):
        asyncio.run(client.acall_with_tools(
            system=None, messages=[], tools=NEWS_TOOLS
        ))
    _, kwargs = acall_mock.call_args
    assert kwargs.get("tools") == NEWS_TOOLS
