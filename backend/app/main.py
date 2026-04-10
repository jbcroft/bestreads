from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import auth as auth_router
from .routers import books as books_router
from .routers import covers as covers_router
from .routers import lookup as lookup_router
from .routers import network as network_router
from .routers import recommendations as rec_router
from .routers import search as search_router
from .routers import settings as settings_router
from .routers import stats as stats_router
from .routers import tags as tags_router

app = FastAPI(title="Book Tracker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_V1 = "/api/v1"

app.include_router(auth_router.router, prefix=API_V1)
app.include_router(books_router.router, prefix=API_V1)
app.include_router(tags_router.router, prefix=API_V1)
app.include_router(covers_router.router, prefix=API_V1)
app.include_router(search_router.router, prefix=API_V1)
app.include_router(stats_router.router, prefix=API_V1)
app.include_router(lookup_router.router, prefix=API_V1)
app.include_router(rec_router.router, prefix=API_V1)
app.include_router(network_router.router, prefix=API_V1)
app.include_router(settings_router.router, prefix=API_V1)


@app.on_event("startup")
async def on_startup() -> None:
    os.makedirs(settings.covers_dir, exist_ok=True)


@app.get(f"{API_V1}/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
