"""Application settings — single source of truth for all environment variables.

Loaded once at import time as the module-level ``settings`` singleton.
"""

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (Neon — async driver)
    DATABASE_URL: str

    # Provider API keys
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Auth
    API_KEY_SALT: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days

    # OAuth — shared secret guarding the server-to-server /auth/oauth endpoint
    # (set identically here and in the frontend env). See design.md.
    OAUTH_INTERNAL_SECRET: str = ""

    # Frontend / CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # Providers
    PROVIDER_TIMEOUT_SECONDS: int = 30

    @property
    def async_database_url(self) -> str:
        """Normalize a Neon/libpq connection string to the asyncpg driver.

        Accepts plain ``postgresql://`` URLs with ``sslmode=`` query params
        (Neon's default copy-paste form) and returns a ``postgresql+asyncpg://``
        URL that asyncpg can consume: ``sslmode`` -> ``ssl`` and the
        libpq-only ``channel_binding`` param dropped.
        """
        url = self.DATABASE_URL
        parts = urlsplit(url)

        scheme = parts.scheme
        if scheme in ("postgres", "postgresql"):
            scheme = "postgresql+asyncpg"

        query = []
        for key, value in parse_qsl(parts.query):
            if key == "channel_binding":
                continue
            if key == "sslmode":
                key = "ssl"
            query.append((key, value))

        return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
