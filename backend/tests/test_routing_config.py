"""DB-shape invariants for the routing config (Phase 2E).

Replaces the old three-file-sync test: routing domain assignment and fallback
order now live in one place (the DB, backfilled by migration 006), so we assert
THAT source is internally consistent instead of comparing three Python
structures. The migration itself guarantees coverage — it UPDATEs by name and
then makes fallback_priority NOT NULL, so a seeded model it forgets would fail
the migration outright.
"""

import importlib.util
from pathlib import Path

from app.core.embeddings import DOMAINS


def _load_migration_006():
    path = Path(__file__).parents[1] / "alembic" / "versions" / "006_admin_and_routing_config.py"
    spec = importlib.util.spec_from_file_location("_mig006", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BACKFILL = _load_migration_006()._BACKFILL


def test_fallback_priorities_are_unique():
    priorities = [p for _n, p, _d in _BACKFILL]
    assert len(priorities) == len(set(priorities))


def test_fallback_priorities_are_contiguous_from_zero():
    priorities = sorted(p for _n, p, _d in _BACKFILL)
    assert priorities == list(range(len(_BACKFILL)))


def test_every_routing_domain_is_known():
    for _n, _p, domains in _BACKFILL:
        assert set(domains) <= DOMAINS, f"unknown domain in {domains}"


def test_all_six_domains_are_covered():
    covered = {d for _n, _p, domains in _BACKFILL for d in domains}
    assert covered == DOMAINS


def test_model_names_are_unique():
    names = [n for n, _p, _d in _BACKFILL]
    assert len(names) == len(set(names))
