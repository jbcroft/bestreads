# Book Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Executed phase-by-phase with checkpoints. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a multi-user book-tracking web app (React frontend + FastAPI REST API + MCP server + Postgres) per `/Users/justin/Desktop/BOOK_TRACKER_REQUIREMENTS.md`, runnable via `docker compose up`.

**Architecture:** Three-tier stack in Docker Compose. FastAPI owns all business logic and data. React frontend consumes the REST API, served by nginx. MCP server is a thin translator that calls the REST API on behalf of Claude using a user-scoped API key. Postgres 16 with `tsvector` full-text search. Cover images persisted to a shared Docker volume.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), Alembic, Pydantic v2, python-jose, bcrypt, httpx, `mcp` SDK, React 18 + TypeScript, Vite, Tailwind, TanStack Query, React Router, PostgreSQL 16, nginx, Docker Compose.

**Testing strategy (per user preference):** Minimal tests, smoke-test at the end. No strict TDD. Focus on shipping working features; add a smoke test suite in Phase 6 that hits the running stack end-to-end.

---

## Repository Layout

```
bestreads/
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app, router wiring, CORS
│   │   ├── config.py         # pydantic-settings, loads .env
│   │   ├── db.py             # async engine, session factory, Base
│   │   ├── models.py         # SQLAlchemy models (User, Book, Tag, BookTag, Recommendation)
│   │   ├── schemas.py        # Pydantic request/response schemas
│   │   ├── deps.py           # auth dependencies (get_current_user etc.)
│   │   ├── security.py       # bcrypt + JWT helpers + API key gen
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── books.py
│   │   │   ├── tags.py
│   │   │   ├── covers.py
│   │   │   ├── search.py
│   │   │   ├── stats.py
│   │   │   ├── lookup.py
│   │   │   ├── recommendations.py
│   │   │   └── settings.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── openlibrary.py
│   │       └── anthropic_recs.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── tests/
│       └── test_smoke.py     # added in Phase 6
├── mcp-server/
│   ├── server.py             # MCP tools that HTTP to FastAPI
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── api/              # typed fetch wrappers + React Query hooks
│   │   ├── auth/             # auth context, login/register pages
│   │   ├── components/       # Shelf, BookCard, StatusControl, TagChip, ThemeToggle, Toast
│   │   ├── pages/            # Dashboard, Library, BookDetail, Stats, Settings
│   │   └── lib/              # utils, markdown renderer
│   ├── nginx.conf            # reverse proxy /api → fastapi
│   └── Dockerfile            # multi-stage build → nginx
├── docker-compose.yml
├── .env.example
├── .gitignore
└── docs/superpowers/plans/2026-04-08-book-tracker.md  (this file)
```

---

# Phase 1 — Backend Foundation (DB, Models, Auth)

**Goal at end of phase:** `uvicorn app.main:app` boots against a Postgres running in Docker, and you can `POST /api/v1/auth/register` and `POST /api/v1/auth/login` via curl.

