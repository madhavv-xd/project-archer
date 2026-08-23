"""Model catalog response schema."""

import uuid

from pydantic import BaseModel, ConfigDict


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    display_name: str
    provider: str
    model_id: str
    is_active: bool
    context_window: int
    speed_tier: str
    best_for: list[str]
    # Lets the playground disable the effort control for models that can only
    # switch thinking on or off (see providers.base.reasoning_params).
    reasoning_mode: str
