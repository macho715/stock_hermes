"""Tests for the Anthropic SDK wrapper.

The ``anthropic`` package is optional in this repository; rather than
hitting the network we exercise the wrapper through a fake client
injected via the SDK-level seam.  This covers prompt assembly, cache
breakpoint placement, cost arithmetic and exponential backoff.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from stock_rtx4060.advisors.claude_client import (
    CACHE_READ_MULTIPLIER,
    CACHE_WRITE_MULTIPLIER,
    ClaudeClient,
    DEFAULT_MODEL,
    compute_cost_usd,
)


# ─── fake message + client ────────────────────────────────────────────────


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    def __init__(self, *, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_creation: int = 0) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_read_input_tokens = cache_read
        self.cache_creation_input_tokens = cache_creation


class _Message:
    def __init__(self, text: str, **usage_kwargs: int) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage(**usage_kwargs)


class _SyncMessages:
    def __init__(self, parent: "_FakeClient") -> None:
        self.parent = parent

    def create(self, **kwargs: Any) -> _Message:
        self.parent.calls.append(kwargs)
        if self.parent.error_queue:
            err = self.parent.error_queue.pop(0)
            if err is not None:
                raise err
        return _Message("ok", input_tokens=10, output_tokens=5, cache_read=20, cache_creation=30)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.messages = _SyncMessages(self)
        self.error_queue: list[Exception | None] = []


# ─── cost arithmetic ──────────────────────────────────────────────────────


def test_compute_cost_usd_components():
    cost = compute_cost_usd(
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
        model=DEFAULT_MODEL,
    )
    assert cost == pytest.approx(5.00, rel=1e-9)

    out_cost = compute_cost_usd(
        input_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=1_000_000,
        model=DEFAULT_MODEL,
    )
    assert out_cost == pytest.approx(25.00, rel=1e-9)

    cache_read_cost = compute_cost_usd(
        input_tokens=0,
        cache_read_tokens=1_000_000,
        cache_creation_tokens=0,
        output_tokens=0,
        model=DEFAULT_MODEL,
    )
    assert cache_read_cost == pytest.approx(5.00 * CACHE_READ_MULTIPLIER, rel=1e-9)

    cache_write_cost = compute_cost_usd(
        input_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=1_000_000,
        output_tokens=0,
        model=DEFAULT_MODEL,
    )
    assert cache_write_cost == pytest.approx(5.00 * CACHE_WRITE_MULTIPLIER, rel=1e-9)


def test_compute_cost_usd_unknown_model_falls_back_to_opus():
    a = compute_cost_usd(input_tokens=1000, cache_read_tokens=0, cache_creation_tokens=0, output_tokens=1000, model="unknown")
    b = compute_cost_usd(input_tokens=1000, cache_read_tokens=0, cache_creation_tokens=0, output_tokens=1000, model=DEFAULT_MODEL)
    assert a == pytest.approx(b)


def test_compute_cost_usd_negative_inputs_clamped():
    cost = compute_cost_usd(
        input_tokens=-100,
        cache_read_tokens=-100,
        cache_creation_tokens=-100,
        output_tokens=-100,
        model=DEFAULT_MODEL,
    )
    assert cost == 0.0


# ─── ClaudeClient.call ────────────────────────────────────────────────────


def test_call_attaches_cache_control_to_string_system_prompt():
    client = ClaudeClient()
    fake = _FakeClient()
    client._sync_client = fake

    result = client.call(system="hello world", messages=[{"role": "user", "content": "hi"}])

    assert len(fake.calls) == 1
    sys_blocks = fake.calls[0]["system"]
    assert isinstance(sys_blocks, list)
    assert sys_blocks[0]["cache_control"] == {"type": "ephemeral"}
    assert result.text == "ok"
    assert result.tokens_in == 10 + 20 + 30  # uncached + cache_read + cache_creation
    assert result.tokens_out == 5
    assert result.cache_read_tokens == 20
    assert result.cache_creation_tokens == 30


def test_call_passes_through_structured_system_blocks():
    client = ClaudeClient()
    fake = _FakeClient()
    client._sync_client = fake

    sys_blocks = [
        {"type": "text", "text": "system instruction", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "factor schema reference", "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": "ticker fundamental snapshot", "cache_control": {"type": "ephemeral"}},
    ]
    client.call(system=sys_blocks, messages=[{"role": "user", "content": "go"}])

    sent = fake.calls[0]["system"]
    breakpoints = [b for b in sent if b.get("cache_control") == {"type": "ephemeral"}]
    assert len(breakpoints) == 3
    # We never exceed the 4-breakpoint limit.
    assert len(breakpoints) <= 4


def test_call_computes_cost_from_usage():
    client = ClaudeClient()
    fake = _FakeClient()
    client._sync_client = fake

    result = client.call(system="s", messages=[{"role": "user", "content": "u"}])
    expected = compute_cost_usd(10, 20, 30, 5, DEFAULT_MODEL)
    assert result.cost_usd == pytest.approx(expected, rel=1e-9)


def test_call_retries_on_rate_limit_and_then_succeeds():
    client = ClaudeClient(max_retries=2, base_delay=0.0, max_delay=0.0)

    class _RateLimit(Exception):
        pass

    fake = _FakeClient()
    fake.error_queue = [_RateLimit("rate limited"), _RateLimit("again"), None]
    client._sync_client = fake
    client._retryable_error_classes = lambda: (_RateLimit,)  # type: ignore[assignment]

    result = client.call(system="s", messages=[{"role": "user", "content": "u"}])
    assert result.text == "ok"
    assert len(fake.calls) == 3  # 2 failures + 1 success


def test_call_exhausts_retries_and_raises():
    client = ClaudeClient(max_retries=1, base_delay=0.0, max_delay=0.0)

    class _RateLimit(Exception):
        pass

    fake = _FakeClient()
    fake.error_queue = [_RateLimit("a"), _RateLimit("b"), _RateLimit("c")]
    client._sync_client = fake
    client._retryable_error_classes = lambda: (_RateLimit,)  # type: ignore[assignment]

    with pytest.raises(_RateLimit):
        client.call(system="s", messages=[{"role": "user", "content": "u"}])
    assert len(fake.calls) == 2  # 1 initial + 1 retry


def test_acall_async_round_trip():
    client = ClaudeClient(base_delay=0.0)

    class _AsyncMessages:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return _Message("async", input_tokens=1, output_tokens=2)

    class _AsyncClient:
        def __init__(self) -> None:
            self.messages = _AsyncMessages()

    fake = _AsyncClient()
    client._async_client = fake

    out = asyncio.run(
        client.acall(system="sys", messages=[{"role": "user", "content": "x"}])
    )
    assert out.text == "async"
    assert out.tokens_in == 1
    assert out.tokens_out == 2
    assert len(fake.messages.calls) == 1


def test_prompt_hash_is_deterministic():
    client = ClaudeClient()
    fake = _FakeClient()
    client._sync_client = fake

    a = client.call(system="hello", messages=[{"role": "user", "content": "x"}])
    b = client.call(system="hello", messages=[{"role": "user", "content": "x"}])
    assert a.prompt_hash == b.prompt_hash
    c = client.call(system="hello!", messages=[{"role": "user", "content": "x"}])
    assert a.prompt_hash != c.prompt_hash
