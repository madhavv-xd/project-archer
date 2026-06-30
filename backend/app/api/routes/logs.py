"""Paginated request logs (JWT-protected)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.core.proxy import model_cache
from app.db.database import get_db
from app.db.models import RequestLog, User
from app.db.repositories import requests as requests_repo
from app.schemas.common import PaginatedResponse
from app.schemas.logs import RequestLogResponse

router = APIRouter(prefix="/logs", tags=["logs"])


def _to_response(log: RequestLog) -> RequestLogResponse:
    model = model_cache.get_by_id(log.model_id)
    return RequestLogResponse(
        id=log.id,
        model=model.display_name if model else None,
        routing_reason=log.routing_reason,
        prompt_tokens=log.prompt_tokens,
        completion_tokens=log.completion_tokens,
        total_tokens=log.total_tokens,
        latency_ms=log.latency_ms,
        status=log.status,
        fallback_used=log.fallback_used,
        created_at=log.created_at,
    )


@router.get("", response_model=PaginatedResponse[RequestLogResponse])
async def list_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[RequestLogResponse]:
    logs, total = await requests_repo.list_for_user(db, user_id=user.id, page=page, limit=limit)
    total_pages = (total + limit - 1) // limit
    return PaginatedResponse(
        items=[_to_response(log) for log in logs],
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )
