"""Normalizer — every provider body must come out in the archer-auto shape."""

from app.core.normalizer import normalize_response


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
