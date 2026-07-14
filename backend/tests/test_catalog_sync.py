"""Three-file sync rule (Phase 2A model-catalog spec): the model names in the
seed migration, app/core/router.py, and app/core/proxy.py must be mutually
consistent. DB-driven routing config is Phase 2E; until then a name that appears
in one place but is missing/misspelled in another is a latent runtime bug, so we
fail the build on drift instead of relying on convention.
"""

import importlib.util
from pathlib import Path

from app.core.embeddings import DOMAIN_MODEL
from app.core.proxy import FALLBACK_CHAIN
from app.core.router import keyword_route

SPEC_DOMAINS = {"coding", "math", "writing", "simple", "analysis", "general"}

# The 5 models seeded by 001_initial (frozen). The 003 migration then removes
# some of these and adds new ones; both deltas are read live from that migration
# so this stays honest as the catalog evolves.
ORIGINAL_5 = {
    "llama-3.3-70b-groq",
    "llama-3.1-8b-groq",
    "gpt-oss-120b-groq",
    "gpt-oss-20b-groq",
    "qwen-2.5-72b-or",
}


def _load_migration_003():
    """Load the 003 migration module by path (its name starts with a digit, so
    it can't be imported normally)."""
    path = Path(__file__).parents[1] / "alembic" / "versions" / "003_expand_catalog.py"
    spec = importlib.util.spec_from_file_location("_mig003", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MIG = _load_migration_003()
SEED_NAMES = (ORIGINAL_5 - set(_MIG._REMOVED_NAMES)) | {m["name"] for m in _MIG._NEW_MODELS}


def test_catalog_has_8_to_10_models():
    assert 8 <= len(SEED_NAMES) <= 10


def test_fallback_chain_covers_every_seeded_model_exactly():
    # Every seeded model is reachable via the chain, and the chain names nothing
    # that isn't seeded (no strays / typos).
    assert set(FALLBACK_CHAIN) == SEED_NAMES


def test_fallback_chain_has_no_duplicates():
    assert len(FALLBACK_CHAIN) == len(set(FALLBACK_CHAIN))


def test_every_router_target_is_a_seeded_model():
    # Representative query per routing branch — collect the model each selects.
    probes = [
        "can you debug this python function for me",          # coding
        "please solve this integral and derivative",          # math
        "write a short poem about the ocean",                 # writing
        "hi",                                                 # simple
        "compare and evaluate these detailed tradeoffs "      # analysis
        "comprehensively across every option in the report",
        "i wandered around the old town square for a while "  # default
        "and watched the birds by the fountain late today",
    ]
    targets = {keyword_route(q)[0] for q in probes}
    assert targets <= SEED_NAMES


def test_domain_model_keys_are_exactly_the_six_domains():
    # Fourth file in the catalog-sync web (Phase 2B): DOMAIN_MODEL must cover the
    # 6 spec domains and target only seeded models (or shadow agreement breaks).
    assert set(DOMAIN_MODEL.keys()) == SPEC_DOMAINS


def test_every_domain_model_target_is_a_seeded_model():
    assert set(DOMAIN_MODEL.values()) <= SEED_NAMES
