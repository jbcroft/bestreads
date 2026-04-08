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

- **App** → http://localhost:3001
- **MCP server (SSE)** → http://localhost:8080
- **FastAPI docs** → http://localhost:8001/docs

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

The `mcp-server` container runs an SSE transport on port 8080, but the most
reliable way to use Bestreads from Claude Desktop is to run the MCP server
**locally over stdio** and let Claude Desktop spawn it. That avoids any
fiddliness around SSE auth headers and keeps your API key out of `.env`.

Tools exposed: `search_books`, `add_book`, `update_status`, `rate_book`,
`get_stats`, `recommend_books`.

### 1. Install the MCP server locally (one-time)

Requires Python 3.12 or newer. Check with `python3 --version`; if it's
older than 3.12, install a newer one with `brew install python@3.13` (or
similar) and substitute it below.

```bash
cd mcp-server
python3 -m venv .venv
.venv/bin/pip install -e .
```

Confirm the install:

```bash
.venv/bin/python -c "import mcp, httpx, pydantic; print('ok')"
# → ok
```

This creates `mcp-server/.venv/` with `mcp`, `httpx`, and `pydantic`
installed. The venv's Python is what Claude Desktop will launch.

### 2. Generate an API key in the web app

1. Make sure the stack is running: `docker compose up -d`
2. Open http://localhost:3001 and sign in (or register)
3. Go to **Settings → MCP API key → Generate key**
4. **Copy the full `bt_...` key immediately** — it's shown only once

### 3. Edit Claude Desktop's config

On macOS the config lives at:

```
~/Library/Application Support/Claude/claude_desktop_config.json
```

If the file doesn't exist yet, create it. If it already has an `mcpServers`
object, add the `bestreads` entry alongside your existing servers.

```json
{
  "mcpServers": {
    "bestreads": {
      "command": "/ABSOLUTE/PATH/TO/bestreads/mcp-server/.venv/bin/python",
      "args": [
        "/ABSOLUTE/PATH/TO/bestreads/mcp-server/server.py"
      ],
      "env": {
        "API_BASE_URL": "http://localhost:8001/api/v1",
        "BOOK_TRACKER_API_KEY": "bt_PASTE_YOUR_KEY_HERE",
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/bestreads` with the real path on your machine
(e.g. `/Users/yourname/code/bestreads`) and paste the key from step 2.

### 4. Restart Claude Desktop

Fully quit with `⌘Q` (don't just close the window) and reopen — Claude
Desktop only re-reads the config on launch. In a new chat the plug/tools
icon should show a `bestreads` server with all 6 tools listed.

### 5. Try it out

> *"What books are in my Bestreads library?"*

Claude will call `search_books()` and list what you have.

> *"Add 'Dune' by Frank Herbert to my want-to-read list."*

Refresh http://localhost:3001 and the book appears on the dashboard.

### Troubleshooting

- **Server doesn't appear in Claude Desktop.** The `command` path is wrong
  or the venv doesn't exist. Verify:
  `ls /ABSOLUTE/PATH/TO/bestreads/mcp-server/.venv/bin/python`
- **"Invalid credentials" from tool calls.** API key wasn't copied correctly
  — it must start with `bt_`. Regenerate in **Settings** and update the
  config.
- **"Connection refused" from tool calls.** The FastAPI backend isn't
  running. Check with `docker compose ps` — `fastapi` should show
  `running` on `0.0.0.0:8001->8000/tcp`.
- **Config changes aren't taking effect.** Claude Desktop caches the config
  across sessions — force-quit with `⌘Q` and relaunch.

### Alternative: SSE transport from the Docker stack

If you'd rather use the containerized SSE server on `http://localhost:8080/sse`,
set `BOOK_TRACKER_API_KEY` in `.env` before `docker compose up` so the
`mcp-server` container picks it up. Some MCP clients support SSE URLs
directly — consult your client's docs. For Claude Desktop, stdio (above) is
the recommended path.

## Smoke test

After `docker compose up -d --build`:

```bash
pip install httpx pytest pytest-asyncio
BASE_URL=http://localhost:8001 pytest backend/tests/test_smoke.py -v
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
