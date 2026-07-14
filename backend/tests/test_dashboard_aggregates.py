"""Pure-logic tests for the 2C dashboard aggregates.

The SQL aggregates themselves need a live DB (the suite has no DB harness by
design — see CLAUDE.md), so this covers the one extractable pure function:
the model-distribution percentage math. Same posture as 2B's
`_shadow_agreement_pct` test in test_embeddings.py.
"""

from app.db.repositories.requests import _distribution_from_counts


def test_distribution_empty_is_empty():
    assert _distribution_from_counts([]) == []


def test_distribution_single_model_is_100pct():
    out = _distribution_from_counts([("Llama 3.3 70B", 7)])
    assert out == [{"model": "Llama 3.3 70B", "count": 7, "percentage": 100.0}]


def test_distribution_multiple_sums_to_100():
    out = _distribution_from_counts([("A", 1), ("B", 1), ("C", 2)])
    assert [r["percentage"] for r in out] == [25.0, 25.0, 50.0]
    assert sum(r["percentage"] for r in out) == 100.0
    assert [r["count"] for r in out] == [1, 1, 2]
