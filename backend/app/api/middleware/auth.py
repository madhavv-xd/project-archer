"""Auth dependencies.

- get_current_user: validates a dashboard JWT (Authorization: Bearer <jwt>).
- get_api_key: validates an Archer API key (Authorization: Bearer arch_sk_...).
- enforce_limits: get_api_key + Redis rate limit/quota checks (use on /v1/*).
Both auth schemes reject inactive users/keys and are intentionally separate systems.
"""

import asyncio
import uuid

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.rate_limit import RateLimitExceeded, check_monthly_quota, check_rate_limit
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


async def enforce_limits(
    request: Request,
    response: Response,
    api_key: ApiKey = Depends(get_api_key),
) -> ApiKey:
    """Rate-limit + quota gate for /v1/* — a drop-in replacement for get_api_key.

    No Redis client (REDIS_URL unset) = Phase 1 behavior: no checks, no headers.
    Header values are stashed on request.state for routes that return a Response
    directly (the streaming path), and set on the injected Response for the
    normal JSON path.
    """
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return api_key

    limits = settings.plan_limits.get(api_key.user.plan) or settings.plan_limits["free"]

    rl = await check_rate_limit(redis, api_key.id, limits["rpm"])
    headers = {
        "X-RateLimit-Limit-Requests": str(rl.limit),
        "X-RateLimit-Remaining-Requests": str(rl.remaining),
        "X-RateLimit-Reset-Requests": str(rl.reset_seconds),
    }
    request.state.rate_limit_headers = headers
    response.headers.update(headers)

    if not rl.allowed:
        raise RateLimitExceeded(
            code="rate_limit_exceeded",
            message=(
                f"Rate limit of {rl.limit} requests per minute exceeded. "
                f"Try again in {rl.reset_seconds} seconds."
            ),
            retry_after=rl.reset_seconds,
            headers=headers,
        )

    # Checked second so requests rejected by the RPM limit don't consume quota.
    quota = await check_monthly_quota(redis, api_key.user_id, limits["monthly_requests"])
    if not quota.allowed:
        raise RateLimitExceeded(
            code="monthly_quota_exceeded",
            message=f"Monthly quota of {quota.limit} requests exceeded.",
            retry_after=quota.reset_seconds,
            headers=headers,
        )
    return api_key
