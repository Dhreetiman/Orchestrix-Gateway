# Orchestrix Gateway

A production-grade AI API Gateway that sits between your applications and LLM providers, adding **intelligent routing**, **distributed caching**, **observability**, **retries**, **rate limiting**, and **cost monitoring** — all behind a single OpenAI-compatible endpoint.

> Status: **All three phases are implemented and runnable end-to-end.** Backend gateway, multi-provider routing + observability, and the macOS-styled Next.js dashboard.

---

## Why

LLM applications quickly accumulate provider-specific glue: retry logic, cost tracking, request logging, cache layers, per-team rate limits. Orchestrix Gateway centralizes that plumbing so applications stay thin and operators get a single pane of glass over LLM traffic.

## Architecture

```
            ┌────────────────────────┐
 Client ──▶ │  FastAPI Gateway       │ ──▶ Provider Adapter (OpenAI / Anthropic)
            │  - Auth (API keys)     │         │
            │  - Rate limit          │         └─▶ retries + failover
            │  - Cache lookup        │     ┌──────────────┐
            │  - Routing engine      │ ──▶ │ Redis        │ (cache + rate limit)
            │  - Streaming (SSE)     │     └──────────────┘
            │  - Logging / metrics   │     ┌──────────────┐
            └──────────┬─────────────┘ ──▶ │ PostgreSQL   │ (request logs, api_keys)
                       │ /metrics          └──────────────┘
                       ▼
               Prometheus ──▶ Grafana   ✅ provisioned
```

Design principles:

- **HTTP-only providers.** No vendor SDKs — every upstream is plain `httpx`, so the gateway owns the request lifecycle (cache key, retries, streaming pass-through, cost calc).
- **OpenAI-compatible surface.** Existing OpenAI client libraries drop in by changing the base URL.
- **Stateless API tier.** All state lives in Postgres + Redis. Containers scale horizontally without coordination.

---

## Tech Stack

| Layer          | Tech                                                       |
| -------------- | ---------------------------------------------------------- |
| Language       | Python 3.12, async-first                                   |
| Web            | FastAPI + Uvicorn                                          |
| Persistence    | PostgreSQL 16 (SQLAlchemy 2.0 async + Alembic migrations)  |
| Cache          | Redis 7 (`redis.asyncio`)                                  |
| Providers      | OpenAI + Anthropic (Phase 2); Gemini scoped for later      |
| Observability  | structlog (JSON, secret-redacted), Prometheus, Grafana     |
| Infrastructure | Docker, Docker Compose                                     |
| Frontend       | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn-style UI (macOS-styled, dark mode) |

---

## Repository Layout

```
Orchestrix-Gateway/
├── backend/                  FastAPI gateway
│   ├── app/
│   │   ├── api/              chat, health endpoints + Pydantic schemas
│   │   ├── cache/            Redis client, cache key strategy
│   │   ├── core/             config, structlog, exceptions, security
│   │   ├── db/                models, session, Alembic migrations
│   │   ├── middleware/        API-key auth
│   │   ├── providers/         Provider Protocol + OpenAI / Mock impls
│   │   ├── routing/           model → provider routing
│   │   ├── services/          cost calculator, request logger
│   │   └── main.py            app factory
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                 Next.js dashboard (Phase 3)
├── infra/                    Prometheus, Grafana, NGINX configs
├── docker-compose.yml
├── Makefile
└── .env.example
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- (Optional, for local dev) Python 3.12

### 1. Clone & configure

```bash
git clone https://github.com/<you>/Orchestrix-Gateway.git
cd Orchestrix-Gateway
cp .env.example .env
# Edit .env to set OPENAI_API_KEY if you want real OpenAI calls.
```

### 2. Bring up the stack

```bash
make up         # builds and starts api + postgres + redis
make logs       # tail logs across services
```

The API is now live at <http://localhost:8000>. Other surfaces:

- <http://localhost:3000> — **Dashboard** (macOS-styled Next.js UI)
- <http://localhost:8000/docs> — Swagger UI
- <http://localhost:8000/metrics> — Prometheus metrics
- <http://localhost:9090> — Prometheus
- <http://localhost:3001> — Grafana (anonymous viewer access; admin/admin to log in)

### 3. Seed an API key

```bash
make seed
# →  API key created.
# →    name: default
# →    key:  ogw_<long-random-string>
# →    Save this now — it will NOT be shown again.
```

### 4. Make a request

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ogw_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "gpt-4o-mini",
        "messages": [{"role":"user","content":"Hello from Orchestrix!"}]
      }'
```

The **second identical call** returns from Redis in single-digit milliseconds with `X-Cache: HIT`. Inspect Postgres to confirm:

```bash
make psql
> SELECT provider, model, tokens_in, tokens_out, cost_usd, latency_ms, cache_hit FROM request_logs ORDER BY created_at DESC LIMIT 5;
```

### 5. Streaming

```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ogw_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Stream please"}],"stream":true}'
```

SSE chunks flow back token-by-token. The full request is logged with `streamed=true` after the stream completes.

### 6. Try without real API keys

Use the built-in `mock` provider — no upstream needed:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer ogw_<your-key>" \
  -d '{"model":"mock","messages":[{"role":"user","content":"ping"}]}'
