"""Model catalog (JWT-protected dashboard view)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.db.repositories import models as models_repo
from app.schemas.models import ModelResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelResponse])
async def list_models(
    _user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ModelResponse]:
    models = await models_repo.list_all(db)
    return [ModelResponse.model_validate(m) for m in models]
