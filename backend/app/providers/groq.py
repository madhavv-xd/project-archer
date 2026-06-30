"""Groq provider — OpenAI-compatible."""

from app.config import settings
from app.providers.base import BaseProvider


class GroqProvider(BaseProvider):
    name = "groq"

    @property
    def base_url(self) -> str:
        return "https://api.groq.com/openai/v1"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
