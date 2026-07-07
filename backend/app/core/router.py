"""Keyword routing (context.md §5.8). Rules are checked in this exact order."""

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
