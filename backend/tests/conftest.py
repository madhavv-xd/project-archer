"""Shared test catalog for the routing tests.

Mirrors migration 009's active set (name, fallback_priority, routing_domains) so
proxy / router / embedding tests resolve domains and fallback order the same way
production does — without a live DB. One source of truth for all three.

Only the active models appear here: 007 retired 5 decommissioned models via
is_active = false, and ModelCache.load() filters those out before building the
chain or the domain map, so they can never influence a routing decision.
"""

import pytest

from app.core.proxy import model_cache
from app.db.models import Model

# (name, fallback_priority, routing_domains) — must match 009_qwen38_retire_minimax._ACTIVE.
CATALOG = [
    ("gpt-oss-120b-groq", 0, ["coding", "math"]),
    ("qwen3.8-27b-groq", 1, ["simple"]),
    ("gpt-oss-20b-groq", 2, ["general"]),
    ("nemotron-3-nano-ollama", 3, []),
    ("nemotron-3-ultra-ollama", 4, ["analysis"]),
    ("nemotron-3-super-ollama", 5, []),
    ("gemma4-31b-ollama", 6, ["writing"]),
]

# name → reasoning_mode, mirroring migrations 008 + 009 (qwen3.8). The
# modes carry incompatible effort vocabularies, so tests that exercise fallback
# need the real ones to catch a payload built for the wrong model.
REASONING_MODES = {
    "gpt-oss-120b-groq": "effort",
    "gpt-oss-20b-groq": "effort",
    "qwen3.8-27b-groq": "effort_optional",
    "nemotron-3-nano-ollama": "effort_optional",
    "nemotron-3-ultra-ollama": "effort_optional",
    "nemotron-3-super-ollama": "effort_optional",
    "gemma4-31b-ollama": "none",
}


def catalog_models() -> list[Model]:
    return [
        Model(
            name=n,
            provider="ollama" if n.endswith("-ollama") else "groq",
            model_id=n,
            is_active=True,
            fallback_priority=p,
            routing_domains=d,
            reasoning_mode=REASONING_MODES[n],
        )
        for n, p, d in CATALOG
    ]


@pytest.fixture
def catalog():
    """Load the standard catalog into the module-level model cache for a test."""
    model_cache.load(catalog_models())
    yield
    model_cache.load([])