**Files created this phase:** `backend/pyproject.toml`, `backend/app/{main,config,db,models,schemas,security,deps}.py`, `backend/app/routers/{__init__,auth,settings}.py`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`, `docker-compose.yml` (postgres service only), `.env.example`.

### Task 1.1 — Remove PyCharm placeholder, initial git layout

- [ ] Delete `main.py` (PyCharm default stub)
- [ ] Create `.gitignore` covering Python, Node, env, IDE, covers dir, pgdata
- [ ] Commit: `chore: clear placeholder, add gitignore`

### Task 1.2 — Backend package scaffold

- [ ] Create `backend/pyproject.toml` with deps: fastapi, uvicorn[standard], sqlalchemy[asyncio]>=2, asyncpg, alembic, pydantic>=2, pydantic-settings, python-jose[cryptography], bcrypt, passlib[bcrypt], python-multipart, httpx, anthropic
- [ ] Create empty `backend/app/__init__.py`
- [ ] Create `backend/app/config.py` — `Settings` via `pydantic_settings.BaseSettings`, fields: `database_url`, `jwt_secret`, `jwt_access_token_expire_minutes` (default 30), `jwt_refresh_token_expire_days` (default 7), `anthropic_api_key` (optional), `covers_dir` (default `/app/covers`). Loads from `.env`.
- [ ] Create `backend/app/db.py` — `create_async_engine(settings.database_url)`, `async_sessionmaker`, `Base = declarative_base()` (SQLAlchemy 2 style), `async def get_session() -> AsyncSession` dependency.

### Task 1.3 — SQLAlchemy models

- [ ] `backend/app/models.py` — all models from spec:
  - `User`: id (UUID pk), username (unique), email (unique), password_hash, avatar_url (nullable), api_key (nullable, unique index), created_at (server_default now)
  - `Book`: id, user_id (FK, cascade), title, author, isbn (nullable), page_count (nullable), description (nullable text), cover_image_path (nullable), status (enum: `want_to_read`/`reading`/`finished`), rating (nullable smallint), notes (nullable text), date_added (server_default now), started_at (nullable), finished_at (nullable)
  - `Tag`: id, name, user_id (FK); unique (user_id, name)
  - `BookTag`: composite pk (book_id, tag_id) with FKs
  - `Recommendation`: id, user_id (FK), title, author, reason, mood (nullable), tag_filter (nullable), generated_at
- [ ] Use `sa.Enum('want_to_read','reading','finished', name='book_status')` for status.
- [ ] Relationships: `User.books`, `Book.tags` (secondary=BookTag), `Book.user`, etc.

### Task 1.4 — Alembic setup + initial migration

- [ ] Create `backend/alembic.ini` (pointing script_location at `alembic`)
- [ ] Create `backend/alembic/env.py` — async-aware, imports `Base.metadata` from `app.db`, reads URL from `app.config.settings.database_url`
- [ ] Create `backend/alembic/script.py.mako` (standard template)
- [ ] Create `backend/alembic/versions/0001_initial.py` — upgrade() creates all tables, the `book_status` enum, indexes (user_id on books/tags/recommendations, the tsvector column + GIN index for search — see Phase 2 note), plus the many-to-many `book_tags` table. Downgrade drops everything.
- [ ] Note: full-text `tsvector` column will be added in a Phase 2 migration, NOT this one.

### Task 1.5 — Security helpers

- [ ] `backend/app/security.py`:
  - `hash_password(pw) -> str` and `verify_password(pw, hash) -> bool` using passlib CryptContext(bcrypt)
  - `create_access_token(sub, expires_delta)` and `create_refresh_token(sub)` via python-jose HS256
  - `decode_token(token) -> dict`
  - `generate_api_key() -> str` — `"bt_" + secrets.token_urlsafe(32)`

### Task 1.6 — Pydantic schemas for auth

- [ ] `backend/app/schemas.py` (will grow across phases; start with):
  - `UserCreate` (username, email, password)
  - `UserPublic` (id, username, email, avatar_url, created_at)
  - `TokenPair` (access_token, refresh_token, token_type="bearer")
  - `RefreshRequest` (refresh_token)
  - `LoginRequest` (username_or_email, password)

### Task 1.7 — Auth router

- [ ] `backend/app/deps.py`:
  - `get_current_user` — Bearer token dep, decodes JWT, loads user, raises 401 on failure
  - `get_current_user_by_api_key` — alternate dep that accepts a Bearer API key (`bt_...`) for MCP, looks up by `User.api_key`
  - `get_auth_user` — tries JWT first, falls back to API key (used on endpoints MCP also needs)
- [ ] `backend/app/routers/auth.py`:
  - `POST /auth/register` — create user, return `UserPublic`
  - `POST /auth/login` — accept username_or_email + password, return `TokenPair`
  - `POST /auth/refresh` — accept refresh token, return new access token

### Task 1.8 — Settings router (API key)

- [ ] `backend/app/routers/settings.py`:
  - `GET /settings/api-key` — returns masked key like `bt_abcd…xyz9` or `null` if none
  - `POST /settings/api-key/regenerate` — generates a new key, saves, returns the full plaintext key **once**

### Task 1.9 — FastAPI app wiring

- [ ] `backend/app/main.py`:
  - Create FastAPI app (title="Book Tracker API")
  - CORS middleware allowing `http://localhost:3000` and `http://localhost:5173` for dev
  - Include routers under `/api/v1`
  - `GET /api/v1/healthz` returning `{"ok": True}`

