"""Normalize any provider's raw response into the standard Archer/OpenAI shape."""

import time
import uuid

from app.schemas.chat import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionUsage,
    ChatMessage,
)


def normalize_response(raw: dict) -> ChatCompletionResponse:
    """Both providers return OpenAI-shaped bodies; we re-stamp id/model/created
    so the client never sees which provider answered."""
    choice = (raw.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    usage = raw.get("usage") or {}

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4()}",
        created=int(time.time()),
        model="archer-auto",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(
                    role=message.get("role", "assistant"),
                    content=message.get("content", "") or "",
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
