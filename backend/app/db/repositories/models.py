"""Model catalog data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Model


async def list_all(db: AsyncSession) -> list[Model]:
    result = await db.execute(select(Model).order_by(Model.fallback_priority))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, model_id: uuid.UUID) -> Model | None:
    return await db.get(Model, model_id)


async def create(db: AsyncSession, **fields) -> Model:
    model = Model(**fields)
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


async def update(db: AsyncSession, model: Model, **fields) -> Model:
    for key, value in fields.items():
        setattr(model, key, value)
    await db.commit()
    await db.refresh(model)
    return model


async def list_active(db: AsyncSession) -> list[Model]:
    result = await db.execute(
        select(Model).where(Model.is_active.is_(True)).order_by(Model.created_at)
    )
    return list(result.scalars().all())
