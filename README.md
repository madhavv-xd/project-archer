# Archer

**Orchestration-as-a-Service.** Archer is a smart proxy in front of multiple LLM providers that auto-routes each query to the model best suited for it. Call one OpenAI-compatible endpoint with one API key — Archer decides which model answers. Every response reports `"model": "archer-auto"` and the underlying provider is invisible to the client.

Inspired by Sakana AI's Fugu Technical Report.

---

## Quick start — use the live instance

| Component | URL |
|---|---|
| **Frontend (Dashboard)** | https://project-archer.online |
| **Backend (API)** | https://api.project-archer.online |
| **Swagger docs** | https://api.project-archer.online/docs |

### 1. Register & get a key

Open the dashboard → **Register** → log in → **API Keys** → **Create New Key**. Copy your key immediately — it is shown once (`arch_sk_` + 48 chars) and never stored in plaintext.

### 2. Send a request

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.project-archer.online/v1",
    api_key="arch_sk_YOUR_KEY",
)
resp = client.chat.completions.create(
    model="anything",  # ignored — Archer decides
    messages=[{"role": "user", "content": "compare REST and GraphQL"}],
)
print(resp.choices[0].message.content)
# response says model="archer-auto"
```

```bash
curl https://api.project-archer.online/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer arch_sk_YOUR_KEY" \
  -d '{"model": "anything", "messages": [{"role": "user", "content": "compare REST and GraphQL"}]}'
```

### 3. View logs

Check the **Logs** page to see every request — the real model used, routing reason, token counts, and latency.

---

## Project status — Phase 1 complete

| Sub-phase | Scope | Status |
|---|---|---|
| **1A** | Backend foundation: config, async DB, 4 tables, repos, schemas, Alembic migration + 5-model seed | done |
| **1B** | Backend API: providers, keyword router, normalizer, proxy + fallback chain, both auth systems, all 11 routes | done |
| **1C** | Frontend: NextAuth credential flow, route guard, dashboard pages (stats, API keys, models, logs) | done |
| **1D** | Docker + Nginx + AWS EC2/ECR + GitHub Actions CI/CD | done |

---

## Architecture

Archer has two independent architectures worth understanding separately: how a **request is processed** once it reaches the backend, and how the backend is **built, shipped, and kept running** on AWS. They're decoupled on purpose — the application has no idea it's running in a container on EC2 versus anywhere else.

### 1. Request architecture

```
                     ┌─────────────────────────────────────────────┐
  Your app            │                 Archer                       │
  (OpenAI SDK,       │                                              │
   curl, Postman)    │  POST /v1/chat/completions                    │
       │             │       │                                       │
       │ arch_sk_ key│       ▼                                       │
       └────────────>│  keyword router → picks best model            │
                     │       │                                       │
                     │       ▼                                       │
                     │  provider call (Groq / OpenRouter)            │──→ free LLMs
                     │       │  └─ fallback chain on error           │
                     │       ▼                                       │
                     │  normalize → "archer-auto" → log to Postgres   │──→ Neon
                     └─────────────────────────────────────────────┘
