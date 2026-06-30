"""OpenRouter provider — OpenAI-compatible, with attribution headers."""

from app.config import settings
from app.providers.base import BaseProvider


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    @property
    def base_url(self) -> str:
        return "https://openrouter.ai/api/v1"

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://archer.ai",
            "X-Title": "Archer",
        }
