"""Archer — FastAPI entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    yield
    # Shutdown: close the shared provider HTTP client.
    await close_client()


app = FastAPI(title="Archer", version=health.VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(api_keys.router)
app.include_router(models.router)
app.include_router(logs.router)
app.include_router(dashboard.router)
app.include_router(chat.router)

#for running -> uv run uvicorn app.main:app --reload --port 8000