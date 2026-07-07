"""The LLM API (API-key protected): POST /v1/chat/completions, GET /v1/models."""

import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.middleware.auth import enforce_limits
from app.core.proxy import (
    AllModelsUnavailable,
    StreamOutcome,
    call_with_fallback,
    model_cache,
    stream_with_fallback,
)
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
    request: Request,
    body: ChatCompletionRequest,
    api_key: ApiKey = Depends(enforce_limits),
):
    if body.stream:
        return await _stream_completion(request, body, api_key)

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


async def _stream_completion(
    request: Request, body: ChatCompletionRequest, api_key: ApiKey
) -> StreamingResponse:
    query = _last_user_message(body)
    selected_name, routing_reason = keyword_route(query)
    selected = model_cache.get(selected_name)
    archer_id = f"chatcmpl-{uuid.uuid4()}"

    outcome = StreamOutcome()
    started = time.perf_counter()
    agen = stream_with_fallback(
        selected_name, routing_reason, body.messages,
        body.temperature, body.max_tokens, archer_id, outcome,
    )

    # Prime the generator: resolve pre-first-byte fallback BEFORE returning a
    # StreamingResponse, so an all-models-fail case still surfaces as HTTP 503
    # rather than a broken 200 stream.
    try:
        first_chunk = await agen.__anext__()
    except StopAsyncIteration:
        first_chunk = None
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
                    is_streaming=True,
                )
            )
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "All models unavailable")

    headers = dict(getattr(request.state, "rate_limit_headers", {}))
    headers["X-Accel-Buffering"] = "no"
    headers["Cache-Control"] = "no-cache"

    async def body_iter():
        try:
            if first_chunk is not None:
                yield first_chunk
            async for chunk in agen:
                yield chunk
        finally:
            latency_ms = int((time.perf_counter() - started) * 1000)
            log_model = outcome.model or selected
            if log_model is not None:
                usage = outcome.usage
                asyncio.create_task(
                    _log(
                        api_key_id=api_key.id,
                        model_id=log_model.id,
                        routing_reason=outcome.routing_reason or routing_reason,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                        latency_ms=latency_ms,
                        time_to_first_token_ms=outcome.ttft_ms,
                        status="error" if outcome.interrupted else "success",
                        error_message=outcome.error_message,
                        fallback_used=outcome.fallback_used,
                        original_model_id=(
                            outcome.original_model.id if outcome.original_model else None
                        ),
                        is_streaming=True,
                    )
                )

    return StreamingResponse(body_iter(), media_type="text/event-stream", headers=headers)


@router.get("/models")
async def list_models(_api_key: ApiKey = Depends(enforce_limits)) -> dict:
    # Archer presents a single virtual model; the real pool is never exposed.
    return {
        "object": "list",
        "data": [{"id": "archer-auto", "object": "model", "owned_by": "archer"}],
    }
