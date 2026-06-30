# Archer

**Orchestration-as-a-Service.** Archer is a smart proxy that sits in front of multiple LLM providers and automatically routes each request to the model best suited for it. You call one OpenAI-compatible endpoint with one API key — Archer decides which underlying model answers, and you never have to know or care which one it was.

> Inspired by the idea of *orchestration as a scaling axis* (Sakana AI's Fugu report): intelligent routing across existing models can match or beat any single frontier model, without training a bigger one. Archer is a small, accessible, open implementation of that idea. The full vision and 5‑phase roadmap live in [`context.md`](./context.md).

---

## What it does (Phase 1)

```
                         ┌──────────────────────────────────────────────┐
   Your app              │                  Archer                       │
   (OpenAI SDK,          │                                               │
    curl, Postman)       │   POST /v1/chat/completions                   │
        │                │        │                                      │
        │  arch_sk_ key  │        ▼                                      │
        └───────────────▶│   keyword router ──▶ picks best model         │
                         │        │                                      │
                         │        ▼                                      │
                         │   provider call (Groq / OpenRouter)           │──▶ free cloud LLMs
                         │        │   └─ fallback chain on error          │
                         │        ▼                                      │
                         │   normalize → "archer-auto" → log to Postgres  │──▶ Neon
                         └──────────────────────────────────────────────┘
```

- **One OpenAI-compatible API.** Point any OpenAI client at Archer; the `model` field you send is **ignored** — Archer always chooses.
- **Keyword routing** across 5 free models (no ML yet — that's a later phase). Coding → a 70B model, math → a reasoning model, short/simple → a fast 8B model, etc.
- **Automatic fallback.** If the chosen model is rate-limited or errors, Archer transparently retries down a fixed chain.
- **Every request is logged** (model used, routing reason, tokens, latency, fallback) to Postgres.
- **A dashboard** (Next.js) to register, manage API keys, browse the model catalog, and view stats + paginated request logs.

### The 5 models & routing

| Route (keywords) | Model | Provider | Model string |
|---|---|---|---|
| coding / default | Llama 3.3 70B | Groq | `llama-3.3-70b-versatile` |
| simple / short | Llama 3.1 8B | Groq | `llama-3.1-8b-instant` |
| math | GPT-OSS 120B | Groq | `openai/gpt-oss-120b` |
| writing / chat | GPT-OSS 20B | Groq | `openai/gpt-oss-20b` |
| analysis | Qwen 2.5 72B | OpenRouter | `qwen/qwen-2.5-72b-instruct:free` |

**Fallback chain:** Llama 3.3 70B → GPT-OSS 120B → Llama 3.1 8B → Qwen 2.5 72B → GPT-OSS 20B.

All five are free-tier. Routing rules are checked in a fixed order (`context.md` §5.8); the responses are normalized so the client always sees `"model": "archer-auto"`.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.12, **FastAPI** (async), **SQLAlchemy 2.0 async** + **Alembic** |
| Package manager | **uv** (no `requirements.txt`) |
| Database | **Neon** (managed serverless Postgres) — not a local container |
| Frontend | **Next.js 16** (App Router) + React 19, **Tailwind v4**, shadcn/ui, **NextAuth v4** |
| Providers | **Groq** + **OpenRouter** (both natively OpenAI-compatible) |
| Deploy (Phase 1) | Docker + Nginx on a single AWS EC2, images via ECR, CI/CD via GitHub Actions *(not yet built)* |

---

## Project status

| Sub-phase | Scope | Status |
|---|---|---|
| **1A** | Backend foundation: config, async DB, 4 tables, repos, schemas, migration + 5-model seed | ✅ done & verified |
| **1B** | Backend API: providers, router, normalizer, proxy + fallback, both auth systems, all routes | ✅ done & verified |
| **1C** | Frontend: NextAuth, route guard, dashboard pages | ✅ done & verified |
| **1D** | Docker + Nginx + AWS (EC2/ECR) + GitHub Actions CI/CD | ⏳ not started |

---

## Architecture

Two components (a third, Nginx, arrives in 1D):

### `backend/`
```
app/
├── main.py            FastAPI app: CORS, startup model-cache load, routers
├── config.py          Pydantic Settings (single source of env vars)
├── core/
│   ├── router.py      keyword_route() — routing decision
│   ├── proxy.py       call_with_fallback() + in-memory model cache
│   ├── normalizer.py  unify any provider response → "archer-auto" shape
│   └── security.py    bcrypt, JWT, arch_sk_ key generation + hashing
├── providers/         base.py (shared httpx call) + groq.py / openrouter.py
├── db/                database.py, models.py (4 tables), repositories/
├── api/
│   ├── routes/        chat, auth, api_keys, models, logs, dashboard, health
│   └── middleware/    auth.py — get_current_user (JWT) + get_api_key
└── alembic/versions/  001_initial.py — creates tables + seeds 5 models
```

### `frontend/`
```
app/
├── (auth)/            login, register
├── (dashboard)/       dashboard, api-keys, models, logs (protected)
└── api/auth/[...nextauth]/route.ts
lib/                   auth.ts (NextAuth), api.ts (typed fetch)
proxy.ts               route protection (Next 16 renamed "middleware" → "proxy")
components/            layout, dashboard, api-keys, models, logs, ui
```

### Two separate auth systems (don't conflate them)
1. **Dashboard auth = JWT.** Register/login → bcrypt-checked → HS256 JWT. Protects the dashboard endpoints.
2. **LLM API auth = API keys.** Format `arch_sk_` + 48 chars, stored only as `SHA-256(key + salt)`, shown to you exactly once. Protects `/v1/*`.

---

## Getting started (local)

### Prerequisites
- [uv](https://docs.astral.sh/uv/), Node.js 20+, and a free **Neon** Postgres database.
- API keys from **Groq** and **OpenRouter** (both have free tiers).

### 1. Backend
```bash
cd backend
cp .env.example .env        # then fill in the values (see below)
uv sync                     # install dependencies
uv run alembic upgrade head # create tables on Neon + seed the 5 models
uv run uvicorn app.main:app --reload --port 8000
```
Backend runs at **http://localhost:8000** — interactive API docs at **http://localhost:8000/docs**.

**`backend/.env`:**
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require   # paste Neon's URL as-is
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
API_KEY_SALT=<random hex>      # e.g. `openssl rand -hex 32`
JWT_SECRET=<random hex>
FRONTEND_URL=http://localhost:3000
```
> Archer normalizes the Neon URL to the async driver internally, so you can paste the standard `postgresql://...sslmode=require` string without editing it.

### 2. Frontend
```bash
cd frontend
cp .env.example .env.local   # then fill in NEXTAUTH_SECRET
npm install
npm run dev
```
Frontend runs at **http://localhost:3000**.

**`frontend/.env.local`:**
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<random hex>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Trying it out

### Easiest: the dashboard
Open http://localhost:3000 → **Register** → go to **API Keys** → **Create New Key** and copy the `arch_sk_…` key (shown once). Browse **Models**, and after you send a request (below) watch it appear under **Logs**.

### Send a request to the LLM API
The dashboard has no chat box (Phase 1), so send one request via **Swagger** (`/docs` → **Authorize** with your `arch_sk_` key → `POST /v1/chat/completions`) or any OpenAI client:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="arch_sk_...")
resp = client.chat.completions.create(
    model="anything",  # ignored — Archer decides
    messages=[{"role": "user", "content": "Write a Python function to reverse a string"}],
)
print(resp.choices[0].message.content)  # answered by Llama 3.3 70B; response says model="archer-auto"
```

Try a math prompt (`"Calculate the derivative of x^2"`) or a short one (`"hello"`) and check the **Logs** page — the response always says `archer-auto`, but the log shows the real model + routing reason.

> **Note on Swagger's single Authorize box:** dashboard endpoints want your **JWT** (from `POST /auth/login`); `/v1/*` wants your **`arch_sk_` key**. Swap the value depending on what you're testing.

---

## API reference

**Public**
| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | status + models loaded |
| POST | `/auth/register` | `{email, password, name?}` | the new user |
| POST | `/auth/login` | `{email, password}` | `{access_token, user}` |

**Dashboard (Bearer JWT)**
| Method | Path | Notes |
|---|---|---|
| GET / POST / DELETE | `/api-keys` `/api-keys/{id}` | POST returns the full key **once** |
| GET | `/models` | model catalog |
| GET | `/logs?page=&limit=` | paginated request logs |
| GET | `/dashboard/stats` | totals, success rate, most-used model |

**LLM API (Bearer `arch_sk_…`)**
| Method | Path | Notes |
|---|---|---|
| POST | `/v1/chat/completions` | OpenAI-compatible; `stream:true` → HTTP 400 |
| GET | `/v1/models` | returns the single virtual `archer-auto` model |

---

## Roadmap (beyond Phase 1)

Each phase fixes the previous one's biggest limitation (full detail in `context.md`):

- **Phase 2 — make it a product:** Stripe billing, Redis rate limiting, workspaces, embedding-based routing, richer dashboard.
- **Phase 3 — real intelligence:** train a lightweight routing head (Fugu-style soft-target + KL-divergence), ONNX inference, per-workspace personalization.
- **Phase 4 — multi-step workflows:** a "Conductor" that designs multi-model workflows with memory isolation.
- **Phase 5 — scale:** ECS auto-scaling, Multi-AZ, observability, canary deploys.

### Phase 1 is intentionally limited
No billing, no rate limiting beyond what providers enforce, no streaming, no ML routing, single server. Don't add those here — see the not-in-scope list in `context.md` §5.1.

---

## Repository docs
- [`context.md`](./context.md) — the complete product spec and roadmap (source of truth).
- [`CLAUDE.md`](./CLAUDE.md) — orientation for AI coding agents, including where the implementation deliberately diverges from the spec.
