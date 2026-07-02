"""Dashboard auth — register, login (JWT), and OAuth identity resolution."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.db.repositories import oauth_accounts as oauth_repo
from app.db.repositories import users as users_repo
from app.schemas.auth import (
    LoginRequest,
    OAuthUpsertRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    if await users_repo.get_by_email(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = await users_repo.create(
        db, email=body.email, password_hash=hash_password(body.password), name=body.name
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await users_repo.get_by_email(db, body.email)
    if user is None or user.password_hash is None or not verify_password(
        body.password, user.password_hash
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/oauth", response_model=TokenResponse)
async def oauth(
    body: OAuthUpsertRequest,
    x_internal_secret: str = Header(None, alias="X-Internal-Secret"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Server-to-server: resolve an OAuth identity to a backend JWT.

    Called only by NextAuth's server-side `jwt` callback after it has already
    completed the provider handshake, so this endpoint trusts the claimed
    identity — it is guarded by a shared secret, never exposed to clients.
    """
    if not settings.OAUTH_INTERNAL_SECRET or x_internal_secret != settings.OAUTH_INTERNAL_SECRET:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid internal secret")

    # 1. Known OAuth identity → return its user.
    user = await oauth_repo.get_user_by_provider_account(
        db, body.provider, body.provider_account_id
    )
    if user is None:
        # 2. Existing account with this email → link the new provider to it.
        user = await users_repo.get_by_email(db, body.email)
        if user is None:
            # 3. Brand-new user → create passwordless, then link.
            user = await users_repo.create(db, email=body.email, name=body.name)
        await oauth_repo.link(
            db,
            user_id=user.id,
            provider=body.provider,
            provider_account_id=body.provider_account_id,
        )

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is inactive")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))
