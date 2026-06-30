"""Model catalog data access."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Model


async def list_all(db: AsyncSession) -> list[Model]:
    result = await db.execute(select(Model).order_by(Model.created_at))
    return list(result.scalars().all())


async def list_active(db: AsyncSession) -> list[Model]:
    result = await db.execute(
        select(Model).where(Model.is_active.is_(True)).order_by(Model.created_at)
    )
    return list(result.scalars().all())
