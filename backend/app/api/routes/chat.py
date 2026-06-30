"""The LLM API (API-key protected): POST /v1/chat/completions, GET /v1/models."""

import asyncio
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.middleware.auth import get_api_key
from app.core.proxy import AllModelsUnavailable, call_with_fallback, model_cache
from app.core.router import keyword_route
from app.db.database import AsyncSessionLocal
from app.db.models import ApiKey
from app.db.repositories import requests as requests_repo
from app.schemas.chat import ChatCompletionRequest, ChatCompletionResponse

logger = logging.getLogger("archer.chat")

router = APIRouter(prefix="/v1", tags=["llm-api"])


def _last_user_message(body: ChatCompletionRequest) -> str:
    for msg in reversed(body.messages):
        if msg.role == "user":
            return msg.content
    return body.messages[-1].content


async def _log(**fields) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await requests_repo.create_log(session, **fields)
    except Exception:  # logging must never surface to the client
        logger.exception("failed to write request log")


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest, api_key: ApiKey = Depends(get_api_key)
) -> ChatCompletionResponse:
    if body.stream:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Streaming is not supported in Phase 1")

    query = _last_user_message(body)
    selected_name, routing_reason = keyword_route(query)
    selected = model_cache.get(selected_name)

    started = time.perf_counter()
    try:
        result = await call_with_fallback(
            selected_name, routing_reason, body.messages, body.temperature, body.max_tokens
        )
    except AllModelsUnavailable as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        if selected is not None:
            asyncio.create_task(
                _log(
                    api_key_id=api_key.id,
                    model_id=selected.id,
                    routing_reason=routing_reason,
                    latency_ms=latency_ms,
                    status="error",
                    error_message=str(exc),
                    fallback_used=True,
                )
            )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "All models unavailable")

    latency_ms = int((time.perf_counter() - started) * 1000)
    usage = result.response.usage

    asyncio.create_task(
        _log(
            api_key_id=api_key.id,
            model_id=result.model.id,
            routing_reason=result.routing_reason,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
            status="success",
            fallback_used=result.fallback_used,
            original_model_id=result.original_model.id if result.original_model else None,
        )
    )
    return result.response


@router.get("/models")
async def list_models(_api_key: ApiKey = Depends(get_api_key)) -> dict:
    # Archer presents a single virtual model; the real pool is never exposed.
    return {
        "object": "list",
        "data": [{"id": "archer-auto", "object": "model", "owned_by": "archer"}],
    }
