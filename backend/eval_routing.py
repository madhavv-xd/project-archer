"""Self-serve routing eval — the shadow soak, minus the users.

Runs a labeled query set through BOTH routers locally and reports:
  - keyword accuracy vs the hand label
  - embedding accuracy vs the hand label (as it would actually route: embedding
    if similarity >= threshold, else keyword fallback)
  - agreement between the two, and every disagreement, so you can eyeball
    whether embedding was smarter on the cases keyword gets wrong.

Run: uv run python eval_routing.py   (needs EMBEDDING_API_KEY in .env)

The query set leans on KEYWORD-FREE paraphrases on purpose — those are the whole
reason 2B exists, so that's where embedding should earn its keep.
"""

import asyncio

from app.config import settings
from app.core.embeddings import embedding_route
from app.core.router import keyword_route

# keyword routing_reason -> domain (so both routers speak the same 6 buckets)
REASON_DOMAIN = {
    "coding_keywords": "coding",
    "math_keywords": "math",
    "writing_keywords": "writing",
    "simple_query": "simple",
    "analysis_keywords": "analysis",
    "default": "general",
}

# (query, expected_domain). Mix of keyword-free paraphrases (hard) and a few
# obvious ones. Edit freely — this is your eval set.
CASES = [
    # coding — mostly no whitelisted coding word
    ("my program keeps crashing on line 40", "coding"),
    ("the app freezes whenever I hit save", "coding"),
    ("how do I make this loop run faster", "coding"),
    ("why does my recursive call blow the stack", "coding"),
    ("connect my backend to a postgres database", "coding"),  # has 'database'
    ("help me debug this python function", "coding"),          # obvious
    ("tests pass locally but fail in the pipeline", "coding"),
    # math — no whitelisted math word in most
    ("if a train goes 60mph for two hours how far", "math"),
    ("whats the chance of rolling two sixes in a row", "math"),
    ("how many ways can I arrange five books", "math"),
    ("reduce this fraction to lowest terms", "math"),
    ("solve this integral step by step", "math"),              # obvious
    ("how much interest at 5 percent over 3 years", "math"),
    # writing
    ("help me put together a birthday message for my mom", "writing"),
    ("make this sound more professional", "writing"),
    ("give me a catchy tagline for my coffee shop", "writing"),
    ("turn these bullet points into a paragraph", "writing"),
    ("write a short poem about the ocean", "writing"),          # obvious
    ("craft a toast for my best friends wedding", "writing"),
    # simple
    ("hey there", "simple"),
    ("whats the capital of france", "simple"),
    ("who painted the mona lisa", "simple"),
    ("how tall is mount everest", "simple"),
    ("good morning", "simple"),
    ("how do you spell restaurant", "simple"),
    # analysis
    ("weigh the upsides and downsides of remote work", "analysis"),
    ("which of these three vendors should we pick and why", "analysis"),
    ("break down whats really driving our customer churn", "analysis"),
    ("compare these strategies across cost risk and timeline", "analysis"),  # obvious
    ("whats the long term consequence of raising prices", "analysis"),
    # general
    ("tell me something cool about deep sea creatures", "general"),
    ("what should I cook with chicken and rice", "general"),
    ("explain how airplanes stay in the air", "general"),
    ("how do bees make honey", "general"),
    ("recommend a beginner houseplant thats hard to kill", "general"),
    ("what causes the northern lights", "general"),
]


async def main() -> None:
    thr = settings.EMBEDDING_SIMILARITY_THRESHOLD
    assert settings.EMBEDDING_API_KEY, "set EMBEDDING_API_KEY in .env first"
    print(f"threshold={thr}  cases={len(CASES)}\n")

    kw_correct = emb_correct = agree = 0
    disagreements = []
    print(f"{'expected':9} {'keyword':9} {'embedding':16} query")
    print("-" * 80)
    for query, expected in CASES:
        kw_domain = REASON_DOMAIN[keyword_route(query)[1]]
        domain, sim = await embedding_route(query)
        # As deployed: embedding decides only above threshold, else keyword.
        emb_domain = domain if sim >= thr else kw_domain
        emb_label = f"{emb_domain}({sim:.2f})" if sim >= thr else f"kw:{kw_domain}({sim:.2f})"

        kw_correct += kw_domain == expected
        emb_correct += emb_domain == expected
        agree += kw_domain == emb_domain
        if kw_domain != emb_domain:
            disagreements.append((query, expected, kw_domain, emb_domain, sim))

        flag = "" if emb_domain == expected else "  <-- embedding miss"
        print(f"{expected:9} {kw_domain:9} {emb_label:16} {query}{flag}")

    n = len(CASES)
    print("\n" + "=" * 80)
    print(f"keyword   accuracy vs label: {kw_correct}/{n}  ({kw_correct/n*100:.0f}%)")
    print(f"embedding accuracy vs label: {emb_correct}/{n}  ({emb_correct/n*100:.0f}%)")
    print(f"agreement (same pick):       {agree}/{n}  ({agree/n*100:.0f}%)")
    print(f"\ndisagreements ({len(disagreements)}) — who was right?")
    for query, expected, kw, emb, sim in disagreements:
        kw_ok = "OK" if kw == expected else "X"
        emb_ok = "OK" if emb == expected else "X"
        print(f"  expected={expected:9} keyword={kw:9}[{kw_ok}] embedding={emb:9}[{emb_ok}] sim={sim:.2f}  {query}")


if __name__ == "__main__":
    asyncio.run(main())