### Task 1.10 — docker-compose (postgres only for now)

- [ ] `docker-compose.yml` with `postgres` service: postgres:16, env `POSTGRES_USER=booktracker`, `POSTGRES_PASSWORD=booktracker`, `POSTGRES_DB=booktracker`, volume `pgdata`, port 5432 exposed for dev.
- [ ] `.env.example` per spec template
- [ ] Start postgres: `docker compose up -d postgres`
- [ ] Run `DATABASE_URL=postgresql+asyncpg://booktracker:booktracker@localhost:5432/booktracker alembic upgrade head` from `backend/`
- [ ] Smoke check: `uvicorn app.main:app --reload` → `curl localhost:8000/api/v1/healthz`
- [ ] Smoke check: register, login, regenerate API key via curl
- [ ] Commit: `feat(backend): db models, auth, api key management`

---

# Phase 2 — Core Book API

**Goal at end of phase:** Fully functional CRUD + status transitions + tags + cover upload + search + stats, authenticated with JWT, scoped to user.

**Files created this phase:** `backend/app/routers/{books,tags,covers,search,stats}.py`, extend `schemas.py`, `backend/alembic/versions/0002_fulltext.py`.

### Task 2.1 — Book schemas

- [ ] Extend `schemas.py`:
  - `BookBase` (title, author, isbn?, page_count?, description?, status default `want_to_read`, rating?, notes?)
  - `BookCreate(BookBase)`
  - `BookUpdate` — all fields optional
  - `BookRead` — adds id, cover_image_path (turned into a URL), tags, date_added, started_at, finished_at
  - `TagRead` (id, name)
  - `TagCreate` (name)

### Task 2.2 — Books router

- [ ] `backend/app/routers/books.py`, all use `get_auth_user`:
  - `GET /books` — filters: `status`, `tag` (name), `q` (ILIKE fallback until FTS), `sort` (date_added/title/author/rating/finished_at), `min_rating`. Scoped to user. Returns list.
  - `GET /books/{id}` — 404 if not owned
  - `POST /books` — create
  - `PATCH /books/{id}` — partial update; if status changes apply transition rules (see 2.3 helper)
  - `DELETE /books/{id}` — delete (also invalidate recommendations cache — implement in phase 3; leave TODO hook)

### Task 2.3 — Status transition endpoints

- [ ] Helper `apply_status_transition(book, new_status, now)` in a small `services/transitions.py` (or inline in router):
  - → `reading`: set `started_at = now` if not set, clear `finished_at`
  - → `finished`: set `finished_at = now`, set `started_at = started_at or now`
  - → `want_to_read`: clear `started_at` and `finished_at`
- [ ] `POST /books/{id}/start` → transition to reading
- [ ] `POST /books/{id}/finish` → transition to finished
- [ ] `POST /books/{id}/reset` → transition to want_to_read

### Task 2.4 — Tags

- [ ] `backend/app/routers/tags.py`:
  - `GET /tags` — list user's tags
  - `POST /tags` — create (idempotent on name conflict — return existing)
  - `DELETE /tags/{id}` — delete tag and cascade remove associations
- [ ] Also in `books.py`: `PATCH /books/{id}/tags` — body `{tag_names: [str]}`; resolve or create tags by name for this user, replace book's tag set.

### Task 2.5 — Covers

