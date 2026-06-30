"""Provider registry keyed by the value stored in models.provider."""

from app.providers.base import BaseProvider, ProviderError
from app.providers.groq import GroqProvider
from app.providers.openrouter import OpenRouterProvider

_PROVIDERS: dict[str, BaseProvider] = {
    "groq": GroqProvider(),
    "openrouter": OpenRouterProvider(),
}


def get_provider(name: str) -> BaseProvider:
    provider = _PROVIDERS.get(name)
    if provider is None:
        raise ProviderError("client_error", f"unknown provider: {name}")
    return provider


__all__ = ["get_provider", "ProviderError", "BaseProvider"]
