"""The answer contract: `content` is the answer, never the model's scratchpad.

Two halves, matching the two ways providers leak reasoning — inline `<think>`
tags (qwen3.6) and a sibling `reasoning` field (everything else) — plus the
per-model effort vocabulary, where a wrong value is a non-retryable HTTP 400.
"""

import json

import pytest

from app.core.normalizer import StreamNormalizer, ThinkStripper, normalize_response, strip_think
from app.providers.base import reasoning_params

ARCHER_ID = "chatcmpl-fixed"


# --- inline <think> stripping ------------------------------------------------


def _feed_in_pieces(text: str, size: int) -> str:
    """Stream `text` through the stripper in fixed-size slices."""
    stripper = ThinkStripper()
    out = "".join(stripper.feed(text[i : i + size]) for i in range(0, len(text), size))
    return out + stripper.flush()


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("<think>deliberating</think>120 miles", "120 miles"),
        ("before<think>mid</think>after", "beforeafter"),
        ("no tags at all", "no tags at all"),
        ("<think>only reasoning</think>", ""),
        ("a<think>x</think>b<think>y</think>c", "abc"),
        # A lone angle bracket is content, not the start of a tag.
        ("5 < 7 and 8 > 2", "5 < 7 and 8 > 2"),
        ("ends with a bare <", "ends with a bare <"),
    ],
)
def test_strip_think_whole_text(raw, expected):
    assert strip_think(raw) == expected


@pytest.mark.parametrize("chunk_size", [1, 2, 3, 5, 7, 11])
def test_strip_think_survives_any_chunk_boundary(chunk_size):
    """The tags straddle chunk boundaries in real streams — a chunk ending in
    `<thi` must not be forwarded before the next chunk resolves it."""
    raw = "Answer: <think>step one, step two</think>120 miles. <think>check</think>Done."
    assert _feed_in_pieces(raw, chunk_size) == "Answer: 120 miles. Done."


def test_stripper_holds_back_at_most_a_tag():
    """Bounded lookahead: withholding more than a partial tag would show up
    directly as worse time-to-first-token."""
    stripper = ThinkStripper()
    emitted = stripper.feed("a long stretch of ordinary answer text<thi")
    assert emitted == "a long stretch of ordinary answer text"
    assert stripper.feed("nk>hidden</think>tail") == "tail"


def test_unterminated_tag_fragment_is_flushed_as_content():
    stripper = ThinkStripper()
    assert stripper.feed("done<th") == "done"
    assert stripper.flush() == "<th"


# --- non-streaming responses -------------------------------------------------


def _body(content: str, reasoning: str | None = None) -> dict:
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning"] = reasoning
    return {"choices": [{"message": message, "finish_reason": "stop"}]}


def test_inline_think_stripped_from_response():
    out = normalize_response(_body("<think>scratch</think>120 miles"))
    assert out.choices[0].message.content == "120 miles"


def test_sibling_reasoning_dropped_when_not_requested():
    out = normalize_response(_body("120 miles", reasoning="scratch"))
    assert out.choices[0].message.content == "120 miles"
    assert out.choices[0].message.reasoning is None


def test_sibling_reasoning_kept_when_requested():
    out = normalize_response(_body("120 miles", reasoning="scratch"), include_reasoning=True)
    assert out.choices[0].message.reasoning == "scratch"
    assert out.choices[0].message.content == "120 miles"


# --- streaming ---------------------------------------------------------------


def _line(delta: dict) -> str:
    return "data: " + json.dumps({"id": "p", "model": "m", "choices": [{"delta": delta}]})


def _content_of(chunks: list[str]) -> str:
    text = ""
    for chunk in chunks:
        obj = json.loads(chunk[len("data: ") :])
        for choice in obj.get("choices") or []:
            text += (choice.get("delta") or {}).get("content") or ""
    return text


