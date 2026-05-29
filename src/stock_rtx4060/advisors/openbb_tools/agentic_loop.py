"""Canonical Anthropic tool_use agentic loop.

Implements the standard pattern:
  while True:
    response = messages.create(tools=tools, ...)
    if stop_reason == "end_turn":  break
    if stop_reason == "tool_use":  execute tools, append results, continue

Ordering invariant (Anthropic API requirement):
  ``tool_result`` content blocks MUST appear before ``text`` blocks in the
  same user message, or the API returns HTTP 400.

References
----------
* https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
* Temporal AI cookbook 2026-01-16 — serialisation notes
"""

from __future__ import annotations

import logging
from typing import Any

from .tool_executor import ToolExecutor

_LOGGER = logging.getLogger("advisors.openbb_tools.agentic_loop")

_MAX_TOOL_ROUNDS_DEFAULT = 5


def _serialize_content(content: Any) -> list[dict[str, Any]]:
    """Coerce SDK content blocks to plain dicts for JSON round-trips."""
    if isinstance(content, list):
        out = []
        for block in content:
            if isinstance(block, dict):
                out.append(block)
            elif hasattr(block, "model_dump"):
                out.append(block.model_dump())
            elif hasattr(block, "__dict__"):
                out.append(dict(block.__dict__))
            else:
                out.append({"type": "text", "text": str(block)})
        return out
    return []


def _extract_text_blocks(content: Any) -> str:
    """Extract concatenated text from assistant content blocks."""
    if not content:
        return ""
    chunks: list[str] = []
    for block in content:
        block_type = getattr(block, "type", None) or (block.get("type") if isinstance(block, dict) else None)
        if block_type != "text":
            continue
        text = getattr(block, "text", None) or (block.get("text", "") if isinstance(block, dict) else "")
        if text:
            chunks.append(str(text))
    return "".join(chunks)


def _count(usage: Any, attr: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(attr, 0) or 0)
    return int(getattr(usage, attr, 0) or 0)


async def run_tool_loop(
    client: Any,
    *,
    messages: list[dict[str, Any]],
    model: str,
    system: Any,
    tools: list[dict[str, Any]],
    executor: ToolExecutor,
    as_of: str | None = None,
    max_tool_rounds: int = _MAX_TOOL_ROUNDS_DEFAULT,
    max_tokens: int = 4096,
) -> tuple[str, int, int, float]:
    """Run the Anthropic tool_use agentic loop.

    Parameters
    ----------
    client
        An ``anthropic.AsyncAnthropic`` (or compatible) client instance.
    messages
        Mutable list of messages.  Modified in-place to append tool
        interactions.  Pass a *copy* if you need the original preserved.
    model
        Model ID string.
    system
        System prompt (str or list-of-blocks).
    tools
        Tool definitions (Anthropic JSON schema format).
    executor
        :class:`ToolExecutor` instance.
    as_of
        PIT constraint forwarded to the executor on every tool call.
    max_tool_rounds
        Maximum number of tool_use iterations before forcing termination.
    max_tokens
        Hard output token ceiling.

    Returns
    -------
    (text, total_tokens_in, total_tokens_out, total_cost_usd)
    """
    total_in = total_out = 0
    total_cost = 0.0
    last_response: Any = None

    for round_num in range(max_tool_rounds + 1):
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "tools": tools,
        }
        if system is not None:
            kwargs["system"] = system

        response = await client.messages.create(**kwargs)
        last_response = response

        total_in += _count(response.usage, "input_tokens")
        total_in += _count(response.usage, "cache_read_input_tokens")
        total_in += _count(response.usage, "cache_creation_input_tokens")
        total_out += _count(response.usage, "output_tokens")

        stop_reason = getattr(response, "stop_reason", None)

        if stop_reason == "end_turn" or stop_reason is None:
            return _extract_text_blocks(response.content), total_in, total_out, total_cost

        if stop_reason == "tool_use":
            if round_num >= max_tool_rounds:
                _LOGGER.warning(
                    "[agentic_loop] max_tool_rounds=%d reached — forcing end_turn", max_tool_rounds
                )
                break

            # Append assistant message (serialised for JSON round-trips)
            messages.append({
                "role": "assistant",
                "content": _serialize_content(response.content),
            })

            # Execute all tool calls and collect results
            tool_results: list[dict[str, Any]] = []
            for block in response.content:
                block_type = getattr(block, "type", None)
                if block_type != "tool_use":
                    continue
                tool_name = getattr(block, "name", "")
                tool_input = getattr(block, "input", {}) or {}
                tool_id = getattr(block, "id", "")
                _LOGGER.debug("[agentic_loop] round=%d calling tool=%s", round_num + 1, tool_name)
                result_str, call_cost = await executor.dispatch(
                    name=tool_name,
                    input_params=dict(tool_input),
                    as_of=as_of,
                )
                total_cost += call_cost
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": result_str,
                })

            # Ordering invariant: tool_result blocks MUST precede text blocks
            messages.append({"role": "user", "content": tool_results})
        else:
            # max_tokens, error, or unknown stop_reason — exit loop
            _LOGGER.warning("[agentic_loop] unexpected stop_reason=%s", stop_reason)
            break

    # Fallback: return whatever text the last response had
    if last_response is not None:
        return _extract_text_blocks(last_response.content), total_in, total_out, total_cost
    return "", total_in, total_out, total_cost


__all__ = ["run_tool_loop"]
