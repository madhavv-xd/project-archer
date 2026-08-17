"""Catalog drift check — are the active models still live at their providers?

Free-tier lineups change on the providers' schedule, not ours. Phase 2A's
catalog was verified live; a month later 5 of 9 models had been decommissioned
while still flagged is_active, so the priority-0 default was dead and two
routing domains resolved to nothing. This is the check that would have caught
that on day one.

    uv run python check_catalog.py

Deliberately not a pytest case (needs network + live keys, would break offline
runs) and not a CI job (a provider's deprecation shouldn't redden an unrelated
build). Run it when you sit down to work on the project.

Note: a model listed by the provider can still be uncallable on our tier —
Ollama Cloud lists subscription-gated models that return HTTP 403. Pass --call
to spend one tiny completion per model and catch that too.
"""

import asyncio
import sys

import httpx
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Model
from app.providers import get_provider


async def _live_ids(client: httpx.AsyncClient, provider_name: str) -> set[str]:
    provider = get_provider(provider_name)
    resp = await client.get(f"{provider.base_url}/models", headers=provider.headers())
    resp.raise_for_status()
    return {m["id"] for m in resp.json()["data"]}


async def _callable(client: httpx.AsyncClient, model: Model) -> str | None:
    """None if the model answers, else a short reason."""
    provider = get_provider(model.provider)
    resp = await client.post(
        f"{provider.base_url}/chat/completions",
        headers=provider.headers(),
        json={
            "model": model.model_id,
            "messages": [{"role": "user", "content": "Say OK."}],
            "max_tokens": 8,
        },
    )
    return None if resp.status_code == 200 else f"HTTP {resp.status_code} {resp.text[:100]}"


async def main() -> int:
    check_calls = "--call" in sys.argv

    async with AsyncSessionLocal() as db:
        active = list(
            (
                await db.execute(
                    select(Model).where(Model.is_active.is_(True)).order_by(Model.fallback_priority)
                )
            )
            .scalars()
            .all()
        )

    problems: list[str] = []
    async with httpx.AsyncClient(timeout=90) as client:
        listings = {
            name: await _live_ids(client, name) for name in sorted({m.provider for m in active})
        }

        for model in active:
            if model.model_id not in listings[model.provider]:
                problems.append(f"{model.name}: {model.model_id} not listed by {model.provider}")
                continue
            if check_calls:
                # Sequential: the free Ollama tier caps concurrency and answers
                # parallel probes with 429s that look like real failures.
                reason = await _callable(client, model)
                if reason:
                    problems.append(f"{model.name}: {model.model_id} listed but {reason}")
                await asyncio.sleep(1.5)

    for model in active:
        print(f"  {model.fallback_priority:>2} {model.name:<26} {model.provider:<7} {model.model_id}")

    print()
    if problems:
        print(f"DRIFT — {len(problems)} of {len(active)} active models are unusable:")
        for p in problems:
            print(f"  ! {p}")
        print("\nRetire them with a migration (is_active = false — do not DELETE, request_logs FKs them).")
        return 1

    checked = "listed and callable" if check_calls else "listed"
    print(f"OK — all {len(active)} active models {checked}." + ("" if check_calls else " Re-run with --call to verify tier access."))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
