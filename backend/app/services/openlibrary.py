from __future__ import annotations

import os
from pathlib import Path

import httpx

from ..config import settings

OPEN_LIBRARY_BASE = "https://openlibrary.org"
OPEN_LIBRARY_COVERS = "https://covers.openlibrary.org"


async def _fetch_json(client: httpx.AsyncClient, url: str) -> dict | None:
    try:
        r = await client.get(url, timeout=10.0)
    except httpx.RequestError:
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


async def _resolve_author_name(client: httpx.AsyncClient, author_key: str) -> str | None:
    data = await _fetch_json(client, f"{OPEN_LIBRARY_BASE}{author_key}.json")
    if not data:
        return None
    return data.get("name")


async def lookup_isbn(isbn: str) -> dict | None:
    """Fetch metadata for a given ISBN from Open Library."""
    url = f"{OPEN_LIBRARY_BASE}/isbn/{isbn}.json"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        data = await _fetch_json(client, url)
        if not data:
            return None

        title = data.get("title", "")
        page_count = data.get("number_of_pages")
        description_field = data.get("description")
        if isinstance(description_field, dict):
            description = description_field.get("value")
        elif isinstance(description_field, str):
            description = description_field
        else:
            description = None

        # Authors: list of {"key": "/authors/OL..A"}
        author_names: list[str] = []
        for a in data.get("authors", []) or []:
            if isinstance(a, dict) and "key" in a:
                name = await _resolve_author_name(client, a["key"])
                if name:
                    author_names.append(name)
        author = ", ".join(author_names) if author_names else "Unknown"

        cover_url = f"{OPEN_LIBRARY_COVERS}/b/isbn/{isbn}-L.jpg"

    return {
        "title": title,
        "author": author,
        "isbn": isbn,
        "page_count": page_count,
        "description": description,
        "cover_url": cover_url,
    }


async def search_books(q: str, limit: int = 10) -> list[dict]:
    """Search Open Library by query for the quick-add flow."""
    url = f"{OPEN_LIBRARY_BASE}/search.json"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(url, params={"q": q, "limit": limit}, timeout=10.0)
        except httpx.RequestError:
            return []
        if r.status_code != 200:
            return []
        data = r.json()

    out: list[dict] = []
    for doc in data.get("docs", [])[:limit]:
        title = doc.get("title")
        if not title:
            continue
        authors = doc.get("author_name") or []
        author = ", ".join(authors) if authors else "Unknown"
        year = doc.get("first_publish_year")
        isbns = doc.get("isbn") or []
        isbn = isbns[0] if isbns else None
        cover_id = doc.get("cover_i")
        cover_url: str | None = None
        if cover_id:
            cover_url = f"{OPEN_LIBRARY_COVERS}/b/id/{cover_id}-M.jpg"
        elif isbn:
            cover_url = f"{OPEN_LIBRARY_COVERS}/b/isbn/{isbn}-M.jpg"
        out.append(
            {
                "title": title,
                "author": author,
                "year": year,
                "isbn": isbn,
                "cover_url": cover_url,
            }
        )
    return out


async def download_cover(isbn: str) -> str | None:
    """Download large cover for ISBN into covers_dir; return filename or None."""
    url = f"{OPEN_LIBRARY_COVERS}/b/isbn/{isbn}-L.jpg"
    return await download_cover_from_url(url, f"ol_{isbn}.jpg")


async def download_cover_from_url(url: str, suggested_name: str | None = None) -> str | None:
    """Download an Open Library cover URL into covers_dir; return filename or None.

    Accepts any cover URL (by isbn or by cover_id). Upgrades size-M to size-L
    where possible for better frontend display.
    """
    if not url:
        return None
    # Prefer large size if the URL used a smaller one
    upgraded = url.replace("-M.jpg", "-L.jpg").replace("-S.jpg", "-L.jpg")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            r = await client.get(upgraded, timeout=15.0)
        except httpx.RequestError:
            return None
    if r.status_code != 200:
        return None
    # Open Library serves a tiny placeholder for missing covers.
    if len(r.content) < 1024:
        return None
    os.makedirs(settings.covers_dir, exist_ok=True)

    if suggested_name:
        filename = suggested_name
    else:
        # Derive filename from the URL's last segment; fall back to a uuid
        tail = upgraded.rstrip("/").rsplit("/", 1)[-1] or "cover.jpg"
        filename = f"ol_{tail}"
    path = Path(settings.covers_dir) / filename
    path.write_bytes(r.content)
    return filename
