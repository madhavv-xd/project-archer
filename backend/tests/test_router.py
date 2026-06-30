"""Keyword router — covers every branch and the priority ordering (§5.8)."""

from app.core.router import keyword_route


def test_coding_keyword_routes_to_llama_70b():
    model, reason = keyword_route("can you help me debug this python function")
    assert model == "llama-3.3-70b-groq"
    assert reason == "coding_keywords"


def test_math_keyword_routes_to_gpt_oss_120b():
    model, reason = keyword_route("please solve this integral and show the derivative steps")
    assert model == "gpt-oss-120b-groq"
    assert reason == "math_keywords"


def test_short_query_routes_to_llama_8b():
    model, reason = keyword_route("what time is it")
    assert model == "llama-3.1-8b-groq"
    assert reason == "simple_query"


def test_simple_prefix_overrides_length():
    # >15 words but starts with a simple prefix → still simple_query.
    model, reason = keyword_route(
        "what is the meaning of life the universe and everything according to the famous book"
    )
    assert model == "llama-3.1-8b-groq"
    assert reason == "simple_query"


def test_analysis_keyword_routes_to_qwen():
    model, reason = keyword_route(
        "please compare these two different business strategies and give me a thorough "
        "breakdown of each option for my quarterly report"
    )
    assert model == "qwen-2.5-72b-or"
    assert reason == "analysis_keywords"


def test_analysis_phrase_substring_matches():
    model, reason = keyword_route(
        "walk me through these marketing plans in depth so the whole team understands every "
        "tradeoff before the launch next week"
    )
    assert model == "qwen-2.5-72b-or"
    assert reason == "analysis_keywords"


def test_long_neutral_query_falls_to_default():
    model, reason = keyword_route(
        "i went to the market yesterday and bought some fresh vegetables fruits bread and "
        "also met an old friend there for a while"
    )
    assert model == "llama-3.3-70b-groq"
    assert reason == "default"


def test_coding_beats_math_on_priority():
    # Contains both a coding word ("code") and math words ("solve", "equation").
    model, reason = keyword_route("write code to solve this equation for me")
    assert model == "llama-3.3-70b-groq"
    assert reason == "coding_keywords"
