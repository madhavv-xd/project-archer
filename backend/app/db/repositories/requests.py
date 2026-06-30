"""Request-log data access: write logs, paginate, and aggregate dashboard stats."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiKey, Model, RequestLog


async def create_log(db: AsyncSession, **fields) -> RequestLog:
    log = RequestLog(**fields)
    db.add(log)
    await db.commit()
    return log


def _user_logs_query(user_id: uuid.UUID):
    """Logs belong to a user via api_keys.user_id."""
    return (
        select(RequestLog)
        .join(ApiKey, RequestLog.api_key_id == ApiKey.id)
        .where(ApiKey.user_id == user_id)
    )


async def list_for_user(
    db: AsyncSession, *, user_id: uuid.UUID, page: int, limit: int
) -> tuple[list[RequestLog], int]:
    base = _user_logs_query(user_id)

    total = await db.scalar(
        select(func.count()).select_from(base.subquery())
    )

    result = await db.execute(
        base.order_by(RequestLog.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    return list(result.scalars().all()), int(total or 0)


async def recent_for_user(
    db: AsyncSession, *, user_id: uuid.UUID, limit: int = 10
) -> list[RequestLog]:
    result = await db.execute(
        _user_logs_query(user_id).order_by(RequestLog.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def stats_for_user(db: AsyncSession, user_id: uuid.UUID) -> dict:
    base = _user_logs_query(user_id).subquery()

    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # One pass over the logs for all four scalar aggregates (FILTER avoids
    # separate round-trips for the conditional counts).
    agg = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(base.c.created_at >= start_of_day),
                func.coalesce(func.sum(base.c.total_tokens), 0),
                func.count().filter(base.c.status == "success"),
            ).select_from(base)
        )
    ).one()
    total_requests = int(agg[0] or 0)
    requests_today = int(agg[1] or 0)
    total_tokens = int(agg[2] or 0)
    successes = int(agg[3] or 0)
    success_rate = round((successes / total_requests) * 100, 2) if total_requests else 0.0

    # Most-used model (by name)
    most_used_row = await db.execute(
        select(Model.display_name, func.count().label("c"))
        .select_from(base)
        .join(Model, Model.id == base.c.model_id)
        .group_by(Model.display_name)
        .order_by(func.count().desc())
        .limit(1)
    )
    most_used = most_used_row.first()

    return {
        "total_requests": total_requests,
        "requests_today": requests_today,
        "total_tokens": total_tokens,
        "success_rate": success_rate,
        "most_used_model": most_used[0] if most_used else None,
    }
