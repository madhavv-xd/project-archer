"""Abstract provider — both Groq and OpenRouter speak the OpenAI HTTP format,
so the actual request lives here and subclasses only supply URL + headers."""

from abc import ABC, abstractmethod

import httpx

from app.config import settings
from app.schemas.chat import ChatMessage

# Error categories that the proxy treats as "try the next model in the chain".
RETRYABLE = {"rate_limit", "server_error", "timeout"}


class ProviderError(Exception):
    def __init__(self, category: str, message: str, status: int | None = None):
        self.category = category
        self.status = status
        super().__init__(message)


class BaseProvider(ABC):
    name: str

    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @abstractmethod
    def headers(self) -> dict[str, str]: ...

    async def chat(
        self,
        model_id: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Call the provider's /chat/completions and return the raw JSON body.

        Raises ProviderError with a category the proxy can act on.
        """
        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.PROVIDER_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers(),
                )
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", f"{self.name} timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("server_error", f"{self.name} connection error: {exc}") from exc

        if resp.status_code == 429:
            raise ProviderError("rate_limit", f"{self.name} rate limited", 429)
        if resp.status_code >= 500:
            raise ProviderError("server_error", f"{self.name} server error", resp.status_code)
        if resp.status_code >= 400:
            raise ProviderError(
                "client_error",
                f"{self.name} returned {resp.status_code}: {resp.text[:300]}",
                resp.status_code,
            )

        return resp.json()
