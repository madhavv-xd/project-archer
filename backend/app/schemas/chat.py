"""OpenAI-compatible chat completion request/response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    # NOTE: the `model` field is accepted for OpenAI compatibility but IGNORED —
    # Archer always decides which model answers.
    model: str | None = None
    messages: list[ChatMessage] = Field(..., min_length=1)
    temperature: float = 1.0
    max_tokens: int = 2048
    stream: bool = False


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
