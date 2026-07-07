"""Provider call with fallback chain + an in-memory model cache.

The cache is populated once at startup (see app.main lifespan) so the hot path
never hits Postgres for model metadata.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field

from app.core.normalizer import normalize_chunk, normalize_response
from app.db.models import Model
from app.providers import ProviderError, get_provider
from app.providers.base import RETRYABLE
from app.schemas.chat import ChatCompletionResponse, ChatMessage

logger = logging.getLogger("archer.proxy")

# Fixed fallback order (context.md §5.9, Archer-corrected for Groq deprecations;
# rebalanced in Phase 2A). Fast/reliable Groq models early; the large Ollama
# Cloud models (free tier — can rate-limit) sit in the middle; the chain still
# ends on ultra-reliable fast Groq models as the final safety net. Must contain
# every active model name (kept in sync with the seed + router.py — see
# tests/test_catalog_sync.py).
FALLBACK_CHAIN = [
    "llama-3.3-70b-groq",
    "llama-4-scout-groq",
    "gpt-oss-120b-groq",
    "qwen3-coder-ollama",
    "nemotron-3-super-ollama",
    "minimax-m3-ollama",
    "glm-4.7-ollama",
    "gpt-oss-20b-groq",
    "llama-3.1-8b-groq",
]


class ModelCache:
    def __init__(self) -> None:
        self._by_name: dict[str, Model] = {}
        self._by_id: dict[uuid.UUID, Model] = {}

    def load(self, models: list[Model]) -> None:
        active = [m for m in models if m.is_active]
        self._by_name = {m.name: m for m in active}
        self._by_id = {m.id: m for m in active}

    def get(self, name: str) -> Model | None:
        return self._by_name.get(name)

    def get_by_id(self, model_id: uuid.UUID) -> Model | None:
        return self._by_id.get(model_id)

    def __len__(self) -> int:
        return len(self._by_name)


model_cache = ModelCache()


class AllModelsUnavailable(Exception):
    pass


@dataclass
class ProxyResult:
    response: ChatCompletionResponse
    model: Model
    original_model: Model | None
    fallback_used: bool
    routing_reason: str


async def call_with_fallback(
    selected_name: str,
    routing_reason: str,
    messages: list[ChatMessage],
    temperature: float,
    max_tokens: int,
) -> ProxyResult:
    """Try the selected model, then walk the fallback chain on retryable errors."""
    selected = model_cache.get(selected_name)

    # Attempt order: selected model first, then the rest of the chain.
    order = [selected_name] + [n for n in FALLBACK_CHAIN if n != selected_name]

    last_error: ProviderError | None = None
    for attempt_name in order:
        model = model_cache.get(attempt_name)
        if model is None:
            continue
        try:
            raw = await get_provider(model.provider).chat(
                model.model_id, messages, temperature, max_tokens
            )
        except ProviderError as exc:
            last_error = exc
            logger.warning("provider %s failed (%s): %s", attempt_name, exc.category, exc)
            if exc.category in RETRYABLE:
                continue
            # Non-retryable (e.g. client_error): another model won't fix a bad
            # request, so stop walking the chain instead of fanning out N calls.
            break

        is_fallback = model.name != selected_name and selected is not None
        return ProxyResult(
            response=normalize_response(raw),
            model=model,
            original_model=selected if is_fallback else None,
            fallback_used=is_fallback,
            routing_reason=f"{routing_reason}_fallback" if is_fallback else routing_reason,
        )

    raise AllModelsUnavailable(str(last_error) if last_error else "no models available")


@dataclass
class StreamOutcome:
    """Mutable channel back to the route — populated as the stream progresses so
    the fire-and-forget log written in the route's finally has model/usage/TTFT."""

    model: Model | None = None
    original_model: Model | None = None
    fallback_used: bool = False
    routing_reason: str = ""
    ttft_ms: int | None = None
    usage: dict = field(default_factory=dict)
    forwarded_any: bool = False
    interrupted: bool = False
    error_message: str | None = None


async def stream_with_fallback(
    selected_name: str,
    routing_reason: str,
    messages: list[ChatMessage],
    temperature: float,
    max_tokens: int,
    archer_id: str,
    outcome: StreamOutcome,
):
    """Yield normalized SSE lines, walking the chain on retryable errors — but
    only until the first chunk is forwarded. After that the response is
    committed: a provider failure terminates the stream (best-effort [DONE] +
    stream_interrupted) with no model switch. If every model fails before the
    first byte, raises AllModelsUnavailable so the route can return 503 (nothing
    has been sent to the client yet — the route primes this generator before
    building the StreamingResponse)."""
    selected = model_cache.get(selected_name)
    order = [selected_name] + [n for n in FALLBACK_CHAIN if n != selected_name]

    started = time.perf_counter()
    last_error: ProviderError | None = None

    for attempt_name in order:
        model = model_cache.get(attempt_name)
        if model is None:
            continue
        gen = get_provider(model.provider).stream(
            model.model_id, messages, temperature, max_tokens
        )
        try:
            async for raw_line in gen:
                normalized = normalize_chunk(raw_line, archer_id)
                if normalized is None:
                    continue
                if not outcome.forwarded_any:
                    outcome.forwarded_any = True
                    outcome.ttft_ms = int((time.perf_counter() - started) * 1000)
                    is_fallback = model.name != selected_name and selected is not None
                    outcome.model = model
                    outcome.fallback_used = is_fallback
                    outcome.original_model = selected if is_fallback else None
                    outcome.routing_reason = (
                        f"{routing_reason}_fallback" if is_fallback else routing_reason
                    )
                if '"usage"' in normalized:
                    try:
                        chunk = json.loads(normalized[len("data: "):])
                        if chunk.get("usage"):
                            outcome.usage = chunk["usage"]
                    except (ValueError, TypeError):
                        pass
                yield normalized
            yield "data: [DONE]\n\n"
            return
        except ProviderError as exc:
            last_error = exc
            if outcome.forwarded_any:
                # Committed to this model — cannot swap mid-response.
                outcome.interrupted = True
                outcome.error_message = f"stream_interrupted: {exc}"
                logger.warning("stream %s interrupted (%s): %s", attempt_name, exc.category, exc)
                yield "data: [DONE]\n\n"
                return
            logger.warning("stream provider %s failed (%s): %s", attempt_name, exc.category, exc)
            if exc.category in RETRYABLE:
                continue
            break
        finally:
            await gen.aclose()

    outcome.error_message = str(last_error) if last_error else "no models available"
    raise AllModelsUnavailable(outcome.error_message)
