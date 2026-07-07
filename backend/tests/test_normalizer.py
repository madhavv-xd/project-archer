"""Normalizer — every provider body must come out in the archer-auto shape."""

import json

from app.core.normalizer import normalize_chunk, normalize_response


def test_normalizes_to_archer_auto():
    raw = {
        "choices": [
            {"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    }
    out = normalize_response(raw)

    assert out.model == "archer-auto"
    assert out.id.startswith("chatcmpl-")
    assert out.choices[0].message.content == "hello"
    assert out.choices[0].finish_reason == "stop"
    assert out.usage.total_tokens == 8


def test_handles_missing_fields_with_defaults():
    out = normalize_response({})

    assert out.model == "archer-auto"
    assert out.choices[0].message.role == "assistant"
    assert out.choices[0].message.content == ""
    assert out.choices[0].finish_reason == "stop"
    assert out.usage.prompt_tokens == 0
    assert out.usage.completion_tokens == 0
    assert out.usage.total_tokens == 0


ARCHER_ID = "chatcmpl-fixed-id"


def _payload(line: str) -> dict:
    assert line is not None
    assert line.startswith("data: ") and line.endswith("\n\n")
    return json.loads(line[len("data: "):].strip())


def test_chunk_restamps_model_and_id():
    raw = 'data: {"id": "provider-xyz", "model": "llama-3.3-70b-versatile", ' \
          '"choices": [{"delta": {"content": "Hi"}}], "x_groq": {"id": "req_1"}}'
    obj = _payload(normalize_chunk(raw, ARCHER_ID))

    assert obj["model"] == "archer-auto"
    assert obj["id"] == ARCHER_ID
    assert "x_groq" not in obj
    assert obj["choices"][0]["delta"]["content"] == "Hi"


def test_chunk_malformed_json_dropped():
    assert normalize_chunk("data: {not valid json", ARCHER_ID) is None


def test_chunk_done_and_empty_return_none():
    assert normalize_chunk("data: [DONE]", ARCHER_ID) is None
    assert normalize_chunk("", ARCHER_ID) is None
    assert normalize_chunk(": keep-alive comment", ARCHER_ID) is None


def test_usage_chunk_passthrough_restamped():
    raw = 'data: {"id": "p", "model": "m", "choices": [], ' \
          '"usage": {"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10}}'
    obj = _payload(normalize_chunk(raw, ARCHER_ID))

    assert obj["model"] == "archer-auto"
    assert obj["id"] == ARCHER_ID
    assert obj["usage"]["total_tokens"] == 10
