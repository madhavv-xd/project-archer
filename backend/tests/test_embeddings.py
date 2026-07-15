"""Embedding router: cosine math, threshold/failure fallback, the route()
dispatcher across the three modes, agreement calc, and the latency budget.

Network is always monkeypatched — no real Jina calls in the suite.
"""

import time

import pytest

from app.config import settings
from app.core import embeddings
from app.core.embeddings import cosine, embedding_route
from app.core.router import route
from app.db.repositories.requests import _shadow_agreement_pct


# --- cosine math -----------------------------------------------------------
def test_cosine_identical_is_one():
    assert cosine([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_cosine_orthogonal_is_zero():
    assert cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_zero_vector_is_safe():
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


# --- embedding_route -------------------------------------------------------
@pytest.fixture
def centroids(monkeypatch):
    monkeypatch.setattr(embeddings, "_CENTROIDS", {"coding": [1.0, 0.0, 0.0], "math": [0.0, 1.0, 0.0]})
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "test-key")


async def test_embedding_route_picks_nearest_centroid(centroids, monkeypatch):
    async def fake_embed(_text):
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(embeddings, "embed", fake_embed)
    domain, sim = await embedding_route("anything")
    assert domain == "coding"
    assert sim == pytest.approx(1.0)


async def test_embedding_route_below_threshold_sentinel(centroids, monkeypatch):
    async def fake_embed(_text):
        return [0.0, 0.0, 1.0]  # orthogonal to both centroids

    monkeypatch.setattr(embeddings, "embed", fake_embed)
    _, sim = await embedding_route("anything")
    assert sim < settings.EMBEDDING_SIMILARITY_THRESHOLD


async def test_embedding_route_degrades_on_api_failure(centroids, monkeypatch):
    async def boom(_text):
        raise RuntimeError("jina down")

    monkeypatch.setattr(embeddings, "embed", boom)
    domain, sim = await embedding_route("anything")  # must not raise
    assert (domain, sim) == ("", -1.0)


async def test_embedding_route_disabled_without_key(monkeypatch):
    monkeypatch.setattr(embeddings, "_CENTROIDS", {"coding": [1.0]})
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "")
    assert await embedding_route("x") == ("", -1.0)


# --- route() dispatcher (task 3.4) -----------------------------------------
async def _stub_embedding_route(monkeypatch, result):
    async def fake(_text):
        return result

    monkeypatch.setattr(embeddings, "embedding_route", fake)


async def test_shadow_mode_keyword_decides_embedding_only_logged(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MODE", "shadow")
    await _stub_embedding_route(monkeypatch, ("math", 0.9))
    d = await route("please debug this python function")  # keyword → coding
    assert d.model_name == "llama-3.3-70b-groq"
    assert d.routing_reason == "coding_keywords"
    assert d.routing_method == "keyword"
    assert d.shadow_routing_reason == "embedding_math"


async def test_shadow_mode_embedding_failure_leaves_null(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MODE", "shadow")
    await _stub_embedding_route(monkeypatch, ("", -1.0))  # below threshold / failed
    d = await route("please debug this python function")
    assert d.routing_method == "keyword"
    assert d.shadow_routing_reason is None


async def test_embedding_mode_high_confidence_decides(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MODE", "embedding")
    await _stub_embedding_route(monkeypatch, ("math", 0.9))
    d = await route("some paraphrased quant question")
    assert d.model_name == "gpt-oss-120b-groq"  # DOMAIN_MODEL["math"]
    assert d.routing_reason == "embedding_math"
    assert d.routing_method == "embedding"
    assert d.shadow_routing_reason is None


async def test_embedding_mode_below_threshold_falls_back_to_keyword(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MODE", "embedding")
    await _stub_embedding_route(monkeypatch, ("math", 0.1))
    d = await route("please debug this python function")  # keyword → coding
    assert d.model_name == "llama-3.3-70b-groq"
    assert d.routing_reason == "coding_keywords"  # plain keyword reason, no prefix
    assert d.routing_method == "keyword"


async def test_keyword_mode_never_consults_embedding(monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MODE", "keyword")

    async def boom(_text):
        raise AssertionError("embedding_route must not be called in keyword mode")

    monkeypatch.setattr(embeddings, "embedding_route", boom)
    d = await route("please debug this python function")
    assert d == ("llama-3.3-70b-groq", "coding_keywords", "keyword", None)


# --- shadow agreement calc (task 4.2) --------------------------------------
def test_shadow_agreement_pct():
    rows = [
        ("embedding_coding", "llama-3.3-70b-groq"),   # DOMAIN_MODEL[coding] matches → agree
        ("embedding_math", "gpt-oss-120b-groq"),      # matches → agree
        ("embedding_math", "llama-3.1-8b-groq"),      # mismatch → disagree
    ]
    assert _shadow_agreement_pct(rows) == pytest.approx(66.67)


def test_shadow_agreement_empty_is_none():
    assert _shadow_agreement_pct([]) is None


# --- embedding_health probe (2D) -------------------------------------------
async def test_embedding_health_disabled_without_key(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "")
    assert await embeddings.embedding_health() == "disabled"


async def test_embedding_health_ok_on_success(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "k")
    monkeypatch.setattr(embeddings, "embed", lambda _t: _async([0.0]))
    assert await embeddings.embedding_health() == "ok"


async def test_embedding_health_degraded_on_error(monkeypatch):
    monkeypatch.setattr(settings, "EMBEDDING_API_KEY", "k")

    async def boom(_t):
        raise RuntimeError("jina down")

    monkeypatch.setattr(embeddings, "embed", boom)
    assert await embeddings.embedding_health() == "degraded"


async def _async(v):
    return v


# --- latency budget (task 3.5) ---------------------------------------------
async def test_routing_overhead_p50_under_budget(centroids, monkeypatch):
    import asyncio

    async def slow_embed(_text):
        await asyncio.sleep(0.05)  # realistic Jina network hop
        return [1.0, 0.0, 0.0]

    monkeypatch.setattr(embeddings, "embed", slow_embed)
    samples = []
    for _ in range(11):
        t = time.perf_counter()
        await embedding_route("some query")
        samples.append(time.perf_counter() - t)
    p50 = sorted(samples)[len(samples) // 2]
    assert p50 < 0.2, f"p50 routing overhead {p50 * 1000:.0f}ms exceeds 200ms budget"
