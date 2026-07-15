"""call_with_fallback — fallback walks the chain on retryable errors but must
NOT fan out on a client_error (the Tier-1 fix)."""

import json

import pytest

from app.core import proxy
from app.core.proxy import (
    AllModelsUnavailable,
    StreamOutcome,
    call_with_fallback,
    model_cache,
    stream_with_fallback,
)
from app.providers.base import ProviderError
from app.schemas.chat import ChatMessage

from tests.conftest import CATALOG, catalog_models

# Fallback order = catalog sorted by fallback_priority (the DB-driven chain).
CHAIN = [name for name, _priority, _domains in sorted(CATALOG, key=lambda r: r[1])]

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
    model_cache.load(catalog_models())


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
    assert result.model.name == "llama-4-scout-groq"  # next in FALLBACK_CHAIN
    assert calls == ["llama-3.3-70b-groq", "llama-4-scout-groq"]


async def test_client_error_stops_the_chain(monkeypatch, messages):
    calls = _patch(monkeypatch, {"llama-3.3-70b-groq": ProviderError("client_error", "400")})

    with pytest.raises(AllModelsUnavailable):
        await call_with_fallback("llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128)

    # Did NOT fan out to the other four models.
    assert calls == ["llama-3.3-70b-groq"]


# ---- streaming (stream_with_fallback) ----------------------------------------

def _content_line(text: str) -> str:
    return f'data: {json.dumps({"choices": [{"delta": {"content": text}}]})}'


def _usage_line(total: int) -> str:
    usage = {"prompt_tokens": 1, "completion_tokens": total - 1, "total_tokens": total}
    return f'data: {json.dumps({"choices": [], "usage": usage})}'


class FakeStreamProvider:
    """behavior[model_id] = (list_of_raw_lines, ProviderError | None).

    Empty lines + an error models a pre-first-byte failure; lines then an error
    models a mid-stream interruption; lines then None is a clean stream.
    """

    DEFAULT = ([_content_line("hello"), _usage_line(10)], None)

    def __init__(self, behavior, calls):
        self.behavior = behavior
        self.calls = calls

    async def stream(self, model_id, messages, temperature, max_tokens):
        self.calls.append(model_id)
        lines, err = self.behavior.get(model_id, self.DEFAULT)
        for line in lines:
            yield line
        if err is not None:
            raise err


def _patch_stream(monkeypatch, behavior):
    calls: list[str] = []
    monkeypatch.setattr(proxy, "get_provider", lambda _name: FakeStreamProvider(behavior, calls))
    return calls


async def _drain(agen) -> list[str]:
    return [chunk async for chunk in agen]


async def test_stream_fallback_before_first_byte(monkeypatch, messages):
    calls = _patch_stream(
        monkeypatch, {"llama-3.3-70b-groq": ([], ProviderError("rate_limit", "429"))}
    )
    outcome = StreamOutcome()
    chunks = await _drain(
        stream_with_fallback(
            "llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128, "chatcmpl-x", outcome
        )
    )

    assert outcome.fallback_used is True
    assert outcome.model.name == "llama-4-scout-groq"  # next in FALLBACK_CHAIN
    assert outcome.original_model.name == "llama-3.3-70b-groq"
    assert outcome.routing_reason == "coding_keywords_fallback"
    assert outcome.ttft_ms is not None
    assert outcome.usage["total_tokens"] == 10
    assert outcome.interrupted is False
    assert calls == ["llama-3.3-70b-groq", "llama-4-scout-groq"]
    assert chunks[-1] == "data: [DONE]\n\n"


async def test_stream_interrupt_after_first_byte_does_not_switch(monkeypatch, messages):
    calls = _patch_stream(
        monkeypatch,
        {"gpt-oss-120b-groq": ([_content_line("partial")], ProviderError("server_error", "boom"))},
    )
    outcome = StreamOutcome()
    chunks = await _drain(
        stream_with_fallback(
            "gpt-oss-120b-groq", "math_keywords", messages, 1.0, 128, "chatcmpl-y", outcome
        )
    )

    assert outcome.interrupted is True
    assert outcome.error_message.startswith("stream_interrupted")
    assert outcome.model.name == "gpt-oss-120b-groq"
    assert outcome.fallback_used is False
    # Committed after first byte — no other model tried.
    assert calls == ["gpt-oss-120b-groq"]
    assert chunks[-1] == "data: [DONE]\n\n"


async def test_stream_all_fail_before_byte_raises(monkeypatch, messages):
    behavior = {n: ([], ProviderError("server_error", "down")) for n in CHAIN}
    calls = _patch_stream(monkeypatch, behavior)
    outcome = StreamOutcome()

    with pytest.raises(AllModelsUnavailable):
        await _drain(
            stream_with_fallback(
                "llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128, "chatcmpl-z", outcome
            )
        )

    assert outcome.forwarded_any is False
    assert calls == CHAIN


async def test_stream_client_error_stops_chain(monkeypatch, messages):
    calls = _patch_stream(
        monkeypatch, {"llama-3.3-70b-groq": ([], ProviderError("client_error", "400"))}
    )
    outcome = StreamOutcome()

    with pytest.raises(AllModelsUnavailable):
        await _drain(
            stream_with_fallback(
                "llama-3.3-70b-groq", "coding_keywords", messages, 1.0, 128, "chatcmpl-c", outcome
            )
        )

    assert calls == ["llama-3.3-70b-groq"]