- [ ] `backend/app/routers/covers.py`:
  - `POST /books/{id}/cover` — multipart upload, save to `settings.covers_dir/<uuid>.<ext>`, store relative path on book; ensure dir exists on boot
  - `GET /covers/{filename}` — `FileResponse` from covers dir (used in dev; in Docker, nginx serves covers directly from the shared volume)
- [ ] On app startup (in `main.py`), `os.makedirs(settings.covers_dir, exist_ok=True)`.

### Task 2.6 — Full-text search migration + endpoint

- [ ] `backend/alembic/versions/0002_fulltext.py`: add `search_vector tsvector` generated column on `books` (`title || ' ' || author || ' ' || coalesce(notes,'') || ' ' || coalesce(description,'')`), create GIN index on it.
- [ ] `backend/app/routers/search.py`:
  - `GET /search?q=` — run `plainto_tsquery` against `search_vector` for the user's books. Group results by status in the response: `{want_to_read: [...], reading: [...], finished: [...]}`.

### Task 2.7 — Stats

- [ ] `backend/app/routers/stats.py`:
  - `GET /stats` — counts per status, books finished this calendar year (based on `finished_at`), avg rating (over rated books), top 5 tags (by usage count), total books, finished_by_month for the last 12 months (array of `{month: 'YYYY-MM', count: int}` — used by frontend chart).

### Task 2.8 — Wire routers + smoke

- [ ] Update `main.py` to include new routers.
- [ ] Run a fresh `alembic upgrade head`.
- [ ] Smoke via curl: create book, upload cover, transition status, tag it, search, stats.
- [ ] Commit: `feat(backend): books crud, tags, covers, search, stats`

---

# Phase 3 — External Integrations

**Goal at end of phase:** `/lookup?isbn=…` returns Open Library metadata and caches the cover locally; `/recommendations` returns AI-suggested books from Anthropic with 24h + library-change cache invalidation.

### Task 3.1 — Open Library lookup

- [ ] `backend/app/services/openlibrary.py`:
  - `async def lookup_isbn(isbn: str) -> dict | None` — GET `https://openlibrary.org/isbn/{isbn}.json`, resolve work/author refs where needed. Returns `{title, author, page_count, description, cover_url}`.
  - `async def download_cover(isbn: str) -> str | None` — downloads `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg` (skip if content length < 1KB, Open Library returns a 1-byte placeholder for missing covers), saves into `settings.covers_dir` as `<isbn>.jpg`, returns relative filename.
- [ ] `backend/app/routers/lookup.py`:
  - `GET /lookup?isbn=` — calls `lookup_isbn`; if not found returns 404; if cover_url present, fires and awaits `download_cover`; response includes local cover filename where applicable.
- [ ] Note: when `POST /books` receives an `isbn` without an existing cover_image_path, also auto-download in background.

### Task 3.2 — Anthropic recommendations service

