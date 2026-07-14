"""Dashboard stats (JWT-protected)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.repositories import requests as requests_repo
from app.schemas.logs import (
    DashboardStats,
    ModelDistributionEntry,
    RoutingStats,
    UsageDailyEntry,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def stats(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DashboardStats:
    return DashboardStats(**await requests_repo.stats_for_user(db, user.id))


@router.get("/routing-stats", response_model=RoutingStats)
async def routing_stats(
    days: int = 7,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoutingStats:
    return RoutingStats(**await requests_repo.routing_stats_for_user(db, user.id, days))


@router.get("/usage-daily", response_model=list[UsageDailyEntry])
async def usage_daily(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UsageDailyEntry]:
    rows = await requests_repo.usage_daily_for_user(db, user.id, days)
    return [UsageDailyEntry(**r) for r in rows]


@router.get("/model-distribution", response_model=list[ModelDistributionEntry])
async def model_distribution(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModelDistributionEntry]:
    rows = await requests_repo.model_distribution_for_user(db, user.id, days)
    return [ModelDistributionEntry(**r) for r in rows]
