"""call_with_fallback — fallback walks the chain on retryable errors but must
NOT fan out on a client_error (the Tier-1 fix)."""

import pytest

from app.core import proxy
from app.core.proxy import AllModelsUnavailable, call_with_fallback, model_cache
from app.db.models import Model
from app.providers.base import ProviderError
from app.schemas.chat import ChatMessage

CHAIN = [
    "llama-3.3-70b-groq",
    "gpt-oss-120b-groq",
    "llama-3.1-8b-groq",
    "qwen-2.5-72b-or",
    "gpt-oss-20b-groq",
]

OK = {"choices": [{"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}]}


class FakeProvider:
    """Records each call; raises or returns based on the model_id behavior map."""

    def __init__(self, behavior, calls):
        self.behavior = behavior
        self.calls = calls

    async def chat(self, model_id, messages, temperature, max_tokens):
        self.calls.append(model_id)
        outcome = self.behavior.get(model_id, OK)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome


@pytest.fixture(autouse=True)
def _load_models():
    model_cache.load([Model(name=n, provider="groq", model_id=n, is_active=True) for n in CHAIN])


@pytest.fixture
def messages():
    return [ChatMessage(role="user", content="hi")]


def _patch(monkeypatch, behavior):
    calls: list[str] = []
    monkeypatch.setattr(proxy, "get_provider", lambda _name: FakeProvider(behavior, calls))
    return calls


async def test_selected_succeeds_without_fallback(monkeypatch, messages):
    calls = _patch(monkeypatch, {})
    result = await call_with_fallback("gpt-oss-120b-groq", "math_keywords", messages, 1.0, 128)

    assert result.fallback_used is False
    assert result.routing_reason == "math_keywords"
    assert result.model.name == "gpt-oss-120b-groq"
    assert calls == ["gpt-oss-120b-groq"]


async def test_retryable_error_walks_to_next_model(monkeypatch, messages):
    calls = _patch(monkeypatch, {"llama-3.3-70b-groq": ProviderError("rate_limit", "429")})
    result = await call_with_fallback("llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128)

    assert result.fallback_used is True
    assert result.routing_reason == "coding_keywords_fallback"
    assert result.model.name == "gpt-oss-120b-groq"
    assert calls == ["llama-3.3-70b-groq", "gpt-oss-120b-groq"]


async def test_client_error_stops_the_chain(monkeypatch, messages):
    calls = _patch(monkeypatch, {"llama-3.3-70b-groq": ProviderError("client_error", "400")})

    with pytest.raises(AllModelsUnavailable):
        await call_with_fallback("llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128)

    # Did NOT fan out to the other four models.
    assert calls == ["llama-3.3-70b-groq"]
