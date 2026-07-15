"""Keyword router — covers every branch and the priority ordering (§5.8).

keyword_route now returns a DOMAIN (Phase 2E); the domain→model resolution is
DB-driven and covered by test_domain_resolves_to_backfilled_model below.
"""

from app.core.proxy import model_cache
from app.core.router import keyword_route, model_for_domain


def test_coding_keyword_routes_to_coding_domain():
    domain, reason = keyword_route("can you help me debug this python function")
    assert domain == "coding"
    assert reason == "coding_keywords"


def test_math_keyword_routes_to_math_domain():
    domain, reason = keyword_route("please solve this integral and show the derivative steps")
    assert domain == "math"
    assert reason == "math_keywords"


def test_short_query_routes_to_simple_domain():
    domain, reason = keyword_route("what time is it")
    assert domain == "simple"
    assert reason == "simple_query"


def test_simple_prefix_overrides_length():
    # >15 words but starts with a simple prefix → still simple.
    domain, reason = keyword_route(
        "what is the meaning of life the universe and everything according to the famous book"
    )
    assert domain == "simple"
    assert reason == "simple_query"


def test_analysis_keyword_routes_to_analysis_domain():
    domain, reason = keyword_route(
        "please compare these two different business strategies and give me a thorough "
        "breakdown of each option for my quarterly report"
    )
    assert domain == "analysis"
    assert reason == "analysis_keywords"


def test_analysis_phrase_substring_matches():
    domain, reason = keyword_route(
        "walk me through these marketing plans in depth so the whole team understands every "
        "tradeoff before the launch next week"
    )
    assert domain == "analysis"
    assert reason == "analysis_keywords"


def test_long_neutral_query_falls_to_general_domain():
    domain, reason = keyword_route(
        "i went to the market yesterday and bought some fresh vegetables fruits bread and "
        "also met an old friend there for a while"
    )
    assert domain == "general"
    assert reason == "default"


def test_coding_beats_math_on_priority():
    # Contains both a coding word ("code") and math words ("solve", "equation").
    domain, reason = keyword_route("write code to solve this equation for me")
    assert domain == "coding"
    assert reason == "coding_keywords"


def test_domain_resolves_to_backfilled_model(catalog):
    # DB-driven resolution must reproduce the pre-2E hardcoded targets.
    assert model_for_domain("coding") == "llama-3.3-70b-groq"
    assert model_for_domain("math") == "gpt-oss-120b-groq"
    assert model_for_domain("writing") == "llama-4-scout-groq"
    assert model_for_domain("simple") == "llama-3.1-8b-groq"
    assert model_for_domain("analysis") == "nemotron-3-super-ollama"
    assert model_for_domain("general") == "llama-3.3-70b-groq"


def test_unassigned_domain_falls_back_to_first_in_chain(catalog):
    # A domain nothing is assigned to resolves to the lowest-priority model.
    assert model_for_domain("nonexistent") == "llama-3.3-70b-groq"


def test_empty_cache_never_crashes():
    model_cache.load([])
    assert model_for_domain("coding") == ""  # no model → empty name, chain tried downstream
