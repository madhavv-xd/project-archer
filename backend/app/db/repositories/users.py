"""User data access."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiKey, RequestLog, User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def create(
    db: AsyncSession, *, email: str, password_hash: str | None = None, name: str | None = None
) -> User:
    user = User(email=email, password_hash=password_hash, name=name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def count(db: AsyncSession) -> int:
    return int(await db.scalar(select(func.count()).select_from(User)) or 0)


async def list_with_request_counts(
    db: AsyncSession, *, page: int, limit: int
) -> tuple[list[tuple[User, int]], int]:
    """Admin moderation list: each user with their total request count (across
    all their keys), newest first."""
    total = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    rows = (
        await db.execute(
            select(User, func.count(RequestLog.id))
            .outerjoin(ApiKey, ApiKey.user_id == User.id)
            .outerjoin(RequestLog, RequestLog.api_key_id == ApiKey.id)
            .group_by(User.id)
            .order_by(User.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()
    return [(u, int(c)) for u, c in rows], total


async def set_active(db: AsyncSession, user: User, is_active: bool) -> User:
    user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user
