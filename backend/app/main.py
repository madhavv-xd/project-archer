"""Archer — FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as redis_async
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    api_keys,
    auth,
    chat,
    dashboard,
    health,
    logs,
    models,
)
from app.config import settings
from app.core.proxy import model_cache
from app.core.rate_limit import RateLimitExceeded
from app.db.database import AsyncSessionLocal
from app.db.repositories import models as models_repo
from app.providers.base import close_client

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("archer")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Populate the in-memory model cache once, at startup.
    async with AsyncSessionLocal() as session:
        models_list = await models_repo.list_all(session)
    model_cache.load(models_list)
    logger.info("Loaded %d models into cache", len(model_cache))

    # Redis (rate limiting / quotas). Unset REDIS_URL = limits disabled.
    app.state.redis = None
    if settings.REDIS_URL:
        app.state.redis = redis_async.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        logger.info("Redis client configured — rate limiting enabled")
    else:
        logger.warning("REDIS_URL not set — rate limiting and quotas are disabled")

    yield
    # Shutdown: close Redis and the shared provider HTTP client.
    if app.state.redis is not None:
        await app.state.redis.aclose()
    await close_client()


app = FastAPI(title="Archer", version=health.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RateLimitExceeded)
async def _rate_limit_exceeded(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    # OpenAI-style 429 body — HTTPException would wrap it in {"detail": ...}.
    return JSONResponse(
        status_code=429,
        content={
            "error": {"message": exc.message, "type": "rate_limit_error", "code": exc.code}
        },
        headers={**exc.headers, "Retry-After": str(exc.retry_after)},
    )


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(models.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(chat.router)

#for running -> uv run uvicorn app.main:app --reload --port 8000