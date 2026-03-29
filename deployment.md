# BrainX deployment notes

This document describes how BrainX was wired for **HTTPS reverse proxy** access at `https://dev.internal.kronosx.ai/brainx/`, with the **API** on **port 8002** and **PostgreSQL** as the database.

## Public URL

- **App (dev, Vite):** `https://dev.internal.kronosx.ai/brainx/`
- **API (via same host):** `https://dev.internal.kronosx.ai/brainx/api/...` (Nginx strips the `/brainx` prefix and forwards `/api/...` to the backend)

## Environment (`.env`)

- **`DATABASE_URL`** must use the **asyncpg** driver for this app, for example:
  - `postgresql+asyncpg://USER:PASSWORD@HOST:5432/personal_crm`
- **URL-encode** reserved characters in the password in the URL (e.g. `#` → `%23`, `@` → `%40`). Example pattern: if the password is `foo#bar`, use `foo%23bar` in `DATABASE_URL`.
- Other variables (GROQ keys, `APP_ENV`, `TENANT_ID`, etc.) stay as documented in the project.

## PostgreSQL

1. Ensure the database exists (e.g. `personal_crm`).
2. Enable the extension used by migrations (can be done once manually or via the first migration):
   - `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
3. Run migrations from the repo root (with venv activated and `.env` loaded):
   - `alembic upgrade head`

**Alembic:** `alembic/env.py` imports only models that exist in `src/db/models.py` (`Contact`, `Interaction`, `Proposal`, `Task`). If you add models, update the import list there so migrations load correctly.

## Backend

Run the FastAPI app on the port Nginx expects (here **8002**):

```bash
cd /path/to/BrainX
source .venv/bin/activate   # or your venv
uvicorn src.main:app --reload --host 0.0.0.0 --port 8002
```

In **development**, the app may run `init_db()` on startup; production should rely on Alembic.

## Frontend (Vite dev server)

The frontend is served under the path **`/brainx/`**, so the following were set in the repo:

| Area | Change |
|------|--------|
| `frontend/vite.config.js` | `base: '/brainx/'` |
| `frontend/vite.config.js` | `server.allowedHosts: ['dev.internal.kronosx.ai']` so Vite accepts the proxied `Host` header |
| `frontend/vite.config.js` | `server.proxy`: proxy `/brainx/api` → `http://localhost:8002`, rewrite path by removing the `/brainx` prefix so the backend still sees `/api/...` |
| `frontend/src/main.jsx` | `<BrowserRouter basename="/brainx">` |
| `frontend/src/api/client.js` | `API_BASE = '/brainx/api'` |
| `frontend/src/pages/AddContactPage.jsx` | POST URL uses `/brainx/api/contacts` (same base as the client) |

Run the dev server (default port **5173**):

```bash
cd frontend
npm install
npm run dev
```

**Local dev without Nginx:** open `http://localhost:5173/brainx/` (path required because of `base`).

## Nginx (`/etc/nginx/sites-available/myapp`)

Add these blocks **inside** the `server { ... }` for `dev.internal.kronosx.ai` (HTTPS), **before** the catch-all `location /` so `/brainx` is matched first.

**API** — forward `/brainx/api/...` to the backend as `/api/...`:

```nginx
    # BrainX API backend on localhost:8002
    location /brainx/api/ {
        rewrite ^/brainx/(.*) /$1 break;

        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Prefix /brainx;

        proxy_set_header Accept-Encoding "";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        proxy_redirect http://localhost:8002/ /brainx/;
        proxy_redirect / /brainx/;

        sub_filter 'url: \'/openapi.json\'' 'url: \'/brainx/api/openapi.json\'';
        sub_filter '"/openapi.json"' '"/brainx/api/openapi.json"';
        sub_filter "'/openapi.json'" "'/brainx/api/openapi.json'";
        sub_filter '"openapi":"3.1.0","info"' '"openapi":"3.1.0","servers":[{"url":"/brainx"}],"info"';
        sub_filter_once off;
        sub_filter_types application/javascript application/json;
    }
```

**Frontend (Vite)** — proxy to the dev server with WebSocket support (HMR):

```nginx
    # BrainX frontend on localhost:5173
    location /brainx/ {
        proxy_pass http://localhost:5173/brainx/;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Handle /brainx without trailing slash
    location = /brainx {
        return 301 /brainx/;
    }
```

Then test and reload:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

**Backup:** before editing, copy the site file (e.g. `sudo cp /etc/nginx/sites-available/myapp /etc/nginx/sites-available/myapp.bak`).

## Production alternative (no Vite on 5173)

For production you would typically:

1. `cd frontend && npm run build`
2. Serve `frontend/dist` with `root`/`alias` under `/brainx/` or proxy to a static file server, and keep the same `/brainx/api/` block pointing at the backend.

Adjust `allowedHosts` and proxy targets only if hostnames or ports change.

## Quick verification

1. Backend liveness: `curl -sS http://127.0.0.1:8002/health` → `{"status":"ok"}`.
2. Backend readiness (DB): `curl -sS http://127.0.0.1:8002/ready` → includes `"database":"connected"`.
3. Frontend: Vite listening on `5173`.
4. Through Nginx: open `https://dev.internal.kronosx.ai/brainx/` — no “Blocked request” / `allowedHosts` error.
5. API from browser: network tab shows requests to `/brainx/api/...` (e.g. contacts list) with successful responses.

**Note:** Liveness/readiness routes are mounted at `/health` and `/ready` on the app, not under `/api`. Only paths under `/api/...` are reached via `/brainx/api/...` through Nginx.
