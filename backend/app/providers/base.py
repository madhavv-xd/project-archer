"""Abstract provider — both Groq and OpenRouter speak the OpenAI HTTP format,
so the actual request lives here and subclasses only supply URL + headers."""

from abc import ABC, abstractmethod

import httpx

from app.config import settings
from app.schemas.chat import ChatMessage, ReasoningEffort

# Error categories that the proxy treats as "try the next model in the chain".
RETRYABLE = {"rate_limit", "server_error", "timeout"}


def reasoning_params(
    reasoning_mode: str, provider: str, reasoning: bool, effort: ReasoningEffort
) -> dict:
    """Translate one Archer-level reasoning intent into this model's dialect.

    The providers do not share an effort vocabulary — gpt-oss takes
    low/medium/high and rejects `none`, qwen3.6 takes none/default and rejects
    `low` — and a wrong value is HTTP 400, which the proxy categorizes
    `client_error` and does NOT retry. So the vocabulary is read from the
    model's `reasoning_mode` (a DB column) rather than guessed from its name.

    Groq additionally honors `reasoning_format`, which is what actually fixes
    qwen3.6: `hidden` drops its `<think>` block, `parsed` relocates it out of
    `content` into a sibling `reasoning` field.
    """
    params: dict = {}

    if reasoning_mode == "none":
        # Model doesn't reason unless prodded — and gemma4 starts reasoning if
        # sent an effort at all, so send nothing.
        return params

    if provider == "groq":
        params["reasoning_format"] = "parsed" if reasoning else "hidden"

    if reasoning_mode == "toggle":
        params["reasoning_effort"] = "default" if reasoning else "none"
    elif reasoning_mode == "effort":
        # Cannot be switched off at the provider; "off" means minimum effort,
        # with the output suppressed by reasoning_format above.
        params["reasoning_effort"] = effort if reasoning else "low"
    elif reasoning_mode == "effort_optional":
        params["reasoning_effort"] = effort if reasoning else "none"

    return params

# One shared client for the whole process so connections (and TLS handshakes)
# are pooled and reused across requests instead of rebuilt every call.
# Created lazily; closed on app shutdown (see app.main lifespan).
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=settings.PROVIDER_TIMEOUT_SECONDS,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


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
        extra: dict | None = None,
    ) -> dict:
        """Call the provider's /chat/completions and return the raw JSON body.

        Raises ProviderError with a category the proxy can act on.
        """
        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **(extra or {}),
        }
        try:
            resp = await _get_client().post(
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

    async def stream(
        self,
        model_id: str,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int,
        extra: dict | None = None,
    ):
        """Stream the provider's /chat/completions as raw SSE lines.

        Same URL/headers/error-categorization as chat(); adds the streaming
        request flags. Errors that occur before the first line is yielded raise
        ProviderError so the proxy can fall back; errors after the first line
        also raise ProviderError, but the proxy treats those as interruptions.
        """
        payload = {
            "model": model_id,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
            **(extra or {}),
        }
        try:
            async with _get_client().stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers(),
            ) as resp:
                if resp.status_code == 429:
                    await resp.aread()
                    raise ProviderError("rate_limit", f"{self.name} rate limited", 429)
                if resp.status_code >= 500:
                    await resp.aread()
                    raise ProviderError("server_error", f"{self.name} server error", resp.status_code)
                if resp.status_code >= 400:
                    await resp.aread()
                    raise ProviderError(
                        "client_error",
                        f"{self.name} returned {resp.status_code}: {resp.text[:300]}",
                        resp.status_code,
                    )
                async for line in resp.aiter_lines():
                    if line:
                        yield line
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout", f"{self.name} timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("server_error", f"{self.name} connection error: {exc}") from exc
