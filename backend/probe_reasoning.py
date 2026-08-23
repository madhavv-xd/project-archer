"""Reasoning-capability probe — where does each active model put its thinking?

Archer promises one answer shape whichever model served the request, but the
providers disagree: some return reasoning in a sibling `message.reasoning`
field, one (qwen3.6) inlines it in `content` as `<think>...</think>`, and the
effort vocabularies differ enough that sending the wrong one is a hard HTTP 400
(categorized `client_error`, which the proxy does NOT retry). `models.reasoning_mode`
encodes that per model; this script is how you check the column still matches
reality after a catalog refresh.

    uv run python probe_reasoning.py

Same discipline as check_catalog.py: network + live keys, so not a pytest case
and not CI. Ollama Cloud's free tier caps concurrency (parallel probes come back
`429 too many concurrent requests`), so every call here is sequential.
"""

import asyncio

import httpx
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Model
from app.providers import get_provider

PROMPT = "If a train travels 60mph for 2 hours, how far? Answer briefly."

# What each mode claims the model will accept. `reasoning_format` is Groq-only.
EFFORT_PROBES = {
    "none": [],
    "toggle": ["none", "default"],
    "effort": ["low", "medium", "high"],
    "effort_optional": ["none", "low", "medium", "high"],
}


async def _ask(client: httpx.AsyncClient, model: Model, extra: dict) -> str:
    provider = get_provider(model.provider)
    resp = await client.post(
        f"{provider.base_url}/chat/completions",
        headers=provider.headers(),
        json={
            "model": model.model_id,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 512,
            **extra,
        },
    )
    if resp.status_code != 200:
        return f"HTTP {resp.status_code} {resp.text[:90]}"
    message = (resp.json().get("choices") or [{}])[0].get("message", {})
    content = message.get("content") or ""
    marks = []
    if "<think" in content:
        marks.append("INLINE <think> in content")
    if message.get("reasoning"):
        marks.append("reasoning field")
    return ", ".join(marks) or "no reasoning"


async def main() -> int:
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

    async with httpx.AsyncClient(timeout=90) as client:
        for model in active:
            mode = getattr(model, "reasoning_mode", "?")
            print(f"\n{model.name}  ({model.provider}, mode={mode})")
            print(f"  baseline                      -> {await _ask(client, model, {})}")
            await asyncio.sleep(1.5)

            for effort in EFFORT_PROBES.get(mode, []):
                extra = {"reasoning_effort": effort}
                label = f"effort={effort}"
                print(f"  {label:<30}-> {await _ask(client, model, extra)}")
                await asyncio.sleep(1.5)

            if model.provider == "groq":
                for fmt in ("hidden", "parsed"):
                    extra = {"reasoning_format": fmt}
                    print(f"  {'format=' + fmt:<30}-> {await _ask(client, model, extra)}")
                    await asyncio.sleep(1.5)

    print("\nEvery line must agree with the mode: no HTTP 400s, and no 'INLINE <think>'")
    print("survives once reasoning_format is sent. Mismatch => fix models.reasoning_mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
