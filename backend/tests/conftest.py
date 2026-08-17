"""Shared test catalog for the routing tests.

Mirrors migration 007's active set (name, fallback_priority, routing_domains) so
proxy / router / embedding tests resolve domains and fallback order the same way
production does — without a live DB. One source of truth for all three.

Only the active models appear here: 007 retired 5 decommissioned models via
is_active = false, and ModelCache.load() filters those out before building the
chain or the domain map, so they can never influence a routing decision.
"""

import pytest

from app.core.proxy import model_cache
from app.db.models import Model

# (name, fallback_priority, routing_domains) — must match 007_refresh_catalog._ACTIVE.
CATALOG = [
    ("gpt-oss-120b-groq", 0, ["coding", "math"]),
    ("qwen3.6-27b-groq", 1, ["simple"]),
    ("gpt-oss-20b-groq", 2, ["general"]),
    ("nemotron-3-nano-ollama", 3, []),
    ("nemotron-3-ultra-ollama", 4, ["analysis"]),
    ("nemotron-3-super-ollama", 5, []),
    ("minimax-m3-ollama", 6, []),
    ("gemma4-31b-ollama", 7, ["writing"]),
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
