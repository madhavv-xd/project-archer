"""Dashboard stats (JWT-protected)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.repositories import requests as requests_repo
from app.schemas.logs import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def stats(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DashboardStats:
    return DashboardStats(**await requests_repo.stats_for_user(db, user.id))
