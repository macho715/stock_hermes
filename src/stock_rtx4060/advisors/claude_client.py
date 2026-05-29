"""LLM SDK wrapper used by every advisor agent.

Design notes
------------
* Default Anthropic model is ``claude-opus-4-7`` per the project policy
  (knowledge cutoff: January 2026).  See ``shared/models.md`` in the
  ``claude-api`` skill bundle.
* MiniMax is supported through its OpenAI-compatible chat completions
  endpoint.  Set ``MINIMAX_API_KEY`` or ``LLM_ADVISOR_PROVIDER=minimax``.
  MiniMax thinking output is requested through ``reasoning_split=True`` so
  advisor agents receive parseable final text instead of ``<think>`` blocks.
* Up to **four** ``cache_control: {"type": "ephemeral"}`` breakpoints are
  supported — system prompt, factor schema reference, ticker fundamental
  snapshot, and prior conversation.  The Messages API allows at most 4
  breakpoints per request, which matches our slot budget exactly.
* Exponential backoff is implemented manually on top of the SDK's own
  retry to give us per-call telemetry; we only retry the well-defined
  transient errors (``RateLimitError``, ``OverloadedError``).
* Cost is computed locally from token counts — the SDK does not return a
  USD figure.

The whole module **must** be importable when the ``anthropic`` package is
not installed.  Tests use :mod:`respx` against the underlying ``httpx``
transport so live API calls never occur in CI.

Pricing (sourced 2026-04-29 from ``shared/models.md``):

* ``claude-opus-4-7`` — $5.00 / $25.00 per 1M input / output tokens.
* Cache reads cost ``~0.1×`` of the input rate.
* Cache writes cost ``~1.25×`` of the input rate (5-minute TTL — the
  default we use).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# W2-B3: LiteLLM optional import — graceful degradation when not installed.
try:
    from litellm import Router as _LiteLLMRouter  # type: ignore[import-not-found]

    _HAS_LITELLM = True
except ImportError:
    _LiteLLMRouter = None  # type: ignore[assignment, misc]
    _HAS_LITELLM = False

# Feature flag — set USE_LITELLM=true to activate the LiteLLM gateway.
# Disabled by default so the existing Anthropic/MiniMax path is unaffected.
_USE_LITELLM: bool = os.environ.get("USE_LITELLM", "false").lower() in ("1", "true", "yes")

# [E1-W3] MLflow LLM span tracing — set USE_MLFLOW_TRACING=true to record
# every advisor call as an MLflow span.  LiteLLM-routed calls require manual
# spans because mlflow.anthropic.autolog() does not intercept the Router path.
_USE_MLFLOW_TRACING: bool = os.environ.get("USE_MLFLOW_TRACING", "false").lower() in ("1", "true", "yes")

# OpenBB tool-use feature flag — set OPENBB_TOOLS_ENABLED=true to allow
# advisors to call OpenBB data endpoints via Anthropic tool_use during inference.
# Disabled by default so the existing acall() path is 100% unaffected.
_OPENBB_TOOLS_ENABLED: bool = os.environ.get("OPENBB_TOOLS_ENABLED", "false").lower() in ("1", "true", "yes")

DEFAULT_MODEL = "claude-opus-4-7"
DEFAULT_MINIMAX_MODEL = "MiniMax-M2.7"
DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_MAX_INPUT_TOKENS = 50_000
DEFAULT_MAX_OUTPUT_TOKENS = 4096

# Pricing constants — last reviewed 2026-04-29 against shared/models.md.
# All values are USD per token (i.e. per-token, not per-1M).
_USD_PER_TOKEN = {
    "claude-opus-4-7": {
        "input": 5.00 / 1_000_000.0,
        "output": 25.00 / 1_000_000.0,
    },
    "claude-opus-4-6": {
        "input": 5.00 / 1_000_000.0,
        "output": 25.00 / 1_000_000.0,
    },
    "claude-sonnet-4-6": {
        "input": 3.00 / 1_000_000.0,
        "output": 15.00 / 1_000_000.0,
    },
    "claude-haiku-4-5": {
        "input": 1.00 / 1_000_000.0,
        "output": 5.00 / 1_000_000.0,
    },
}

# Cache-pricing multipliers as documented in shared/prompt-caching.md.
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER = 1.25


def compute_cost_usd(
    input_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    output_tokens: int,
    model: str,
) -> float:
    """Return the USD cost of a single call.

    Tokens served from cache are billed at ``0.1×`` the input rate; cache
    writes are billed at ``1.25×`` the input rate (5-minute TTL).  Output
    tokens are billed at the output rate.
    """
    rates = _USD_PER_TOKEN.get(model)
    if rates is None:
        # Fall back to Opus pricing — conservative for unknown models so
        # we never under-report cost in the audit log.
        rates = _USD_PER_TOKEN[DEFAULT_MODEL]
    input_cost = max(int(input_tokens), 0) * rates["input"]
    cache_read_cost = max(int(cache_read_tokens), 0) * rates["input"] * CACHE_READ_MULTIPLIER
    cache_write_cost = max(int(cache_creation_tokens), 0) * rates["input"] * CACHE_WRITE_MULTIPLIER
    output_cost = max(int(output_tokens), 0) * rates["output"]
    return float(input_cost + cache_read_cost + cache_write_cost + output_cost)


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _looks_like_minimax_key(value: str | None) -> bool:
    return bool(value and value.strip().startswith("sk-cp-"))


def _normalize_provider(value: str | None) -> str | None:
    if not value:
        return None
    provider = value.strip().lower()
    aliases = {
        "anthropic": "anthropic",
        "claude": "anthropic",
        "minimax": "minimax",
        "mini-max": "minimax",
        "mini_max": "minimax",
    }
    return aliases.get(provider)


def has_live_advisor_key() -> bool:
    """Return True when at least one supported live advisor key is configured."""
    provider = _normalize_provider(_env("LLM_ADVISOR_PROVIDER"))
    anthropic_key = _env("ANTHROPIC_API_KEY")
    minimax_key = _env("MINIMAX_API_KEY")
    if provider == "anthropic":
        return bool(anthropic_key)
    if provider == "minimax":
        return bool(minimax_key or _looks_like_minimax_key(anthropic_key))
    return bool(anthropic_key or minimax_key)


@dataclass(frozen=True)
class CallResult:
    """Return value of :meth:`ClaudeClient.call` / ``acall``."""

    text: str
    raw_message: Any
    tokens_in: int
    tokens_out: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    prompt_hash: str
    model: str


@dataclass
class ClaudeClient:
    """Sync + async advisor wrapper with Anthropic and MiniMax support.

    The class is intentionally *light* — it does not own a global
    singleton.  Each agent constructs its own instance so the unit tests
    can mock the underlying ``httpx`` transport via ``respx`` without
    leaking state across tests.

    Parameters
    ----------
    model
        Model ID.  Defaults to :data:`DEFAULT_MODEL`.
    max_input_tokens
        Soft input-token budget — used by callers when assembling
        prompts.  We do not enforce it here.
    max_output_tokens
        Hard ``max_tokens`` ceiling passed to the API.
    api_key
        Optional override.  Falls back to provider-specific env vars.
    provider
        Optional provider override: ``anthropic`` or ``minimax``.  If omitted,
        ``LLM_ADVISOR_PROVIDER`` is read first, then configured keys.
    max_retries
        Number of additional attempts on retryable errors (default 3).
    base_delay
        Base backoff delay in seconds (default 1.0).
    """

    model: str = DEFAULT_MODEL
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    api_key: str | None = None
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    provider: str | None = None
    _sync_client: Any = field(default=None, init=False, repr=False)
    _async_client: Any = field(default=None, init=False, repr=False)

    # ---------- helpers -----------------------------------------------------

    def _provider(self) -> str:
        explicit = _normalize_provider(self.provider) or _normalize_provider(_env("LLM_ADVISOR_PROVIDER"))
        if explicit:
            return explicit
        if _env("MINIMAX_API_KEY") or _looks_like_minimax_key(self.api_key) or _looks_like_minimax_key(_env("ANTHROPIC_API_KEY")):
            return "minimax"
        return "anthropic"

    def _resolved_model(self) -> str:
        if self._provider() == "minimax" and self.model == DEFAULT_MODEL:
            return _env("MINIMAX_MODEL") or DEFAULT_MINIMAX_MODEL
        return self.model

    def _minimax_api_key(self) -> str | None:
        if self.api_key:
            return self.api_key
        key = _env("MINIMAX_API_KEY")
        if key:
            return key
        anthropic_key = _env("ANTHROPIC_API_KEY")
        if _looks_like_minimax_key(anthropic_key):
            return anthropic_key
        return None

    def _minimax_base_url(self) -> str:
        return (_env("MINIMAX_BASE_URL") or DEFAULT_MINIMAX_BASE_URL).rstrip("/")

    def _ensure_sync(self) -> Any:
        if self._provider() == "minimax":
            return self._ensure_minimax_sync()
        if self._sync_client is None:
            try:
                import anthropic  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - import guard
                raise ImportError(
                    "anthropic SDK is required for live calls. " "Install with: pip install 'anthropic>=0.40'"
                ) from exc
            self._sync_client = anthropic.Anthropic(api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY"))
        return self._sync_client

    def _ensure_async(self) -> Any:
        if self._provider() == "minimax":
            return self._ensure_minimax_async()
        if self._async_client is None:
            try:
                import anthropic  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - import guard
                raise ImportError(
                    "anthropic SDK is required for live calls. " "Install with: pip install 'anthropic>=0.40'"
                ) from exc
            self._async_client = anthropic.AsyncAnthropic(api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY"))
        return self._async_client

    def _ensure_minimax_sync(self) -> Any:
        if self._sync_client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise ImportError("httpx is required for MiniMax live calls. Install with: pip install httpx") from exc
            self._sync_client = httpx.Client(base_url=self._minimax_base_url(), timeout=60.0)
        return self._sync_client

    def _ensure_minimax_async(self) -> Any:
        if self._async_client is None:
            try:
                import httpx
            except ImportError as exc:  # pragma: no cover - dependency guard
                raise ImportError("httpx is required for MiniMax live calls. Install with: pip install httpx") from exc
            self._async_client = httpx.AsyncClient(base_url=self._minimax_base_url(), timeout=60.0)
        return self._async_client

    def _retryable_error_classes(self) -> tuple[type, ...]:
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError:  # pragma: no cover - import guard
            return ()
        classes: list[type] = []
        for attr in ("RateLimitError", "OverloadedError", "APIConnectionError"):
            cls = getattr(anthropic, attr, None)
            if isinstance(cls, type):
                classes.append(cls)
        return tuple(classes)

    def _minimax_retryable_error_classes(self) -> tuple[type, ...]:
        try:
            import httpx
        except ImportError:  # pragma: no cover - dependency guard
            return ()
        return (httpx.TimeoutException, httpx.TransportError)

    @staticmethod
    def _build_system_blocks(system: str | list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Coerce ``system`` into the list-of-blocks form so we can attach
        ``cache_control`` markers.  Strings become a single text block.
        """
        if system is None:
            return None
        if isinstance(system, str):
            return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        # caller already provided structured blocks — pass through verbatim
        return system

    @staticmethod
    def _hash_payload(*, system: Any, messages: Any, tools: Any) -> str:
        import json

        try:
            payload = json.dumps(
                {"system": system, "messages": messages, "tools": tools},
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
        except (TypeError, ValueError):
            payload = repr((system, messages, tools))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_text(message: Any) -> str:
        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")
        if not content:
            return ""
        chunks: list[str] = []
        for block in content:
            block_type = getattr(block, "type", None)
            if block_type is None and isinstance(block, dict):
                block_type = block.get("type")
            if block_type != "text":
                continue
            text = getattr(block, "text", None)
            if text is None and isinstance(block, dict):
                text = block.get("text", "")
            if text:
                chunks.append(str(text))
        return "".join(chunks)

    @staticmethod
    def _usage_attr(usage: Any, name: str) -> int:
        if usage is None:
            return 0
        if isinstance(usage, dict):
            return int(usage.get(name, 0) or 0)
        return int(getattr(usage, name, 0) or 0)

    @staticmethod
    def _system_to_minimax_text(system: str | list[dict[str, Any]] | None) -> str | None:
        if system is None:
            return None
        if isinstance(system, str):
            return system
        chunks: list[str] = []
        for block in system:
            if block.get("type") == "text" and block.get("text"):
                chunks.append(str(block["text"]))
        return "\n\n".join(chunks) if chunks else None

    def _build_minimax_payload(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        max_tokens: int | None,
    ) -> dict[str, Any]:
        minimax_messages = list(messages)
        system_text = self._system_to_minimax_text(system)
        if system_text:
            minimax_messages = [{"role": "system", "content": system_text}, *minimax_messages]
        return {
            "model": self._resolved_model(),
            "max_tokens": int(max_tokens or self.max_output_tokens),
            "messages": minimax_messages,
            "reasoning_split": True,
        }

    @staticmethod
    def _strip_minimax_thinking(text: str) -> str:
        import re

        stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        if stripped.startswith("<think>") and "</think>" in stripped:
            stripped = stripped.split("</think>", 1)[1].strip()
        return stripped

    @staticmethod
    def _extract_minimax_text(payload: dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return ClaudeClient._strip_minimax_thinking(content)
        if isinstance(content, list):
            chunks: list[str] = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    chunks.append(str(block.get("text", "")))
            return ClaudeClient._strip_minimax_thinking("".join(chunks))
        return ClaudeClient._strip_minimax_thinking(str(content or ""))

    def _build_minimax_call_result(self, payload: dict[str, Any], prompt_hash: str) -> CallResult:
        usage = payload.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens", 0) or 0)
        tokens_out = int(usage.get("completion_tokens", 0) or 0)
        return CallResult(
            text=self._extract_minimax_text(payload),
            raw_message=payload,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=0.0,
            prompt_hash=prompt_hash,
            model=self._resolved_model(),
        )

    def _build_call_result(
        self,
        message: Any,
        prompt_hash: str,
    ) -> CallResult:
        usage = getattr(message, "usage", None)
        if usage is None and isinstance(message, dict):
            usage = message.get("usage")
        tokens_in = self._usage_attr(usage, "input_tokens")
        cache_read = self._usage_attr(usage, "cache_read_input_tokens")
        cache_creation = self._usage_attr(usage, "cache_creation_input_tokens")
        tokens_out = self._usage_attr(usage, "output_tokens")
        # ``input_tokens`` is the uncached remainder; the total billable
        # input is the sum of all three.  We track them separately for
        # cost accounting, but report ``tokens_in`` as the SUM in the
        # AdvisoryOutput so that downstream observability sees the full
        # input budget.
        total_in = tokens_in + cache_read + cache_creation
        cost = compute_cost_usd(
            input_tokens=tokens_in,
            cache_read_tokens=cache_read,
            cache_creation_tokens=cache_creation,
            output_tokens=tokens_out,
            model=self.model,
        )
        return CallResult(
            text=self._extract_text(message),
            raw_message=message,
            tokens_in=int(total_in),
            tokens_out=int(tokens_out),
            cache_read_tokens=int(cache_read),
            cache_creation_tokens=int(cache_creation),
            cost_usd=float(cost),
            prompt_hash=prompt_hash,
            model=self.model,
        )

    # ---------- public sync entry point -------------------------------------

    def call(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> CallResult:
        """Synchronous wrapper around ``messages.create``.

        When ``USE_LITELLM=true`` and litellm is installed, routes through the
        LiteLLM Router with Anthropic as primary and MiniMax as fallback.
        Falls back to the native Anthropic/MiniMax path otherwise.
        """
        if _USE_LITELLM and _HAS_LITELLM:
            result = self._call_via_litellm(system=system, messages=messages, max_tokens=max_tokens)
            return self._wrap_with_mlflow_span(messages=messages, inner_result=result)
        if self._provider() == "minimax":
            result = self._call_minimax(system=system, messages=messages, max_tokens=max_tokens)
            return self._wrap_with_mlflow_span(messages=messages, inner_result=result)
        client = self._ensure_sync()
        sys_blocks = self._build_system_blocks(system)
        prompt_hash = self._hash_payload(system=sys_blocks, messages=messages, tools=tools)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(max_tokens or self.max_output_tokens),
            "messages": messages,
        }
        if sys_blocks is not None:
            kwargs["system"] = sys_blocks
        if tools:
            kwargs["tools"] = tools

        retryable = self._retryable_error_classes()
        attempt = 0
        while True:
            try:
                message = client.messages.create(**kwargs)
                result = self._build_call_result(message, prompt_hash)
                return self._wrap_with_mlflow_span(messages=messages, inner_result=result)
            except retryable as exc:  # type: ignore[misc]
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning("Anthropic retryable error exhausted: %s", exc)
                    raise
                delay = self._sleep_for(attempt)
                logger.info("Anthropic retryable error (%s); sleeping %.2fs", type(exc).__name__, delay)
                time.sleep(delay)

    def _call_minimax(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
    ) -> CallResult:
        client = self._ensure_sync()
        payload = self._build_minimax_payload(system=system, messages=messages, max_tokens=max_tokens)
        prompt_hash = self._hash_payload(system=system, messages=messages, tools=None)
        api_key = self._minimax_api_key()
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY is required for MiniMax advisor calls.")

        retryable = self._minimax_retryable_error_classes()
        attempt = 0
        while True:
            try:
                response = client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return self._build_minimax_call_result(response.json(), prompt_hash)
            except retryable as exc:  # type: ignore[misc]
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning("MiniMax retryable error exhausted: %s", exc)
                    raise
                delay = self._sleep_for(attempt)
                logger.info("MiniMax retryable error (%s); sleeping %.2fs", type(exc).__name__, delay)
                time.sleep(delay)

    # ---------- public async entry point ------------------------------------

    async def acall(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
    ) -> CallResult:
        if self._provider() == "minimax":
            return await self._acall_minimax(system=system, messages=messages, max_tokens=max_tokens)
        client = self._ensure_async()
        sys_blocks = self._build_system_blocks(system)
        prompt_hash = self._hash_payload(system=sys_blocks, messages=messages, tools=tools)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": int(max_tokens or self.max_output_tokens),
            "messages": messages,
        }
        if sys_blocks is not None:
            kwargs["system"] = sys_blocks
        if tools:
            kwargs["tools"] = tools

        retryable = self._retryable_error_classes()
        attempt = 0
        while True:
            try:
                message = await client.messages.create(**kwargs)
                return self._build_call_result(message, prompt_hash)
            except retryable as exc:  # type: ignore[misc]
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning("Anthropic retryable error exhausted: %s", exc)
                    raise
                delay = self._sleep_for(attempt)
                logger.info("Anthropic retryable error (%s); sleeping %.2fs", type(exc).__name__, delay)
                await asyncio.sleep(delay)

    async def _acall_minimax(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
    ) -> CallResult:
        client = self._ensure_async()
        payload = self._build_minimax_payload(system=system, messages=messages, max_tokens=max_tokens)
        prompt_hash = self._hash_payload(system=system, messages=messages, tools=None)
        api_key = self._minimax_api_key()
        if not api_key:
            raise RuntimeError("MINIMAX_API_KEY is required for MiniMax advisor calls.")

        retryable = self._minimax_retryable_error_classes()
        attempt = 0
        while True:
            try:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return self._build_minimax_call_result(response.json(), prompt_hash)
            except retryable as exc:  # type: ignore[misc]
                attempt += 1
                if attempt > self.max_retries:
                    logger.warning("MiniMax retryable error exhausted: %s", exc)
                    raise
                delay = self._sleep_for(attempt)
                logger.info("MiniMax retryable error (%s); sleeping %.2fs", type(exc).__name__, delay)
                await asyncio.sleep(delay)

    # ---------- LiteLLM gateway path (W2-B3) -----------------------------------

    def _call_via_litellm(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
    ) -> CallResult:
        """Route through LiteLLM Router with Anthropic primary + MiniMax fallback.

        Activated only when ``USE_LITELLM=true`` and ``litellm`` is installed.
        Falls back silently to the native path on any Router construction error.
        """

        fallback_models_raw = os.environ.get("LITELLM_FALLBACK_MODELS", "openai/MiniMax-M2.7")
        fallback_models = [m.strip() for m in fallback_models_raw.split(",") if m.strip()]

        model_list = [
            {
                "model_name": "primary",
                "litellm_params": {
                    "model": f"anthropic/{self.model}",
                    "api_key": self.api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
                },
            },
        ]
        for fb_model in fallback_models:
            fb_entry: dict[str, Any] = {
                "model_name": "fallback",
                "litellm_params": {"model": fb_model},
            }
            minimax_key = os.environ.get("MINIMAX_API_KEY", "")
            minimax_base = os.environ.get("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL)
            if "minimax" in fb_model.lower() or "MiniMax" in fb_model:
                fb_entry["litellm_params"]["api_key"] = minimax_key
                fb_entry["litellm_params"]["api_base"] = minimax_base
            model_list.append(fb_entry)

        # Build an OpenAI-format messages list (litellm expects this)
        litellm_messages: list[dict[str, Any]] = []
        if system:
            sys_text = system if isinstance(system, str) else " ".join(
                b.get("text", "") if isinstance(b, dict) else str(b) for b in system
            )
            litellm_messages.append({"role": "system", "content": sys_text})
        litellm_messages.extend(messages)

        prompt_hash = self._hash_payload(system=system, messages=messages, tools=None)
        used_provider = "anthropic"
        try:
            router = _LiteLLMRouter(model_list=model_list, fallbacks=[{"primary": ["fallback"]}])
            response = router.completion(
                model="primary",
                messages=litellm_messages,
                max_tokens=int(max_tokens or self.max_output_tokens),
            )
            # Detect which provider actually served the request
            if hasattr(response, "_hidden_params"):
                used_provider = str(response._hidden_params.get("model_id", "anthropic"))
            content = ""
            if response.choices:
                content = response.choices[0].message.content or ""
            usage = response.usage if hasattr(response, "usage") else None
            tokens_in = int(usage.prompt_tokens) if usage else 0
            tokens_out = int(usage.completion_tokens) if usage else 0
            cost = compute_cost_usd(tokens_in, 0, 0, tokens_out, self._resolved_model())
            result = CallResult(
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                prompt_hash=prompt_hash,
                model=self._resolved_model(),
            )
            logger.debug("LiteLLM call succeeded via provider=%s", used_provider)
            # Store provider on the result so callers can log it
            object.__setattr__(result, "_litellm_provider", used_provider)
            return result
        except Exception as exc:
            logger.warning("LiteLLM Router error (%s) — falling back to native path", exc)
            if self._provider() == "minimax":
                return self._call_minimax(system=system, messages=messages, max_tokens=max_tokens)
            return self.call(system=system, messages=messages, max_tokens=max_tokens)

    def _sleep_for(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        # tiny jitter so concurrent retries don't synchronise
        return float(delay) + random.uniform(0.0, min(0.5, delay))


    def _wrap_with_mlflow_span(
        self,
        *,
        messages: list[dict[str, Any]],
        inner_result: CallResult,
    ) -> CallResult:
        """[E1-W3] Record ``inner_result`` as an MLflow LLM span.

        No-ops gracefully when mlflow is not installed or
        ``USE_MLFLOW_TRACING=false`` (the default).
        LiteLLM-routed calls require manual spans because
        ``mlflow.anthropic.autolog()`` does not intercept the Router path.
        """
        if not _USE_MLFLOW_TRACING:
            return inner_result
        try:
            import mlflow  # type: ignore[import-not-found]

            with mlflow.start_span(
                name="advisor_call",
                span_type="LLM",
                attributes={"model": inner_result.model},
            ) as span:
                span.set_inputs({"message_count": len(messages)})
                span.set_outputs(
                    {
                        "tokens_in": inner_result.tokens_in,
                        "tokens_out": inner_result.tokens_out,
                        "cost_usd": round(inner_result.cost_usd, 6),
                    }
                )
        except Exception:  # pragma: no cover — mlflow optional
            logger.debug("mlflow_span failed (optional), continuing")
        return inner_result


    async def acall_with_tools(
        self,
        *,
        system: str | list[dict[str, Any]] | None,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        as_of: str | None = None,
        max_tool_rounds: int = 5,
        max_tokens: int | None = None,
    ) -> CallResult:
        """Async call with Anthropic tool_use agentic loop.

        Wraps :func:`~advisors.openbb_tools.agentic_loop.run_tool_loop` so
        advisors can call OpenBB data endpoints during inference.

        When ``OPENBB_TOOLS_ENABLED=false`` (the default), falls back to the
        standard :meth:`acall` path without any tool handling so the existing
        behaviour is 100% preserved.

        Parameters
        ----------
        tools
            Anthropic tool schemas (from :mod:`advisors.openbb_tools.tool_schemas`).
        as_of
            Point-in-time constraint forwarded to the tool executor.
        max_tool_rounds
            Maximum tool_use iterations before forcing end_turn.
        """
        if not _OPENBB_TOOLS_ENABLED:
            return await self.acall(system=system, messages=messages, tools=tools, max_tokens=max_tokens)

        from .openbb_tools.agentic_loop import run_tool_loop
        from .openbb_tools.tool_executor import ToolExecutor

        client = self._ensure_async()
        sys_blocks = self._build_system_blocks(system)
        prompt_hash = self._hash_payload(system=sys_blocks, messages=messages, tools=tools)
        executor = ToolExecutor(as_of=as_of)

        text, total_in, total_out, tool_cost = await run_tool_loop(
            client,
            messages=list(messages),   # copy so caller's list is not mutated
            model=self.model,
            system=sys_blocks,
            tools=tools,
            executor=executor,
            as_of=as_of,
            max_tool_rounds=max_tool_rounds,
            max_tokens=int(max_tokens or self.max_output_tokens),
        )

        cost = compute_cost_usd(
            input_tokens=total_in,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            output_tokens=total_out,
            model=self.model,
        ) + tool_cost

        result = CallResult(
            text=text,
            raw_message=None,
            tokens_in=total_in,
            tokens_out=total_out,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            cost_usd=float(cost),
            prompt_hash=prompt_hash,
            model=self.model,
        )
        return self._wrap_with_mlflow_span(messages=messages, inner_result=result)


__all__ = [
    "ClaudeClient",
    "CallResult",
    "compute_cost_usd",
    "has_live_advisor_key",
    "DEFAULT_MODEL",
    "DEFAULT_MINIMAX_MODEL",
    "DEFAULT_MINIMAX_BASE_URL",
    "DEFAULT_MAX_INPUT_TOKENS",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "_USE_MLFLOW_TRACING",
    "_OPENBB_TOOLS_ENABLED",
]