```

**Why it's shaped this way:**
- **Routing is keyword-based, not ML, on purpose.** Phase 1's goal is to prove the orchestration concept end-to-end before spending effort on a trained router (that's Phase 3). Keyword rules are cheap, deterministic, and testable (`backend/tests/test_router.py`).
- **The model cache is loaded once at startup** (`app/main.py` `lifespan`), so the hot path never hits Postgres to resolve a model name — only to log the request afterward.
- **Fallback only retries on retryable errors** (`rate_limit`, `server_error`, `timeout`). A `client_error` is never retried, because a bad request fails identically on every model in the chain — retrying would just burn a rate-limit slot on a second provider for nothing.
- **Logging is fire-and-forget** (`asyncio.create_task`). A slow logging write should never make the caller wait longer for their LLM response.

### Routing rules

Archer inspects the last user message and runs keyword rules in priority order:

| Route | Keywords / Condition | Model | Provider |
|---|---|---|---|
| **coding / default** | `python`, `function`, `debug`, `api`, `sql`, `algorithm`, ... | **Llama 3.3 70B** | Groq |
| **math** | `calculate`, `derivative`, `integral`, `equation`, `theorem`, ... | **GPT-OSS 120B** | Groq |
| **simple / short** | `< 15 words` or starts with `hi`, `hello`, `what is`, `define`, ... | **Llama 3.1 8B** | Groq |
| **analysis** | `analyze`, `compare`, `pros and cons`, `explain thoroughly`, ... | **Qwen 2.5 72B** | OpenRouter |
| **writing / chat** | `write`, `essay`, `poem`, `story`, `draft`, `edit`, ... | **GPT-OSS 20B** | Groq |
| **default** | everything else | **Llama 3.3 70B** | Groq |

**Fallback chain** (walked on retryable errors — rate limit, server error, timeout):
```
Llama 3.3 70B → GPT-OSS 120B → Llama 3.1 8B → Qwen 2.5 72B → GPT-OSS 20B
```

Non-retryable errors stop the chain immediately. If all models fail, a `503` is returned. Fallbacks are logged with a `_fallback` suffix.

### Request lifecycle

1. **Auth** — extract Bearer token → hash with `SHA-256(key + salt)` → lookup → `401`/`403` if invalid → fire-and-forget `last_used_at` update
2. **Parse body** — validate via Pydantic; `stream: true` → `400` ("not supported in Phase 1"); `model` field is **ignored**
3. **Route** — `keyword_route()` on last user message → `(model_name, reason)`
4. **Model lookup** — in-memory cache (populated once at startup, never hits DB on hot path)
5. **Provider call** — try selected model; walk fallback chain on retryable errors
6. **Normalize** — stamp every response into the `archer-auto` OpenAI-compatible shape
7. **Log** — `asyncio.create_task` (fire-and-forget, never blocks the response)
8. **Return** — normalized response to the client

---

### 2. Deployment architecture (AWS)

The frontend and backend deploy independently, to different platforms, for a deliberate reason (see below). The backend is the piece that runs on AWS.

```
┌─────────────┐         ┌────────────────────────────────────────────────────────────────┐
│   Browser   │         │                         GitHub                                  │
│  (any user) │         │  push to main (paths: backend/**, nginx/**,                     │
└──────┬──────┘         │  docker-compose.prod.yml, workflow file)                        │
       │                │            │                                                    │
       │ HTTPS           │            ▼  .github/workflows/deploy.yml                      │
       ▼                │  ┌──────────────────────────────────────────────────────────┐  │
┌─────────────┐         │  │ 1. checkout                                              │  │
│   Vercel     │         │  │ 2. configure-aws-credentials (IAM user: github-actions- │  │
│  (Next.js    │         │  │    archer, policy: AmazonEC2ContainerRegistryPowerUser, │  │
│  frontend)   │         │  │    keys stored as GitHub Actions secrets)               │  │
└──────┬──────┘         │  │ 3. docker build ./backend → tag :latest AND :<git-sha>  │  │
       │ fetch()          │  │ 4. docker push both tags to ECR                         │  │
       │ NEXT_PUBLIC_    │  │ 5. SSH (appleboy/ssh-action) to EC2 Elastic IP           │  │
       │ API_URL         │  │ 6. on box: ecr login (instance role) → compose pull →   │  │
       ▼                │  │    compose up -d → poll /health up to 10× → prune images│  │
api.project-archer       │  └──────────────────────────────────────────────────────────┘  │
.online (DNS A record)  └────────────────────────────────┬───────────────────────────────┘
       │                                                   │ docker push / pull
       ▼                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ AWS EC2 — t3.micro, Ubuntu, Elastic IP                              ┌───────────────┐│
│ Security group: 80/443 open to internet, 22 restricted to admin     │  Amazon ECR   ││
│                                                                      │  repo:         ││
│  ┌───────────────────────── docker compose (prod) ───────────────┐ │  archer-backend││
│  │                                                                 │ │  tags: latest, ││
│  │   nginx:alpine container            backend container          │ │  <git-sha>     ││
│  │   ─────────────────────            ────────────────────        │ └───────┬───────┘│
│  │   :80  → 301 redirect to :443       FastAPI (uvicorn)           │         │        │
│  │   :80  /.well-known/acme-challenge  bound to 127.0.0.1:8000 ONLY│  pulled via      │
│  │        (Certbot HTTP-01 renewal)    — never reachable directly  │  instance IAM    │
│  │   :443 TLS (Let's Encrypt certs,    from the public internet    │  role            │
│  │        mounted read-only from host) │                            │  archer-ec2-role │
│  │   :443 proxy_pass → backend:8000    healthcheck: GET /health     │  (ECR-ReadOnly,  │
│  │        (same docker network)        every 30s, 3 retries        │  no static keys  │
│  │   proxy_read/send_timeout 120s      restart: unless-stopped     │  on the box)     │
│  │        (LLM calls are slow)                                     │                  │
│  └─────────────────────────────────────────┬───────────────────────┘                  │
│                                              │                                          │
│  Host (outside compose):                    │                                          │
│   - Certbot (systemd timer) renews certs    │                                          │
│     into /etc/letsencrypt, --webroot         │                                          │
│   - 2 GB swap file (t3.micro has 1 GB RAM)  │                                          │
│   - ~/archer/.env (chmod 600, never          │                                          │
│     committed): DATABASE_URL, GROQ_API_KEY,  │                                          │
│     OPENROUTER_API_KEY, JWT_SECRET,          │                                          │
│     API_KEY_SALT, FRONTEND_URL,              │                                          │
│     OAUTH_INTERNAL_SECRET                    │                                          │
└──────────────────────────────────────────────┼──────────────────────────────────────────┘
                                                 │
                                    ┌────────────┴────────────┐
                                    ▼                          ▼
                          ┌──────────────────┐      ┌────────────────────┐
                          │   Neon Postgres    │      │  Groq / OpenRouter  │
                          │  (managed, TLS,     │      │  (LLM providers,    │
                          │   not on EC2)        │      │   free tier)        │
                          └──────────────────┘      └────────────────────┘
```

**Design decisions, and why:**

| Decision | Why |
|---|---|
| **Frontend stays on Vercel; only the backend moved to AWS** | The backend is the stateful-looking-but-actually-stateless piece worth controlling directly (custom domain, container control, cost visibility). Keeping the frontend on Vercel avoids a second Dockerfile, a NextAuth env migration, and gives up nothing — Vercel's CDN and zero-config deploys are strictly better for a static/SSR frontend than self-hosting one on a 1 GB box. |
| **`t3.micro`, not a larger instance** | Free-tier eligible for 12 months, and the backend is I/O-bound (`httpx` calls out to Groq/OpenRouter, `asyncpg` to Neon) rather than CPU-bound — it doesn't need much compute. A 2 GB swap file absorbs the 1 GB RAM ceiling. Resizing later (stop → change instance type → start) is non-disruptive since the Elastic IP survives it. |
| **Backend container bound to `127.0.0.1:8000` only** | Nginx and the backend share a Docker network, so Nginx can reach it, but the port is never published to the instance's public interface. The **only** public entry points are Nginx's 80/443. This means even a misconfigured security group can't expose the raw FastAPI process. |
| **Nginx runs as a compose service; Certbot runs on the host** | Nginx-in-compose keeps the whole stack reproducible from two files (`docker-compose.prod.yml` + `nginx/nginx.conf`) with nothing hand-installed. Certbot as a host package (not a container) avoids wiring a renewal-hook container and its own volume/network — a plain systemd timer renews certs into `/etc/letsencrypt`, which Nginx mounts read-only. Initial issuance uses `--standalone` (port 80 free, before Nginx's first start); renewals use `--webroot` through the already-running Nginx. |
| **One ECR repo, two tags per push (`latest` + `<git-sha>`)** | `latest` is what the box normally runs; the sha tag is a point-in-time rollback — set `IMAGE_TAG` in the server's `.env` and `docker compose up -d` to pin an older image, no rebuild required. |
| **Two separate AWS identities, least privilege each direction** | **EC2 → ECR (pull):** an *instance IAM role* (`archer-ec2-role`) with the AWS-managed `AmazonEC2ContainerRegistryReadOnly` policy — no static credentials ever live on the box; `aws ecr get-login-password` authenticates via the instance metadata service, re-run on every deploy (ECR tokens expire in 12h). **GitHub Actions → ECR (push):** a separate *IAM user* (`github-actions-archer`) with `AmazonEC2ContainerRegistryPowerUser`, whose access key lives only as encrypted GitHub Actions secrets. Neither identity can do what the other can. |
| **Deploy = SSH + `docker compose pull && up -d`, not a managed deploy service** | Simple, debuggable, and matches a single-box topology. The workflow gates success on a real health check (polls `GET /health` up to 10× before declaring victory) and runs `docker system prune -f` after, so stale image layers don't fill the 30 GB disk over time. A few seconds of downtime during the container swap is accepted for Phase 1 — zero-downtime rolling deploys are explicitly deferred to a later scaling phase. |
| **Neon (managed Postgres), never a DB container on EC2** | Keeps the box stateless and disposable — it can be destroyed and recreated from the same Docker image + `.env` with no data migration. Neon also handles TLS and backups so the box doesn't have to. |

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | **Python 3.12**, **FastAPI** (async) |
| ORM / migrations | **SQLAlchemy 2.0** async + **Alembic** |
| Package manager | **uv** (no `requirements.txt`) |
| Database | **Neon** (managed serverless Postgres) — no local container |
| Frontend | **Next.js 16** (App Router) + **React 19**, **Tailwind v4**, shadcn/ui, **NextAuth** |
| Providers | **Groq** + **OpenRouter** (both OpenAI-compatible, free tier) |
| Deployment | Docker on **AWS EC2** (t3.micro), images via **ECR**, Nginx + Let's Encrypt TLS |
| CI/CD | **GitHub Actions** — builds image → pushes to ECR → SSH + pulls + restarts on EC2 |

---

## Two separate auth systems

They share one Swagger Authorize box but expect different token types.

| Auth system | Token format | Protects |
|---|---|---|
| Dashboard auth | **JWT** (HS256, from `POST /auth/login`, or via Google/GitHub OAuth → `POST /auth/oauth`) | `/api-keys`, `/models`, `/logs`, `/dashboard/*` |
| LLM API auth | **API key** (`arch_sk_` + 48 chars) | `/v1/*` |

API keys are stored as `SHA-256(key + API_KEY_SALT)` — the full key is shown **exactly once** at creation and never stored in plaintext. OAuth sign-in issues the same backend JWT as password login (NextAuth's `jwt` callback exchanges the provider handshake for one via `/auth/oauth`), so `session.accessToken`, `proxy.ts`, and `get_current_user` all behave identically regardless of how the user signed in.

---

## Local development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+
- A free [Neon](https://neon.tech) Postgres database and keys from [Groq](https://console.groq.com) + [OpenRouter](https://openrouter.ai)

### Backend

```bash
cd backend
cp .env.example .env       # fill in the values
uv sync                     # install deps
uv run alembic upgrade head # create tables on Neon + seed 5 models
uv run uvicorn app.main:app --reload --port 8000
```

**`backend/.env`:**
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DB?sslmode=require
GROQ_API_KEY=gsk_...
OPENROUTER_API_KEY=sk-or-...
API_KEY_SALT=            # openssl rand -hex 32
JWT_SECRET=              # openssl rand -hex 32
FRONTEND_URL=http://localhost:3000
```

> Archer normalizes the Neon URL internally — paste the standard connection string as-is.

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

**`frontend/.env.local`:**
```env
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=              # openssl rand -hex 32
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Trying it out

1. Open http://localhost:3000 → **Register** → log in
2. **API Keys** → **Create New Key** → copy the `arch_sk_…` key
3. Open Swagger at http://localhost:8000/docs → **Authorize** with the key
4. Try `POST /v1/chat/completions` with `{"model":"anything","messages":[{"role":"user","content":"write a Python function"}]}`
5. Check the **Logs** page on the dashboard to see routing decisions

**Note:** swap the Authorize box value between your JWT and `arch_sk_` key depending on which endpoint you test.

### Running the stack locally in Docker

`docker-compose.yml` builds the backend from source and fronts it with plain-HTTP Nginx (no TLS) — useful for testing the Nginx reverse-proxy config itself without touching production:

```bash
docker compose up --build
curl localhost/health
```

### Running tests

```bash
cd backend
uv run pytest   # tests/test_router.py, test_proxy.py, test_normalizer.py
```

---

## API reference

### Public

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/health` | — | status + models loaded |
| POST | `/auth/register` | `{email, password, name?}` | `UserResponse` |
| POST | `/auth/login` | `{email, password}` | `{access_token, user}` |

### Dashboard (Bearer JWT)

| Method | Path | Notes |
|---|---|---|
| GET / POST / DELETE | `/api-keys` / `/api-keys/{id}` | POST returns full key once |
| GET | `/models` | model catalog |
| GET | `/logs?page=&limit=` | paginated request logs |
| GET | `/dashboard/stats` | totals, success rate, most-used model |

### LLM API (Bearer `arch_sk_...`)

| Method | Path | Notes |
|---|---|---|
| POST | `/v1/chat/completions` | OpenAI-compatible; `stream:true` → 400 |
| GET | `/v1/models` | returns the single virtual `archer-auto` model |

---

## Repository structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI entry: CORS, lifespan, 7 routers
│   │   ├── config.py            Pydantic Settings (single env-var source)
│   │   ├── core/
│   │   │   ├── router.py        keyword_route() — routing decision
│   │   │   ├── proxy.py         ModelCache + call_with_fallback()
│   │   │   ├── normalizer.py    unify provider responses → "archer-auto"
│   │   │   └── security.py      bcrypt, JWT, arch_sk_ generation & hashing
│   │   ├── providers/
│   │   │   ├── base.py          shared httpx client + ProviderError
│   │   │   ├── groq.py          GroqProvider (URL + headers)
│   │   │   └── openrouter.py    OpenRouterProvider
│   │   ├── db/
│   │   │   ├── database.py      async engine, session, get_db
│   │   │   ├── models.py        4 tables: users, api_keys, models, request_logs
│   │   │   └── repositories/    one module per table (function-style)
│   │   ├── api/
│   │   │   ├── routes/          chat, auth, api_keys, models, logs, dashboard, health
│   │   │   └── middleware/auth.py  get_current_user (JWT) + get_api_key
│   │   └── schemas/             Pydantic models: chat, auth, api_keys, common
│   ├── alembic/versions/        001_initial (tables + 5-model seed), 002_add_oauth
│   ├── tests/                   pytest suite (router, proxy, normalizer)
│   ├── Dockerfile               builds the production backend image
│   └── pyproject.toml           uv-managed, no requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── (auth)/              login, register pages
│   │   ├── (dashboard)/         dashboard, api-keys, models, logs
│   │   └── api/auth/[...nextauth]/
│   ├── lib/                     auth.ts (NextAuth), api.ts (typed fetch)
│   ├── components/              layout, dashboard, forms, ui
│   └── proxy.ts                 route guard (Next.js 16 renamed Middleware)
│
├── nginx/
│   ├── nginx.conf                production reverse proxy + TLS (runs on EC2)
│   └── nginx.local.conf          plain-HTTP config for local `docker-compose.yml`
├── docker-compose.yml            local dev (builds from source, no TLS)
├── docker-compose.prod.yml       production (pulls prebuilt image from ECR, runs on EC2)
└── .github/workflows/deploy.yml  CI/CD: build → push to ECR → SSH → restart on EC2
```

> A few files you'll see locally but **won't** find in this list on GitHub — `CLAUDE.md`, `context.md`, `ROADMAP.md`, and `openspec/` are excluded via `.gitignore`. They're internal planning/spec documents for development-time use, not part of the shipped project, so don't expect their links to resolve on the hosted repo.

---

## Roadmap

Phase 1 (this repo, as documented above) is complete. Planned direction beyond it:

| Phase | Focus | Key additions |
|---|---|---|
| **2** | Make it a product | Embedding-based routing, Redis rate limiting, Stripe billing, workspaces, richer dashboard |
| **3** | Real intelligence | Trained ML routing head (Fugu-style soft-target + KL-divergence), ONNX inference, per-workspace personalization |
| **4** | Multi-step workflows | Conductor LLM designs multi-model workflows, memory isolation (access-list pattern), LangGraph execution |
| **5** | Scale | ECS auto-scaling, Multi-AZ database, canary deploys, OpenTelemetry, Sentry error tracking |

### Phase 1 limitations

- No streaming, billing, ML routing, multi-step workflows, or local models
- Single EC2 instance, no auto-scaling or zero-downtime deploys yet (both are Phase 5 concerns)
