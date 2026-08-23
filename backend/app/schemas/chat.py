"""OpenAI-compatible chat completion request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field

ReasoningEffort = Literal["low", "medium", "high"]


class ChatMessage(BaseModel):
    role: str
    content: str
    # Response-side only, and additive: present only when the caller asked for
    # reasoning and the answering model produced some. Routes serialize with
    # exclude_none so existing clients never see the key at all.
    reasoning: str | None = None


class ChatCompletionRequest(BaseModel):
    # NOTE: the `model` field is accepted for OpenAI compatibility but IGNORED —
    # Archer always decides which model answers.
    model: str | None = None
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = 1.0
    max_tokens: int = 2048
    stream: bool = False
    # One Archer-level intent; providers/base.py translates it into whatever the
    # answering model's provider actually accepts (see models.reasoning_mode).
    # Off by default: reasoning tokens are the dominant latency on most of the
    # catalog, so the fastest correct answer is what you get unless you ask.
    reasoning: bool = False
    reasoning_effort: ReasoningEffort = "medium"


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = "archer-auto"
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage
