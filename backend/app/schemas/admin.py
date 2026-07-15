"""Admin-panel schemas (Phase 2E). Model CRUD, platform overview, moderation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.models import ModelResponse


class AdminModelResponse(ModelResponse):
    """Full catalog row incl. the DB-driven routing config."""

    routing_domains: list[str]
    fallback_priority: int


class ModelCreate(BaseModel):
    name: str
    display_name: str
    provider: str
    model_id: str
    context_window: int
    speed_tier: str
    best_for: list[str] = []
    routing_domains: list[str] = []
    fallback_priority: int
    is_active: bool = True


class ModelUpdate(BaseModel):
    """Partial edit — only supplied fields change. `name` is immutable (routing key)."""

    display_name: str | None = None
    provider: str | None = None
    model_id: str | None = None
    context_window: int | None = None
    speed_tier: str | None = None
    best_for: list[str] | None = None
    routing_domains: list[str] | None = None
    fallback_priority: int | None = None
    is_active: bool | None = None


class SetActive(BaseModel):
    is_active: bool


class PlatformOverview(BaseModel):
    total_users: int
    total_requests: int
    requests_today: int
    error_rate: float
    fallback_rate: float


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str | None
    plan: str
    role: str
    is_active: bool
    request_count: int = 0  # populated by the list endpoint; 0 on single-user responses
    created_at: datetime
