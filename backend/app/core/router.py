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
    """Return (model_name, routing_reason)."""
    lowered = text.lower().strip()
    words = _tokens(lowered)

    if words & CODING_KEYWORDS:
        return "llama-3.3-70b-groq", "coding_keywords"

    if words & MATH_KEYWORDS:
        return "gpt-oss-120b-groq", "math_keywords"

    if words & WRITING_KEYWORDS:
        return "llama-4-scout-groq", "writing_keywords"

    if len(lowered.split()) < 15 or lowered.startswith(SIMPLE_PREFIXES):
        return "llama-3.1-8b-groq", "simple_query"

    if (words & ANALYSIS_KEYWORDS) or any(p in lowered for p in ANALYSIS_PHRASES):
        return "nemotron-3-super-ollama", "analysis_keywords"

    return "llama-3.3-70b-groq", "default"


class RouteDecision(NamedTuple):
    model_name: str
    routing_reason: str
    routing_method: str  # 'keyword' | 'embedding' — which engine actually decided
    shadow_routing_reason: str | None  # embedding's would-be choice, shadow mode only


async def route(text: str) -> RouteDecision:
    """Dispatch on settings.ROUTING_MODE. keyword: unchanged from 2A. shadow:
    keyword decides, embedding's opinion is logged alongside. embedding: embedding
    decides, keyword is the below-threshold/failure fallback (design.md 4/5)."""
    # Imported here (not at module top) to keep test_router's keyword_route unit
    # tests free of the embeddings/config/httpx import chain.
    from app.config import settings
    from app.core.embeddings import DOMAIN_MODEL, embedding_route

    mode = settings.ROUTING_MODE

    if mode == "shadow":
        name, reason = keyword_route(text)
        domain, sim = await embedding_route(text)  # never raises
        shadow = f"embedding_{domain}" if sim >= settings.EMBEDDING_SIMILARITY_THRESHOLD else None
        return RouteDecision(name, reason, "keyword", shadow)

    if mode == "embedding":
        domain, sim = await embedding_route(text)  # never raises
        if sim >= settings.EMBEDDING_SIMILARITY_THRESHOLD:
            return RouteDecision(DOMAIN_MODEL[domain], f"embedding_{domain}", "embedding", None)
        name, reason = keyword_route(text)  # below threshold / disabled → keyword decides
        return RouteDecision(name, reason, "keyword", None)

    # keyword (default / unset)
    name, reason = keyword_route(text)
    return RouteDecision(name, reason, "keyword", None)
