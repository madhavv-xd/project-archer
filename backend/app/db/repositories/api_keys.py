"""API key data access."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ApiKey


async def list_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession, *, user_id: uuid.UUID, name: str, key_hash: str, key_prefix: str
) -> ApiKey:
    api_key = ApiKey(user_id=user_id, name=name, key_hash=key_hash, key_prefix=key_prefix)
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def get_for_user(db: AsyncSession, *, user_id: uuid.UUID, key_id: uuid.UUID) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete(db: AsyncSession, api_key: ApiKey) -> None:
    await db.delete(api_key)
    await db.commit()


async def get_by_id(db: AsyncSession, key_id: uuid.UUID) -> ApiKey | None:
    """Global lookup (any owner) — for admin moderation."""
    return await db.get(ApiKey, key_id)


async def set_active(db: AsyncSession, api_key: ApiKey, is_active: bool) -> ApiKey:
    api_key.is_active = is_active
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def get_with_user_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    """Used by API-key auth. Eager-loads the owning user."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash).options(selectinload(ApiKey.user))
    )
    return result.scalar_one_or_none()


async def touch_last_used(db: AsyncSession, key_id: uuid.UUID) -> None:
    """Fire-and-forget update of last_used_at; runs in its own commit."""
    await db.execute(
        update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()
