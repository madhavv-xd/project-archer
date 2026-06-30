"""API key schemas. The full plaintext key is returned exactly once, at creation."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateApiKeyRequest(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    """Listing shape — never includes the plaintext key."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None


class CreatedApiKeyResponse(BaseModel):
    """Returned only at creation — the only time the full key is ever shown."""

    id: uuid.UUID
    name: str
    key: str
    prefix: str