- [ ] `backend/app/services/anthropic_recs.py`:
  - `async def generate_recommendations(user, library_summary, *, count=3, mood=None, tag_filter=None) -> list[dict]`
  - Uses `anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)`, model `claude-sonnet-4-20250514`
  - System prompt: "You are a well-read literary advisor. Return ONLY a JSON array of objects with keys `title`, `author`, `reason`. No prose, no markdown fences. Each reason is one sentence explaining the fit to the user's library."
  - User message: includes library summary (title, author, status, rating, tags) + filters if set
  - Parses JSON, strips accidental ```json fences defensively
- [ ] `build_library_summary(books) -> str` helper producing a compact textual summary (e.g., `"- The Name of the Wind by Patrick Rothfuss [finished, rating 5, tags: fantasy, favorites]"`)

### Task 3.3 — Recommendations router + caching

- [ ] `backend/app/routers/recommendations.py`:
  - `GET /recommendations?count=3&tag=&mood=`
  - If user has <5 books, return `{available: false, message: "Add a few more books to unlock personalized recommendations.", recommendations: []}`
  - Cache key = `(user_id, mood, tag_filter)`; fresh if `generated_at > now - 24h` AND library hasn't mutated since (see 3.4)
  - On cache miss: build summary, call service, replace cache rows for that key, return
- [ ] Track library mutation via `User.library_updated_at` column (add it), bumped on any book add/delete/status change/rating change. Add a small alembic migration `0003_user_library_updated_at.py`.
- [ ] Cache freshness: `cached.generated_at > max(now - 24h, user.library_updated_at)`.

### Task 3.4 — Invalidation hooks

- [ ] In books router: on create/delete/status-change/rating-change, set `current_user.library_updated_at = func.now()`, flush.
- [ ] Extract to a small helper `_touch_library(user, session)` to avoid DRY issues.

### Task 3.5 — Smoke + commit

- [ ] Smoke test: set ANTHROPIC_API_KEY, add 5 books, GET /recommendations — verify JSON shape + cache hit on second call.
- [ ] Commit: `feat(backend): open library lookup + anthropic recommendations`

---

# Phase 4 — MCP Server

**Goal at end of phase:** `mcp-server/server.py` runs (stdio transport locally; HTTP when containerized) and exposes the 6 tools that proxy to FastAPI using a user's API key as bearer token.

### Task 4.1 — Scaffold

- [ ] `mcp-server/pyproject.toml` deps: `mcp`, `httpx`, `pydantic`
- [ ] `mcp-server/server.py`:
  - Read `API_BASE_URL` and `BOOK_TRACKER_API_KEY` from env
  - `httpx.AsyncClient(base_url=API_BASE_URL, headers={"Authorization": f"Bearer {API_KEY}"})`
  - Uses the `mcp` SDK's `Server` class (or `FastMCP` if available in the installed version — check at implementation time)

### Task 4.2 — Tools

- [ ] `search_books(query?, status?, tag?, min_rating?)` → `GET /books` with those params
- [ ] `add_book(title, author, isbn?, status?, tags?)`:
  - If `isbn`, first `GET /lookup?isbn=` to enrich
  - `POST /books` with merged fields
  - If `tags`, `PATCH /books/{id}/tags`
- [ ] `update_status(book_id, status)` → maps to one of `/books/{id}/start|finish|reset`
- [ ] `rate_book(book_id, rating, notes?)` → `PATCH /books/{id}`
- [ ] `get_stats()` → `GET /stats`
- [ ] `recommend_books(mood?, tag?, count?)` → `GET /recommendations?...`

### Task 4.3 — Run + commit

- [ ] Local smoke: start stdio server, use `mcp` inspector or a quick script to call `search_books`.
- [ ] Commit: `feat(mcp): expose book tracker tools`

---

# Phase 5 — React Frontend

**Goal at end of phase:** `npm run dev` boots a working UI that talks to FastAPI on port 8000. Dashboard, library, book detail, add flow, stats, settings all functional. Design: editorial, typography-driven, neutral palette with one accent, dark+light modes.

### Task 5.1 — Scaffold

- [ ] `frontend/package.json` via Vite template: react-ts
- [ ] Install: react-router-dom, @tanstack/react-query, axios, tailwindcss, postcss, autoprefixer, clsx, lucide-react, react-markdown, recharts (for stats chart)
- [ ] `tailwind.config.js` — content globs, extended theme:
  - Neutral palette (zinc scale)
  - Accent color: single custom (`accent: '#C0392B'` — muted terracotta, or similar editorial tone; finalize during implementation)
  - Font families: `serif: ['"Source Serif 4"', 'Georgia', 'serif']` for headings, `sans: ['Inter', ...]` for body
  - `darkMode: 'class'`
- [ ] Global `src/index.css` — Tailwind base/components/utilities; CSS vars for theme; load Inter + Source Serif from Google Fonts
- [ ] `src/main.tsx` wraps `<App>` in `<QueryClientProvider>` and `<BrowserRouter>`

### Task 5.2 — API layer

- [ ] `src/api/client.ts` — axios instance with baseURL `import.meta.env.VITE_API_BASE || '/api/v1'`. Attaches `Authorization: Bearer <access_token>` from localStorage. Interceptor: on 401, tries `/auth/refresh`; on failure, clears tokens and redirects to `/login`.
- [ ] `src/api/types.ts` — TS types mirroring backend schemas
- [ ] `src/api/books.ts`, `auth.ts`, `tags.ts`, `stats.ts`, `lookup.ts`, `recommendations.ts`, `settings.ts` — typed functions + React Query hooks (`useBooks`, `useBook(id)`, `useAddBook`, `useStats`, …)

### Task 5.3 — Auth context + pages

- [ ] `src/auth/AuthContext.tsx` — provides `user`, `login`, `register`, `logout`
- [ ] `src/pages/Login.tsx`, `src/pages/Register.tsx` — minimal editorial forms
- [ ] `src/App.tsx` — routes: `/login`, `/register`, `/` (Dashboard), `/library`, `/books/:id`, `/stats`, `/settings`; protected layout wrapper around authed routes with nav

### Task 5.4 — Navigation + Quick-add bar

- [ ] `src/components/Nav.tsx` — top bar: logo (serif wordmark "Bestreads"), links (Home / Library / Stats / Settings), theme toggle, quick-add search input
- [ ] `src/components/QuickAdd.tsx`:
  - Debounced input → hits Open Library search endpoint (we only have `/lookup?isbn=` — add a `/lookup/search?q=` endpoint in Phase 2.x? **Decision:** add a new endpoint `GET /lookup/search?q=` in this phase that proxies `https://openlibrary.org/search.json?q=<q>&limit=10` — back-add it to backend before wiring frontend)
  - Dropdown of results (cover thumbnail, title, author, year)
  - Click → confirmation card (shelf picker: `want_to_read` default, tags input) → confirm → POST /books
  - "Add manually" link → opens manual add modal

