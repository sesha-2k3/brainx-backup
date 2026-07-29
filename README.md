# BrainX

Web-based personal relationship manager with AI-powered contact extraction.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- Docker (for PostgreSQL)
- Tesseract OCR: `brew install tesseract` (macOS) / `apt install tesseract-ocr` (Debian)

### 2. Setup

```bash
cd brainx

# Python dependencies. pyproject.toml is the source of truth;
# requirements.txt just points at it, so either command works.
uv sync
# or: python -m venv .venv && source .venv/bin/activate && pip install -e .

# Environment config
cp .env.example .env
# Edit .env and set GROQ_API_KEY and JWT_SECRET_KEY

# Frontend dependencies
cd frontend && npm install && cd ..
```

### 3. Database

```bash
# docker-compose.yml is at the repository root
docker compose up -d

# Apply migrations
alembic upgrade head
```

The Postgres image is `pgvector/pgvector:pg15` — plain Postgres 15 with the
`vector` extension available for the planned semantic search work. The extension
still has to be enabled per database, which the first embeddings migration does.

### 4. Run (development)

```bash
# Terminal 1 — backend API
uvicorn src.main:app --reload --port 8000

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open **http://localhost:5173/brainx/**

Vite serves on port 5173 and proxies `/brainx/api/*` through to the backend on
8000, so only the frontend URL needs to be open during development.

### 5. Run (production-style)

```bash
cd frontend && npm run build && cd ..
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/brainx/** (`/` redirects there).

The frontend is built with Vite `base: '/brainx/'`, so FastAPI serves it under
that prefix and mounts its bundles at `/brainx/assets`. Changing one without the
other breaks asset loading.

## Authentication

All `/api/*` endpoints except `/api/auth/*` and `/api/health` require a bearer
token.

```
POST /api/auth/register   → { access_token }   # logs you in immediately
POST /api/auth/login      → { access_token }   # accepts remember_me: bool
GET  /api/auth/me         → current user       # validates a stored token
```

Send the token as `Authorization: Bearer <token>`. Default lifetime is 24 hours,
or 30 days when `remember_me` is true (`REMEMBER_ME_EXPIRE_MINUTES`).

**Tenancy is per user.** Each authenticated user's UUID *is* their `tenant_id`,
injected by the `get_db_for_user` dependency. `TenantSession` then filters every
ORM `SELECT` and stamps every insert automatically, so query code never mentions
`tenant_id`.

> Two caveats worth knowing before writing queries: the auto-filter applies to
> **SELECT statements only** — a bare ORM `update()` or `delete()` is *not*
> scoped, so select the rows first and mutate the loaded objects. And raw SQL
> bypasses it entirely.

## Features

- **Text input** — paste meeting notes, extract contacts automatically
- **Voice upload** — upload voice memos, transcribed via Groq Whisper
- **Business cards** — upload photos, OCR extracts contact info
- **Smart extraction** — deterministic regex pass for email/phone/website, LLM
  for the open-ended fields (name, company, role, context, tasks)
- **Deduplication** — detects existing contacts by email, phone, or name+company
- **Follow-ups** — tasks linked to contacts, with relative dates ("tomorrow")
- **Natural search** — "Who is Eddie?", "Investors I met last month"

## Project layout

```
src/
  main.py             FastAPI app, static serving under /brainx
  config.py           Settings (pydantic-settings)
  api/web.py          Application endpoints
  auth/               Register, login, JWT, current-user dependency
  db/
    __init__.py       get_db_for_user — the tenant-scoped session dependency
    database.py       Engine, TenantSession, auto-filter events
    models.py         SQLAlchemy models
    queries/          Query functions (no tenant_id — it's automatic)
  schemas/            Pydantic request/response models
    fields.py         Shared validated field types
  services/           Extraction, OCR, transcription, dedup, confirmation
  utils/              Pure helpers (dates, text, phone, category)
frontend/src/
  context/            authContext.js + AuthProvider.jsx (split for Fast Refresh)
  api/                client.js, authClient.js
  pages/, components/
alembic/versions/     Migrations
```

## Validation conventions

Two deliberately different policies, worth knowing before adding a field:

- **Explicit input is validated.** A category or date typed by a human or sent
  by an API client is checked and rejected with a 422 if invalid, because
  silently discarding it means the caller never learns it didn't take effect.
- **Inferred input is clamped.** The same values arriving from LLM extraction
  degrade gracefully — an unrecognized category becomes `null`, an
  uninterpretable due date becomes "no due date" — because a model's bad guess
  must not reject the user's entire capture.

## Development

```bash
ruff check . && ruff format .    # lint + format
pytest                          # tests
alembic revision --autogenerate -m "description"
alembic upgrade head
```
