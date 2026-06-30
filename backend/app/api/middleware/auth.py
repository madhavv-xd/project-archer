"""Auth dependencies.

- get_current_user: validates a dashboard JWT (Authorization: Bearer <jwt>).
- get_api_key: validates an Archer API key (Authorization: Bearer arch_sk_...).
Both reject inactive users/keys. These are intentionally separate systems.
"""

import asyncio
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, hash_api_key
from app.db.database import AsyncSessionLocal, get_db
from app.db.models import ApiKey, User
from app.db.repositories import api_keys as api_keys_repo
from app.db.repositories import users as users_repo

bearer = HTTPBearer(auto_error=False)


def _require_credentials(creds: HTTPAuthorizationCredentials | None) -> str:
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return creds.credentials


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _require_credentials(creds)
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token subject")

    user = await users_repo.get_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")
    return user


async def _touch_last_used(key_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        await api_keys_repo.touch_last_used(session, key_id)


async def get_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> ApiKey:
    raw_key = _require_credentials(creds)
    api_key = await api_keys_repo.get_with_user_by_hash(db, hash_api_key(raw_key))

    if api_key is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    if not api_key.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "API key is inactive")
    if not api_key.user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is inactive")

    # Fire-and-forget last_used_at update — never blocks the request.
    asyncio.create_task(_touch_last_used(api_key.id))
    return api_key
