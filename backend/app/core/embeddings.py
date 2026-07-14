"""Centroid-similarity semantic routing (Phase 2B).

Embeds the last user message via the Jina embeddings API and compares it against
6 precomputed per-domain centroids (centroids.json, checked in). Pure-Python
cosine similarity — no numpy. The offline centroid build lives in the __main__
block: `uv run python -m app.core.embeddings` (needs EMBEDDING_API_KEY).

See openspec/changes/phase-2b-embedding-routing/design.md.
"""

import json
import logging
from pathlib import Path

from app.config import settings
from app.providers.base import ProviderError, _get_client

logger = logging.getLogger("archer.embeddings")

JINA_URL = "https://api.jina.ai/v1/embeddings"
JINA_MODEL = "jina-embeddings-v3"

# domain -> the SAME model name router.py's keyword_route() targets for that
# domain. A fourth file in the catalog-sync web (seed / router.py / proxy.py /
# here) — kept in sync by inspection, enforced by tests/test_catalog_sync.py.
# Both engines must target the same model per domain or shadow "agreement" is
# meaningless (design.md decision 2).
DOMAIN_MODEL = {
    "coding": "llama-3.3-70b-groq",
    "math": "gpt-oss-120b-groq",
    "writing": "llama-4-scout-groq",
    "simple": "llama-3.1-8b-groq",
    "analysis": "nemotron-3-super-ollama",
    "general": "llama-3.3-70b-groq",
}

_CENTROIDS_PATH = Path(__file__).parent / "centroids.json"

# Loaded once at import time. Missing (before the first offline build) = empty,
# so embedding_route() always returns the below-threshold sentinel and the
# caller falls back to keyword routing.
try:
    _CENTROIDS: dict[str, list[float]] = json.loads(_CENTROIDS_PATH.read_text())
except FileNotFoundError:
    _CENTROIDS = {}
    logger.warning("centroids.json not found — embedding routing will fall back to keyword")


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


async def embed(text: str) -> list[float]:
    """Embed one string via the Jina API. Raises ProviderError on failure."""
    try:
        resp = await _get_client().post(
            JINA_URL,
            json={"model": JINA_MODEL, "task": "text-matching", "input": [text]},
            headers={"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}"},
        )
    except Exception as exc:  # network / timeout
        raise ProviderError("server_error", f"jina embed failed: {exc}") from exc
    if resp.status_code >= 400:
        raise ProviderError("server_error", f"jina returned {resp.status_code}", resp.status_code)
    return resp.json()["data"][0]["embedding"]


async def embedding_route(text: str) -> tuple[str, float]:
    """Return (domain, top_similarity). On any failure (no key, network, empty
    centroids), returns a below-threshold sentinel — never raises into the
    request path (design.md decisions 4/5)."""
    if not _CENTROIDS or not settings.EMBEDDING_API_KEY:
        return "", -1.0
    try:
        vec = await embed(text)
    except Exception:
        logger.warning("embedding_route failed, falling back to keyword", exc_info=True)
        return "", -1.0

    best_domain, best_sim = "", -1.0
    for domain, centroid in _CENTROIDS.items():
        sim = cosine(vec, centroid)
        if sim > best_sim:
            best_domain, best_sim = domain, sim
    return best_domain, best_sim


if __name__ == "__main__":
    # Offline centroid build. Embeds each domain's exemplars, averages into a
    # per-domain centroid, writes centroids.json (checked into git). Re-run
    # whenever routing_exemplars.py changes. Needs EMBEDDING_API_KEY set.
    import asyncio

    from app.core.routing_exemplars import EXEMPLARS

    async def _build() -> None:
        assert settings.EMBEDDING_API_KEY, "set EMBEDDING_API_KEY to build centroids"
        centroids: dict[str, list[float]] = {}
        for domain, prompts in EXEMPLARS.items():
            vectors = [await embed(p) for p in prompts]
            dim = len(vectors[0])
            centroids[domain] = [sum(v[i] for v in vectors) / len(vectors) for i in range(dim)]
            print(f"{domain}: {len(vectors)} exemplars -> {dim}-dim centroid")
        _CENTROIDS_PATH.write_text(json.dumps(centroids))
        print(f"wrote {_CENTROIDS_PATH}")

    asyncio.run(_build())
