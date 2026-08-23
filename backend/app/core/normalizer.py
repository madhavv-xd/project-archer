"""Normalize any provider's raw response into the standard Archer/OpenAI shape.

Beyond re-stamping id/model, this module is where the *answer contract* is
enforced: `content` carries the answer and nothing else. Providers disagree
about where reasoning goes — most return it in a sibling `reasoning` field, but
qwen3.6 inlines it in `content` as ``<think>...</think>`` — and every response
of every provider passes through here, so this is the one place that can
guarantee the contract regardless of which model the router picked.
"""

import json
import time
import uuid

from app.schemas.chat import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
)

_OPEN = "<think>"
_CLOSE = "</think>"


def _held_back(text: str, tag: str) -> int:
    """Length of the trailing slice of `text` that could still grow into `tag`.

    Bounded by len(tag)-1, so streaming never withholds more than a few
    characters — withholding more would show up directly as worse TTFT.
    """
    for size in range(min(len(text), len(tag) - 1), 0, -1):
        if tag.startswith(text[-size:]):
            return size
    return 0


class ThinkStripper:
    """Removes ``<think>...</think>`` blocks from a text stream.

    Stateful because the tags can straddle chunk boundaries: a chunk ending in
    ``<thi`` must not be forwarded until the next chunk decides whether it was a
    tag or literal text.
    """

    def __init__(self) -> None:
        self._inside = False
        self._held = ""

    def feed(self, text: str) -> str:
        buf = self._held + text
        out = []
        while buf:
            if self._inside:
                end = buf.find(_CLOSE)
                if end == -1:
                    # All reasoning; keep only what might be a partial closing tag.
                    keep = _held_back(buf, _CLOSE)
                    self._held = buf[len(buf) - keep:] if keep else ""
                    return "".join(out)
                buf = buf[end + len(_CLOSE):]
                self._inside = False
                continue

            start = buf.find(_OPEN)
            if start == -1:
                keep = _held_back(buf, _OPEN)
                out.append(buf[: len(buf) - keep] if keep else buf)
                self._held = buf[len(buf) - keep:] if keep else ""
                return "".join(out)
            out.append(buf[:start])
            buf = buf[start + len(_OPEN):]
            self._inside = True
        self._held = ""
        return "".join(out)

    def flush(self) -> str:
        """Emit anything held back that never turned out to be a tag."""
        tail = "" if self._inside else self._held
        self._held = ""
        return tail


def strip_think(text: str) -> str:
    stripper = ThinkStripper()
    return stripper.feed(text) + stripper.flush()


def normalize_response(raw: dict, include_reasoning: bool = False) -> ChatCompletionResponse:
    """Both providers return OpenAI-shaped bodies; we re-stamp id/model/created
    so the client never sees which provider answered, and enforce the answer
    contract on `content`."""
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = raw.get("usage") or {}
    reasoning = message.get("reasoning") or None

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        created=int(time.time()),
        model="archer-auto",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(
                    role=message.get("role", "assistant"),
                    content=strip_think(message.get("content", "") or ""),
                    reasoning=reasoning if include_reasoning else None,
                ),
                finish_reason=choice.get("finish_reason", "stop") or "stop",
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
            total_tokens=usage.get("total_tokens", 0) or 0,
        ),
    )


class StreamNormalizer:
    """Re-stamps one provider stream into the archer-auto shape.

    Stateful (one instance per stream): it owns the `<think>` stripper and the
    stable Archer chunk id. `include_reasoning` decides whether the provider's
    separate reasoning channel is forwarded or dropped — it is never merged into
    `content` either way.
    """

    def __init__(self, archer_id: str, include_reasoning: bool = False) -> None:
        self.archer_id = archer_id
        self.include_reasoning = include_reasoning
        self._stripper = ThinkStripper()

    def normalize(self, raw_line: str) -> str | None:
        """Re-stamp one streamed SSE line.

        Returns a serialized ``data: {json}\\n\\n`` line, or None for empty
        lines, the ``[DONE]`` sentinel (the caller emits its own), malformed
        JSON (dropped, not forwarded), and chunks left with nothing to say once
        reasoning has been stripped out. ``model``/``id`` are re-stamped and
        provider extras (e.g. Groq's ``x_groq``) stripped so the client never
        sees the underlying provider.
        """
        line = raw_line.strip()
        if not line.startswith("data:"):
            return None
        data = line[len("data:"):].strip()
        if not data or data == "[DONE]":
            return None
        try:
            obj = json.loads(data)
        except (ValueError, TypeError):
            return None

        obj["model"] = "archer-auto"
        obj["id"] = self.archer_id
        obj.pop("x_groq", None)

        choices = obj.get("choices") or []
        for choice in choices:
            delta = choice.get("delta")
            if not isinstance(delta, dict):
                continue
            if delta.get("content"):
                delta["content"] = self._stripper.feed(delta["content"])
                if not delta["content"]:
                    del delta["content"]  # was reasoning, in full
            if "reasoning" in delta and not self.include_reasoning:
                del delta["reasoning"]

        # A chunk whose every delta emptied out once reasoning was removed says
        # nothing; forwarding it makes clients render a stall. Keep it only if
        # it still carries a finish_reason or usage.
        if (
            choices
            and all(not c.get("delta") and not c.get("finish_reason") for c in choices)
            and not obj.get("usage")
        ):
            return None
        return f"data: {json.dumps(obj)}\n\n"

    def flush(self) -> str | None:
        """Emit any text held back mid-tag-match that never became a tag."""
        tail = self._stripper.flush()
        if not tail:
            return None
        chunk = {
            "id": self.archer_id,
            "object": "chat.completion.chunk",
            "model": "archer-auto",
            "choices": [{"index": 0, "delta": {"content": tail}}],
        }
        return f"data: {json.dumps(chunk)}\n\n"