def test_stream_strips_think_across_chunks():
    normalizer = StreamNormalizer(ARCHER_ID)
    pieces = ["Ans", "wer: <thi", "nk>hid", "den</thi", "nk>120 m", "iles"]
    out = [c for c in (normalizer.normalize(_line({"content": p})) for p in pieces) if c]
    assert _content_of(out) == "Answer: 120 miles"


def test_stream_drops_chunks_that_were_entirely_reasoning():
    """A chunk emptied by stripping renders as a stall if forwarded."""
    normalizer = StreamNormalizer(ARCHER_ID)
    assert normalizer.normalize(_line({"content": "<think>"})) is None
    assert normalizer.normalize(_line({"content": "reasoning"})) is None
    assert normalizer.normalize(_line({"content": "</think>done"})) is not None


def test_stream_reasoning_delta_dropped_or_forwarded():
    off = StreamNormalizer(ARCHER_ID).normalize(_line({"reasoning": "scratch"}))
    assert off is None

    on = StreamNormalizer(ARCHER_ID, include_reasoning=True).normalize(
        _line({"reasoning": "scratch"})
    )
    assert json.loads(on[len("data: ") :])["choices"][0]["delta"]["reasoning"] == "scratch"


def test_stream_reasoning_never_merged_into_content():
    normalizer = StreamNormalizer(ARCHER_ID, include_reasoning=True)
    out = normalizer.normalize(_line({"reasoning": "scratch", "content": "120"}))
    assert _content_of([out]) == "120"


def test_stream_keeps_finish_reason_chunk():
    """The final chunk carries no content — dropping it would truncate clients."""
    normalizer = StreamNormalizer(ARCHER_ID)
    raw = "data: " + json.dumps(
        {"id": "p", "model": "m", "choices": [{"delta": {}, "finish_reason": "stop"}]}
    )
    assert normalizer.normalize(raw) is not None


def test_stream_flush_emits_unresolved_tag_fragment():
    normalizer = StreamNormalizer(ARCHER_ID)
    normalizer.normalize(_line({"content": "done<th"}))
    assert _content_of([normalizer.flush()]) == "<th"


# --- effort vocabulary -------------------------------------------------------


def test_non_reasoning_model_gets_no_reasoning_params():
    """gemma4 doesn't reason on its own but STARTS if sent an effort at all."""
    assert reasoning_params("none", "ollama", reasoning=True, effort="high") == {}
    assert reasoning_params("none", "ollama", reasoning=False, effort="low") == {}


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_toggle_model_never_receives_a_graded_effort(effort):
    """qwen3.6 rejects low/medium/high with HTTP 400 — a client_error, which the
    proxy does not retry, so this would fail the request outright."""
    on = reasoning_params("toggle", "groq", reasoning=True, effort=effort)
    off = reasoning_params("toggle", "groq", reasoning=False, effort=effort)
    assert on["reasoning_effort"] == "default"
    assert off["reasoning_effort"] == "none"
    # reasoning_format is what actually relocates qwen's inline <think>.
    assert on["reasoning_format"] == "parsed"
    assert off["reasoning_format"] == "hidden"


@pytest.mark.parametrize("effort", ["low", "medium", "high"])
def test_effort_model_never_receives_none(effort):
    """gpt-oss rejects `none`; 'off' means minimum effort + hidden output."""
    on = reasoning_params("effort", "groq", reasoning=True, effort=effort)
    off = reasoning_params("effort", "groq", reasoning=False, effort=effort)
    assert on["reasoning_effort"] == effort
    assert off["reasoning_effort"] == "low"
    assert off["reasoning_format"] == "hidden"


def test_effort_optional_model_takes_both():
    on = reasoning_params("effort_optional", "ollama", reasoning=True, effort="high")
    off = reasoning_params("effort_optional", "ollama", reasoning=False, effort="high")
    assert on == {"reasoning_effort": "high"}
    assert off == {"reasoning_effort": "none"}


def test_reasoning_format_is_groq_only():
    """Ollama Cloud 400s on unknown top-level params it doesn't recognize."""
    assert "reasoning_format" not in reasoning_params(
        "effort_optional", "ollama", reasoning=True, effort="low"
    )