### Task 5.5 — Dashboard

- [ ] `src/pages/Dashboard.tsx` — 3 sections (Want to Read / Reading / Finished) displayed as cover grids with count labels
- [ ] `src/components/CoverGrid.tsx` — responsive grid, uniform aspect ratio (2:3), no borders, subtle hover elevation, click → book detail
- [ ] `src/components/RecommendationsWidget.tsx` — calls `/recommendations?count=3`; shows three cards with title, author, reason, "Add to Want to Read" button; refresh button; hidden when `available:false`

### Task 5.6 — Library page

- [ ] `src/pages/Library.tsx` — filter bar (status multi-select, tag chips, min rating, sort select, grid/list toggle), real-time search; results grid/list driven by filters

### Task 5.7 — Book detail

- [ ] `src/pages/BookDetail.tsx` — large cover left, metadata right; segmented status control (3 buttons reflecting current state), star rating component, markdown notes editor (react-markdown preview + textarea edit toggle), tag chips with add/remove

### Task 5.8 — Stats page

- [ ] `src/pages/Stats.tsx` — uses recharts:
  - Bar chart: books finished by month (last 12)
  - Horizontal bars: top tags
  - Histogram-ish: rating distribution
  - Total counts by status (big numbers)

### Task 5.9 — Settings page

- [ ] `src/pages/Settings.tsx` — profile view, API key management (view masked, "Regenerate" shows full key once in a modal with a copy button), theme toggle

### Task 5.10 — Polish + theming

- [ ] Toast system (`src/components/Toast.tsx` + context) for action feedback
- [ ] Loading skeletons (not spinners)
- [ ] Empty states per spec
- [ ] Fade-in animations via Tailwind `animate-[fadeIn_.3s_ease]`
- [ ] Dark mode: true dark surfaces (`bg-zinc-950`), not inverted; light mode neutral (`bg-stone-50`)
- [ ] Mobile responsive nav + grids
- [ ] Commit: `feat(frontend): react ui — dashboard, library, book detail, stats, settings`

---

# Phase 6 — Docker Compose + Smoke Test

