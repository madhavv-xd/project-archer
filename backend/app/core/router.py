"""Keyword routing (context.md §5.8). Rules are checked in this exact order.

Phase 2B adds the async `route()` dispatcher on `settings.ROUTING_MODE` on top of
the unchanged `keyword_route()`.
"""

import logging
from typing import NamedTuple

logger = logging.getLogger("archer.router")

CODING_KEYWORDS = {
    "code", "function", "class", "debug", "error", "bug", "python", "javascript",
    "typescript", "java", "rust", "go", "api", "database", "sql", "algorithm",
    "implement", "programming", "syntax", "compile", "runtime", "framework", "library",
}

MATH_KEYWORDS = {
    "math", "calculate", "solve", "equation", "integral", "derivative", "matrix",
    "vector", "probability", "statistics", "formula", "theorem", "proof", "algebra",
    "calculus", "geometry",
}

WRITING_KEYWORDS = {
    "write", "essay", "story", "poem", "blog", "email", "draft", "rewrite",
    "paraphrase", "letter", "article", "compose",
}

ANALYSIS_KEYWORDS = {
    "analyze", "compare", "evaluate", "research", "detailed", "comprehensive",
    "tradeoffs",
}
# Multi-word analysis phrases checked as substrings (single-word matches above
# go through the tokenizer; these can't, so they live here).
ANALYSIS_PHRASES = ["pros and cons", "in depth", "explain thoroughly"]

SIMPLE_PREFIXES = (
    "hi", "hello", "thanks", "what is", "who is", "when did", "where is",
    "define", "yes", "no",
)


def _tokens(text: str) -> set[str]:
    return {t.strip(".,!?;:'\"()[]") for t in text.lower().split()}


def keyword_route(text: str) -> tuple[str, str]:
    """Return (domain, routing_reason). The domain→model mapping lives in the DB
    (Phase 2E), resolved by route() via the model cache — not hardcoded here."""
    lowered = text.lower().strip()
    words = _tokens(lowered)

    if words & CODING_KEYWORDS:
        return "coding", "coding_keywords"

    if words & MATH_KEYWORDS:
        return "math", "math_keywords"

    if words & WRITING_KEYWORDS:
        return "writing", "writing_keywords"

    if len(lowered.split()) < 15 or lowered.startswith(SIMPLE_PREFIXES):
        return "simple", "simple_query"

    if (words & ANALYSIS_KEYWORDS) or any(p in lowered for p in ANALYSIS_PHRASES):
        return "analysis", "analysis_keywords"

    return "general", "default"


class RouteDecision(NamedTuple):
    model_name: str
    routing_reason: str
    routing_method: str  # 'keyword' | 'embedding' — which engine actually decided
    shadow_routing_reason: str | None  # embedding's would-be choice, shadow mode only


def model_for_domain(domain: str) -> str:
    """Resolve a routing domain to a concrete model name via the cache. Falls
    back to the first model in the chain if the domain has no active model (all
    disabled, or a domain nothing is assigned to) — never crashes a request."""
    from app.core.proxy import model_cache

    model = model_cache.domain_model(domain)
    if model is None:
        chain = model_cache.fallback_chain()
        model = chain[0] if chain else None
    return model.name if model else ""


async def route(text: str) -> RouteDecision:
    """Dispatch on settings.ROUTING_MODE. keyword: unchanged from 2A. shadow:
    keyword decides, embedding's opinion is logged alongside. embedding: embedding
    decides, keyword is the below-threshold/failure fallback (design.md 4/5).
    Both engines pick a domain; the domain→model resolution is DB-driven (2E)."""
    # Imported here (not at module top) to keep test_router's keyword_route unit
    # tests free of the embeddings/config/httpx import chain.
    from app.config import settings
    from app.core.embeddings import embedding_route

    mode = settings.ROUTING_MODE

    if mode == "shadow":
        domain, reason = keyword_route(text)
        edomain, sim = await embedding_route(text)  # never raises
        shadow = f"embedding_{edomain}" if sim >= settings.EMBEDDING_SIMILARITY_THRESHOLD else None
        return RouteDecision(model_for_domain(domain), reason, "keyword", shadow)

    if mode == "embedding":
        edomain, sim = await embedding_route(text)  # never raises
        if sim >= settings.EMBEDDING_SIMILARITY_THRESHOLD:
            return RouteDecision(
                model_for_domain(edomain), f"embedding_{edomain}", "embedding", None
            )
        domain, reason = keyword_route(text)  # below threshold / disabled → keyword decides
        return RouteDecision(model_for_domain(domain), reason, "keyword", None)

    # keyword (default / unset)
    domain, reason = keyword_route(text)
    return RouteDecision(model_for_domain(domain), reason, "keyword", None)
