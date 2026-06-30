"""Request-log response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class RequestLogResponse(BaseModel):
    id: uuid.UUID
    model: str | None
    routing_reason: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    latency_ms: int
    status: str
    fallback_used: bool
    created_at: datetime


class DashboardStats(BaseModel):
    total_requests: int
    requests_today: int
    total_tokens: int
    success_rate: float
    most_used_model: str | None