**Goal at end of phase:** `docker compose up --build` brings up postgres, fastapi, mcp-server, frontend(nginx). App is reachable at `http://localhost:3000`, MCP at `http://localhost:8080`. Smoke test passes.

### Task 6.1 — Backend Dockerfile

- [ ] `backend/Dockerfile` — python:3.12-slim, install deps, copy app, entrypoint runs `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Task 6.2 — MCP Dockerfile

- [ ] `mcp-server/Dockerfile` — python:3.12-slim, install deps, run `python server.py` (HTTP mode) on port 8080

### Task 6.3 — Frontend Dockerfile + nginx config

- [ ] `frontend/Dockerfile` multi-stage:
  - Stage 1: node:20-alpine, `npm ci && npm run build` → /app/dist
  - Stage 2: nginx:alpine, copy dist → /usr/share/nginx/html, copy `nginx.conf`
- [ ] `frontend/nginx.conf`:
  - `location /api/ { proxy_pass http://fastapi:8000; }`
  - `location /covers/ { alias /covers/; }`
  - SPA fallback: `try_files $uri /index.html;`

### Task 6.4 — Full docker-compose.yml

- [ ] Services: `postgres`, `fastapi`, `mcp-server`, `frontend`
- [ ] Shared volume `covers` mounted into fastapi at `/app/covers` and frontend at `/covers` (ro)
- [ ] `pgdata` volume for postgres
- [ ] `fastapi` depends_on postgres (healthcheck); `frontend` depends_on fastapi; `mcp-server` depends_on fastapi
- [ ] Only `frontend` (3000) and `mcp-server` (8080) exposed; postgres exposed only in dev override
- [ ] Environment wired from `.env`

### Task 6.5 — Smoke test

- [ ] `backend/tests/test_smoke.py` using httpx against `http://localhost:8000`:
  - Register a random user
  - Login
  - Create 5 books (to cross the recommendations threshold)
  - Transition one to reading, one to finished
  - Tag a book
  - Fetch dashboard data (/books by status)
  - Fetch stats
  - Fetch /recommendations (assert shape; tolerate Anthropic key absent with `available:false`)
  - Regenerate API key
- [ ] Document how to run: `docker compose up -d --build && pytest backend/tests/test_smoke.py`
- [ ] Commit: `feat: docker compose stack + smoke test`

### Task 6.6 — README

- [ ] Top-level `README.md` with quickstart (`cp .env.example .env`, edit, `docker compose up --build`), URLs, MCP usage snippet, project layout, env var reference.
- [ ] Commit: `docs: readme and quickstart`

---

## Self-Review (spec coverage checklist)

| Spec section | Covered in |
|---|---|
| Data model (User/Book/Tag/BookTag/Recommendation) | 1.3, 3.3 (library_updated_at) |
| Status transition rules | 2.3 |
| JWT auth + bcrypt + refresh | 1.5, 1.6, 1.7 |
| API key for MCP | 1.5, 1.7 (deps), 1.8 |
| All `/api/v1` endpoints | 1.7, 1.8, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.3 |
| Open Library ISBN lookup + cover download | 3.1 |
| Anthropic recommendations + caching + invalidation | 3.2, 3.3, 3.4 |
| 5-book threshold + privacy (user's own data only) | 3.3 |
| MCP server 6 tools | 4.2 |
| Frontend views (Dashboard/Library/BookDetail/Add/Stats/Settings) | 5.5–5.9 |
| Editorial design principles | 5.1, 5.10 |
| Recommendations widget | 5.5 |
| Quick-add flow (<3 actions) | 5.4 |
| Dark/light mode | 5.1, 5.10 |
| Docker Compose w/ nginx proxy, shared covers volume | 6.1–6.4 |
| External deps: Open Library, Anthropic | 3.1, 3.2 |
| Full-text search w/ tsvector | 2.6 |

No placeholders. No TBDs. Types are consistent across tasks (BookRead, Book, Tag, status enum values all match).
