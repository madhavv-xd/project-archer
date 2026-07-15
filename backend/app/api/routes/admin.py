"""Admin panel (Phase 2E) — role-gated model CRUD, platform overview, moderation.

Every route requires an admin JWT (router-level require_admin). Model writes
refresh the in-memory cache in the same request, so routing/fallback reflect the
change without a restart (single-process deploy — design.md decision 9)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import require_admin
from app.core.proxy import model_cache
from app.db.database import get_db
from app.db.repositories import api_keys as api_keys_repo
from app.db.repositories import models as models_repo
from app.db.repositories import requests as requests_repo
from app.db.repositories import users as users_repo
from app.schemas.admin import (
    AdminModelResponse,
    AdminUserResponse,
    ModelCreate,
    ModelUpdate,
    PlatformOverview,
    SetActive,
)
from app.schemas.common import PaginatedResponse
from app.schemas.logs import ModelDistributionEntry, UsageDailyEntry

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


async def _refresh_cache(db: AsyncSession) -> None:
    model_cache.load(await models_repo.list_all(db))


# --- Model management ------------------------------------------------------


@router.get("/models", response_model=list[AdminModelResponse])
async def list_models(db: AsyncSession = Depends(get_db)) -> list[AdminModelResponse]:
    return [AdminModelResponse.model_validate(m) for m in await models_repo.list_all(db)]


@router.post("/models", response_model=AdminModelResponse, status_code=status.HTTP_201_CREATED)
async def create_model(body: ModelCreate, db: AsyncSession = Depends(get_db)) -> AdminModelResponse:
    model = await models_repo.create(db, **body.model_dump())
    await _refresh_cache(db)
    return AdminModelResponse.model_validate(model)


@router.patch("/models/{model_id}", response_model=AdminModelResponse)
async def update_model(
    model_id: uuid.UUID, body: ModelUpdate, db: AsyncSession = Depends(get_db)
) -> AdminModelResponse:
    model = await models_repo.get_by_id(db, model_id)
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model not found")
    model = await models_repo.update(db, model, **body.model_dump(exclude_unset=True))
    await _refresh_cache(db)
    return AdminModelResponse.model_validate(model)


# --- Platform overview -----------------------------------------------------


@router.get("/overview", response_model=PlatformOverview)
async def overview(db: AsyncSession = Depends(get_db)) -> PlatformOverview:
    stats = await requests_repo.platform_stats(db)
    return PlatformOverview(total_users=await users_repo.count(db), **stats)


@router.get("/usage-daily", response_model=list[UsageDailyEntry])
async def usage_daily(
    days: int = 30, db: AsyncSession = Depends(get_db)
) -> list[UsageDailyEntry]:
    return [UsageDailyEntry(**r) for r in await requests_repo.platform_usage_daily(db, days)]


@router.get("/model-distribution", response_model=list[ModelDistributionEntry])
async def model_distribution(
    days: int = 30, db: AsyncSession = Depends(get_db)
) -> list[ModelDistributionEntry]:
    rows = await requests_repo.platform_model_distribution(db, days)
    return [ModelDistributionEntry(**r) for r in rows]


# --- User & key moderation -------------------------------------------------


@router.get("/users", response_model=PaginatedResponse[AdminUserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[AdminUserResponse]:
    rows, total = await users_repo.list_with_request_counts(db, page=page, limit=limit)
    items = [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            plan=u.plan,
            role=u.role,
            is_active=u.is_active,
            request_count=count,
            created_at=u.created_at,
        )
        for u, count in rows
    ]
    return PaginatedResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def set_user_active(
    user_id: uuid.UUID, body: SetActive, db: AsyncSession = Depends(get_db)
) -> AdminUserResponse:
    user = await users_repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user = await users_repo.set_active(db, user, body.is_active)
    return AdminUserResponse.model_validate(user)


@router.patch("/api-keys/{key_id}")
async def set_key_active(
    key_id: uuid.UUID, body: SetActive, db: AsyncSession = Depends(get_db)
) -> dict:
    key = await api_keys_repo.get_by_id(db, key_id)
    if key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    await api_keys_repo.set_active(db, key, body.is_active)
    return {"id": str(key.id), "is_active": key.is_active}
