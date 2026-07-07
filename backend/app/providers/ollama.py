"""Ollama Cloud provider — hosted, OpenAI-compatible (https://ollama.com/v1).

Not to be confused with local/self-hosted Ollama (out of scope): this is the
hosted cloud API, in the same slot as Groq/OpenRouter.
"""

from app.config import settings
from app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    name = "ollama"

    @property
    def base_url(self) -> str:
        return "https://ollama.com/v1"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"}
