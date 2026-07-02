"""OAuth account data access."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OAuthAccount, User


async def get_user_by_provider_account(
    db: AsyncSession, provider: str, provider_account_id: str
) -> User | None:
    result = await db.execute(
        select(User)
        .join(OAuthAccount, OAuthAccount.user_id == User.id)
        .where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_account_id == provider_account_id,
        )
    )
    return result.scalar_one_or_none()


async def link(
    db: AsyncSession, *, user_id: uuid.UUID, provider: str, provider_account_id: str
) -> OAuthAccount:
    account = OAuthAccount(
        user_id=user_id, provider=provider, provider_account_id=provider_account_id
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account
