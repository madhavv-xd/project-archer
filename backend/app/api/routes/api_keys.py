"""API key management (JWT-protected). Full key is shown exactly once."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.core.security import generate_api_key, hash_api_key
from app.db.database import get_db
from app.db.models import User
from app.db.repositories import api_keys as api_keys_repo
from app.schemas.api_keys import ApiKeyResponse, CreateApiKeyRequest, CreatedApiKeyResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ApiKeyResponse]:
    keys = await api_keys_repo.list_for_user(db, user.id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("", response_model=CreatedApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: CreateApiKeyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreatedApiKeyResponse:
    full_key = generate_api_key()
    prefix = full_key[:12]
    api_key = await api_keys_repo.create(
        db, user_id=user.id, name=body.name, key_hash=hash_api_key(full_key), key_prefix=prefix
    )
    # The only time the plaintext key is ever returned.
    return CreatedApiKeyResponse(id=api_key.id, name=api_key.name, key=full_key, prefix=prefix)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    api_key = await api_keys_repo.get_for_user(db, user_id=user.id, key_id=key_id)
    if api_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    await api_keys_repo.delete(db, api_key)
