"""Provider call with fallback chain + an in-memory model cache.

The cache is populated once at startup (see app.main lifespan) so the hot path
never hits Postgres for model metadata.
"""

import logging
import uuid
from dataclasses import dataclass

from app.core.normalizer import normalize_response
from app.db.models import Model
from app.providers import ProviderError, get_provider
from app.providers.base import RETRYABLE
from app.schemas.chat import ChatCompletionResponse, ChatMessage

logger = logging.getLogger("archer.proxy")

# Fixed fallback order (context.md §5.9, Archer-corrected for Groq deprecations).
FALLBACK_CHAIN = [
    "llama-3.3-70b-groq",
    "gpt-oss-120b-groq",
    "llama-3.1-8b-groq",
    "qwen-2.5-72b-or",
    "gpt-oss-20b-groq",
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
            if exc.category in RETRYABLE or exc.category == "client_error":
                continue
            continue

        is_fallback = model.name != selected_name and selected is not None
        return ProxyResult(
            response=normalize_response(raw),
            model=model,
            original_model=selected if is_fallback else None,
            fallback_used=is_fallback,
            routing_reason=f"{routing_reason}_fallback" if is_fallback else routing_reason,
        )

    raise AllModelsUnavailable(str(last_error) if last_error else "no models available")
