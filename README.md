# Bestreads

A multi-user book tracker with a React frontend, a FastAPI REST API, and an MCP
server that lets Claude manage your library conversationally. Postgres-backed,
fully containerized.

## Quickstart

```bash
cp .env.example .env
# (optional) set ANTHROPIC_API_KEY in .env to enable recommendations
docker compose up --build
```

Then open:

- **App** → http://localhost:3000
- **MCP server (SSE)** → http://localhost:8080
- **FastAPI docs (dev only)** → http://localhost:8000/docs (port not exposed in prod compose)

## Architecture

```
┌───────────────┐   /api   ┌────────────┐
│  frontend     │────────▶ │  fastapi   │──▶ postgres
│  (nginx+React)│          │            │
└───────────────┘          │            │──▶ api.anthropic.com (recs)
        ▲                  │            │──▶ openlibrary.org (isbn lookup)
        │ /covers          └─────▲──────┘
        │                        │
        └─── volume ──────────── │
                                 │
                         ┌───────┴──────┐
                         │  mcp-server  │
                         │  (bt_ key)   │
                         └──────────────┘
```

- `frontend` serves the built React SPA via nginx, reverse-proxying `/api/*` to
  `fastapi:8000` and serving `/covers/*` directly from the shared Docker volume.
- `fastapi` owns all business logic and data. Auth: JWT for the web app, a
  long-lived `bt_...` API key for MCP. The same Bearer-token dependency accepts
  either.
- `mcp-server` is a thin FastMCP translator. Every tool call becomes an
  authenticated HTTP request against FastAPI.

## Environment

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | asyncpg URL for Postgres |
| `JWT_SECRET` | HS256 secret for access/refresh tokens |
| `ANTHROPIC_API_KEY` | optional — recommendations degrade gracefully without it |
| `COVERS_DIR` | directory for cover images (shared volume mount) |
| `API_BASE_URL` | mcp-server → fastapi base URL (internal network) |
| `BOOK_TRACKER_API_KEY` | mcp-server auth; generate in the app's Settings page |

## Using the MCP server

1. Start the stack: `docker compose up --build`
2. Register an account in the web app
3. Go to **Settings → MCP API key → Generate key**
4. Save the full key (shown only once)
5. Point your MCP client at `http://localhost:8080/sse` with that key as a
   bearer token, or set `BOOK_TRACKER_API_KEY` in `.env` and restart
   `mcp-server` to hardcode it.

Tools exposed: `search_books`, `add_book`, `update_status`, `rate_book`,
`get_stats`, `recommend_books`.

## Smoke test

After `docker compose up -d --build`:

```bash
pip install httpx pytest pytest-asyncio
BASE_URL=http://localhost:8000 pytest backend/tests/test_smoke.py -v
```

The test walks the full happy path: register → login → add 5 books → start/
finish/reset transitions → rate and annotate → list by status and tag →
full-text search → stats → recommendations (tolerates `ANTHROPIC_API_KEY`
being unset) → API key regeneration → re-auth with the new key.

## Layout

```
backend/       FastAPI app, SQLAlchemy models, Alembic migrations
mcp-server/    FastMCP server (stdio + SSE transports)
frontend/      Vite + React + TS + Tailwind, served by nginx
docker-compose.yml
docs/          Implementation plan
```

## Local dev (without Docker)

```bash
# Backend
docker compose up -d postgres
cd backend && pip install -e . && alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```