```

---

## API Endpoints

| Endpoint                     | Auth     | Description                                          |
| ---------------------------- | -------- | ---------------------------------------------------- |
| `POST /v1/chat/completions`  | API key  | OpenAI-compatible chat — routes to OpenAI or Anthropic, with caching, retries, and failover |
| `GET /metrics`               | none     | Prometheus metrics                                   |
| `GET /health`                | none     | Liveness                                             |
| `GET /ready`                 | none     | Readiness — pings Postgres + Redis                   |
| `GET /docs`                  | none     | Swagger UI                                           |

Response headers:

- `X-Cache: HIT|MISS` — cache outcome
- `X-Served-By: openai|anthropic|mock` — which upstream actually answered (helpful when failover kicks in)
- `X-Request-ID` — correlation ID echoed back for tracing

## Multi-provider Routing

Models are mapped to a primary provider plus an ordered failover chain. If the primary upstream returns a terminal error (e.g. 401), the next provider in the chain is tried automatically. Failover is non-streaming only — replaying a partial stream is unsafe.

| Model prefix       | Primary    | Failover    |
| ------------------ | ---------- | ----------- |
| `gpt-4o`, `gpt-4`, `gpt-3.5` | OpenAI    | Anthropic   |
| `o1-`, `o3-`       | OpenAI     | —           |
| `claude-3-5`, `claude-3` | Anthropic | OpenAI |
| `mock`             | Mock       | —           |

Toggle failover globally with `ENABLE_FAILOVER=false`.

## Rate Limiting

Per-API-key sliding window in Redis. Default: **60 requests/minute** (`RATE_LIMIT_RPM`). Rejected requests return `429` with a `retry_after_seconds` field in the error body.

```json
{
  "error": {
    "code": "rate_limited",
    "message": "Rate limit exceeded (60 requests/min).",
    "detail": {"retry_after_seconds": 12}
  }
}
```

## Observability

- **Structured JSON logs** via structlog, with request IDs propagated through `contextvars`. Known API-key shapes are auto-redacted (`sk-…`, `sk-ant-…`, `ogw_…`, bearer tokens).
- **Prometheus metrics** exposed at `/metrics` — requests, latency histogram, tokens, cost, provider errors, rate-limit rejections, active streams.
- **Grafana** at `http://localhost:3001` ships with a provisioned **Orchestrix Gateway — Overview** dashboard.

---

## Development

### Local (without Docker)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Point .env at host-mapped services
sed -i '' 's/@postgres:/@localhost:/; s/@redis:/@localhost:/' ../.env

alembic upgrade head
uvicorn app.main:app --reload
```

### Make targets

```bash
make help                # list everything
make up / down / logs    # docker-compose lifecycle
make migrate             # run alembic upgrade head inside api container
make seed                # create an API key
make psql / redis-cli    # open a shell against the running service
make test                # run backend tests
make lint / format       # ruff lint + format
make typecheck           # mypy strict
make web-dev             # pnpm dev — Next.js dashboard
make web-build           # production build
make web-lint            # ESLint
make web-types           # tsc --noEmit
```

### Frontend dev loop

```bash
cd frontend
pnpm install
pnpm dev    # http://localhost:3000 → proxies /api/gateway/* to http://localhost:8000
```

Open the dashboard, go to **Settings**, paste a gateway API key (from `make seed`), and the rest of the pages light up.

### Quality gates

- `ruff check` — lint (passes)
- `ruff format` — formatter
- `mypy --strict` — static typing (passes)
- `pytest` — unit + integration tests

---

## Roadmap

### ✅ Phase 1 — Foundational Gateway (done)

- FastAPI service with structured logging and request IDs
- API-key authentication (`ogw_*` bearer tokens, SHA-256 hashed at rest)
- OpenAI provider with non-streaming + SSE streaming
- Redis-backed response cache (temperature-gated)
- Cost + token + latency logging to Postgres
- Mock provider for offline development
- Docker Compose stack with healthchecks
- Alembic migrations
- Unit tests, ruff, mypy strict

### ✅ Phase 2 — Resilience, Observability, Security (done)

- Anthropic provider (OpenAI-shape translation, streaming + non-streaming)
- Provider-level retries with exponential backoff + jitter
- Multi-provider routing with automatic failover
- Per-API-key sliding-window rate limiting in Redis
- Prometheus metrics at `/metrics` + provisioned Grafana dashboard
- Secret redaction in logs, request body size limit, CORS

### ✅ Phase 3 — macOS-Inspired Dashboard (done)

- Next.js 15 (App Router) + TypeScript + TailwindCSS + shadcn-style components
- macOS design language: translucent vibrancy surfaces, Inter typography, traffic-light chrome on sidebar, `rounded-2xl` cards with hairline borders + soft layered shadows, system-following dark mode via `next-themes`, refined Recharts palette (muted Sonoma blues/greens/oranges)
- **Dashboard** — KPI cards (requests, cache hit ratio, p95 latency, spend), traffic area chart, provider distribution donut
- **Request Logs** — paginated infinite-scroll table with provider/status/cache/model filters and row-expand details
- **Analytics** — latency trend, tokens stacked bars, cost bars, cache hit ratio over time
- **Settings** — set a browser session API key, plus list / create / revoke gateway keys
- All admin pages talk to typed `/admin/*` endpoints on the backend via a TanStack Query + Zustand state layer
- Wired into Docker Compose as a `frontend` service; `pnpm dev` for local development

### Backend Admin API (powering the dashboard)

| Endpoint                              | Description                                |
| ------------------------------------- | ------------------------------------------ |
| `GET  /admin/stats/overview`          | KPIs for the time window                   |
| `GET  /admin/stats/series`            | Time-bucketed series (minute/hour/day)     |
| `GET  /admin/stats/providers`         | Per-provider slice                         |
| `GET  /admin/logs`                    | Paginated request logs with filters        |
| `GET  /admin/api-keys`                | List API keys                              |
| `POST /admin/api-keys`                | Create API key (returned once)             |
| `POST /admin/api-keys/{id}/revoke`    | Revoke an API key                          |

---

## License

MIT — see [LICENSE](LICENSE).
