"""Shared test catalog for the routing tests.

Mirrors migration 006's backfill (name, fallback_priority, routing_domains) so
proxy / router / embedding tests resolve domains and fallback order the same way
production does — without a live DB. One source of truth for all three.
"""

import pytest

from app.core.proxy import model_cache
from app.db.models import Model

# (name, fallback_priority, routing_domains) — must match 006_admin_and_routing_config._BACKFILL.
CATALOG = [
    ("llama-3.3-70b-groq", 0, ["coding", "general"]),
    ("llama-4-scout-groq", 1, ["writing"]),
    ("gpt-oss-120b-groq", 2, ["math"]),
    ("qwen3-coder-ollama", 3, []),
    ("nemotron-3-super-ollama", 4, ["analysis"]),
    ("minimax-m3-ollama", 5, []),
    ("glm-4.7-ollama", 6, []),
    ("gpt-oss-20b-groq", 7, []),
    ("llama-3.1-8b-groq", 8, ["simple"]),
]


def catalog_models() -> list[Model]:
    return [
        Model(
            name=n,
            provider="groq",
            model_id=n,
            is_active=True,
            fallback_priority=p,
            routing_domains=d,
        )
        for n, p, d in CATALOG
    ]


@pytest.fixture
def catalog():
    """Load the standard catalog into the module-level model cache for a test."""
    model_cache.load(catalog_models())
    yield
    model_cache.load([])
