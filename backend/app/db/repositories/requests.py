"""Request-log data access: write logs, paginate, and aggregate dashboard stats."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.proxy import model_cache
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

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # One pass over the logs for all scalar aggregates (FILTER avoids
    # separate round-trips for the conditional counts).
    agg = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(base.c.created_at >= start_of_day),
                func.coalesce(func.sum(base.c.total_tokens), 0),
                func.count().filter(base.c.status == "success"),
                func.count().filter(base.c.created_at >= start_of_month),
            ).select_from(base)
        )
    ).one()
    total_requests = int(agg[0] or 0)
    requests_today = int(agg[1] or 0)
    total_tokens = int(agg[2] or 0)
    successes = int(agg[3] or 0)
    requests_this_month = int(agg[4] or 0)
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
        "requests_this_month": requests_this_month,
        "total_tokens": total_tokens,
        "success_rate": success_rate,
        "most_used_model": most_used[0] if most_used else None,
    }


async def platform_stats(db: AsyncSession) -> dict:
    """Admin overview: request totals across ALL users (no per-user filter)."""
    start_of_day = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    agg = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(RequestLog.created_at >= start_of_day),
                func.count().filter(RequestLog.status == "error"),
                func.count().filter(RequestLog.fallback_used.is_(True)),
            )
        )
    ).one()
    total = int(agg[0] or 0)
    return {
        "total_requests": total,
        "requests_today": int(agg[1] or 0),
        "error_rate": round(int(agg[2] or 0) / total * 100, 2) if total else 0.0,
        "fallback_rate": round(int(agg[3] or 0) / total * 100, 2) if total else 0.0,
    }


async def platform_usage_daily(db: AsyncSession, days: int) -> list[dict]:
    """Platform-wide per-day requests / tokens / errors (same shape as the
    per-user version, without the api_key join)."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(RequestLog.created_at)
    rows = (
        await db.execute(
            select(
                day.label("day"),
                func.count(),
                func.coalesce(func.sum(RequestLog.total_tokens), 0),
                func.count().filter(RequestLog.status == "error"),
            )
            .where(RequestLog.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    return [
        {"day": r[0], "requests": int(r[1]), "tokens": int(r[2]), "errors": int(r[3])}
        for r in rows
    ]


async def platform_model_distribution(db: AsyncSession, days: int) -> list[dict]:
    """Platform-wide top models over the window."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(Model.display_name, func.count())
            .select_from(RequestLog)
            .join(Model, Model.id == RequestLog.model_id)
            .where(RequestLog.created_at >= since)
            .group_by(Model.display_name)
            .order_by(func.count().desc())
        )
    ).all()
    return _distribution_from_counts([(name, c) for name, c in rows])


def _shadow_agreement_pct(rows: list[tuple[str, str]]) -> float | None:
    """(shadow_routing_reason, routed_model_name) pairs -> agreement %. Agreement
    = the embedding router's domain would have routed to the same model that was
    actually served. Domain→model is resolved through the live cache (Phase 2E)."""
    if not rows:
        return None

    def domain_model_name(domain: str) -> str | None:
        m = model_cache.domain_model(domain)
        return m.name if m else None

    agree = sum(
        1
        for reason, model in rows
        if domain_model_name(reason.removeprefix("embedding_")) == model
    )
    return round(agree / len(rows) * 100, 2)


async def usage_daily_for_user(db: AsyncSession, user_id: uuid.UUID, days: int) -> list[dict]:
    """Per-day request count, token sum, and error count over the last `days`."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = _user_logs_query(user_id).where(RequestLog.created_at >= since).subquery()
    day = func.date(base.c.created_at)

    rows = (
        await db.execute(
            select(
                day.label("day"),
                func.count(),
                func.coalesce(func.sum(base.c.total_tokens), 0),
                func.count().filter(base.c.status == "error"),
            )
            .select_from(base)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    return [
        {"day": r[0], "requests": int(r[1]), "tokens": int(r[2]), "errors": int(r[3])}
        for r in rows
    ]


def _distribution_from_counts(rows: list[tuple[str, int]]) -> list[dict]:
    """(model_name, count) pairs -> per-model count + percentage of the total."""
    total = sum(c for _, c in rows)
    return [
        {"model": name, "count": int(c), "percentage": round(c / total * 100, 2) if total else 0.0}
        for name, c in rows
    ]


async def model_distribution_for_user(
    db: AsyncSession, user_id: uuid.UUID, days: int
) -> list[dict]:
    """Which models actually answered, and how often, over the last `days`."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = _user_logs_query(user_id).where(RequestLog.created_at >= since).subquery()

    rows = (
        await db.execute(
            select(Model.display_name, func.count())
            .select_from(base)
            .join(Model, Model.id == base.c.model_id)
            .group_by(Model.display_name)
            .order_by(func.count().desc())
        )
    ).all()
    return _distribution_from_counts([(name, c) for name, c in rows])


async def routing_stats_for_user(db: AsyncSession, user_id: uuid.UUID, days: int) -> dict:
    """Phase 2B routing-stats: method split, shadow agreement, fallback rate,
    and average latency / time-to-first-token over the last `days`."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    base = _user_logs_query(user_id).where(RequestLog.created_at >= since).subquery()

    agg = (
        await db.execute(
            select(
                func.count(),
                func.count().filter(base.c.routing_method == "embedding"),
                func.count().filter(base.c.routing_method == "keyword"),
                func.count().filter(base.c.fallback_used.is_(True)),
                func.avg(base.c.latency_ms),
                func.avg(base.c.time_to_first_token_ms),
            ).select_from(base)
        )
    ).one()
    total = int(agg[0] or 0)
    embedding_count = int(agg[1] or 0)
    keyword_count = int(agg[2] or 0)
    fallback_count = int(agg[3] or 0)

    # Shadow rows: embedding's choice vs the routed model (original pick if a
    # provider-level fallback fired, else the served model).
    routed = aliased(Model)
    routed_id = func.coalesce(base.c.original_model_id, base.c.model_id)
    shadow_rows = (
        await db.execute(
            select(base.c.shadow_routing_reason, routed.name)
            .select_from(base)
            .join(routed, routed.id == routed_id)
            .where(base.c.shadow_routing_reason.isnot(None))
        )
    ).all()

    return {
        "days": days,
        "total_requests": total,
        "keyword_count": keyword_count,
        "embedding_count": embedding_count,
        "shadow_agreement_pct": _shadow_agreement_pct([(r, m) for r, m in shadow_rows]),
        "fallback_rate": round(fallback_count / total * 100, 2) if total else 0.0,
        "avg_latency_ms": round(float(agg[4]), 2) if agg[4] is not None else None,
        "avg_time_to_first_token_ms": round(float(agg[5]), 2) if agg[5] is not None else None,
    }
