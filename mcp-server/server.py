"""MCP server for Book Tracker.

Thin translator that exposes the FastAPI REST API as MCP tools.
Authenticates to the API using a per-user long-lived API key (Bearer).

Two transports are supported:
  - stdio  (default — for local Claude Desktop / MCP clients)
  - sse    (for running in Docker on port 8080)
"""
from __future__ import annotations

import os
import sys
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("BOOK_TRACKER_API_KEY", "")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8080"))

mcp = FastMCP("bestreads")


def _client() -> httpx.AsyncClient:
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return httpx.AsyncClient(base_url=API_BASE_URL, headers=headers, timeout=30.0)


def _book_summary(b: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": b.get("id"),
        "title": b.get("title"),
        "author": b.get("author"),
        "status": b.get("status"),
        "rating": b.get("rating"),
        "tags": [t.get("name") for t in b.get("tags", [])],
    }


@mcp.tool()
async def search_books(
    query: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    min_rating: int | None = None,
) -> list[dict[str, Any]]:
    """Find books in the user's library.

    Args:
        query: Free-text match against title/author/notes.
        status: One of 'want_to_read', 'reading', 'finished'.
        tag: Filter by tag name.
        min_rating: Only books with rating >= this value (1-5).
    """
    params: dict[str, Any] = {}
    if query:
        params["q"] = query
    if status:
        params["status"] = status
    if tag:
        params["tag"] = tag
    if min_rating:
        params["min_rating"] = min_rating
    async with _client() as c:
        r = await c.get("/books", params=params)
        r.raise_for_status()
        return [_book_summary(b) for b in r.json()]


@mcp.tool()
async def add_book(
    title: str,
    author: str,
    isbn: str | None = None,
    status: str = "want_to_read",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Add a book to the user's library.

    If an ISBN is provided, metadata and cover are auto-fetched from
    Open Library. Default status is 'want_to_read'.
    """
    body: dict[str, Any] = {
        "title": title,
        "author": author,
        "status": status,
    }
    if isbn:
        body["isbn"] = isbn
    if tags:
        body["tag_names"] = tags

    async with _client() as c:
        # Optionally enrich via lookup first
        if isbn:
            lookup = await c.get("/lookup", params={"isbn": isbn})
            if lookup.status_code == 200:
                data = lookup.json()
                body["title"] = body.get("title") or data.get("title") or title
                body["author"] = body.get("author") or data.get("author") or author
                body.setdefault("page_count", data.get("page_count"))
                body.setdefault("description", data.get("description"))
                if data.get("cover_image_path"):
                    body["cover_image_path"] = data["cover_image_path"]

        r = await c.post("/books", json=body)
        r.raise_for_status()
        return _book_summary(r.json())


@mcp.tool()
async def update_status(book_id: str, status: str) -> dict[str, Any]:
    """Move a book between shelves. Status must be 'want_to_read', 'reading', or 'finished'."""
    endpoint_map = {
        "reading": "start",
        "finished": "finish",
        "want_to_read": "reset",
    }
    if status not in endpoint_map:
        raise ValueError(f"Invalid status: {status}")
    async with _client() as c:
        r = await c.post(f"/books/{book_id}/{endpoint_map[status]}")
        r.raise_for_status()
        return _book_summary(r.json())


@mcp.tool()
async def rate_book(
    book_id: str, rating: int, notes: str | None = None
) -> dict[str, Any]:
    """Rate a book (1-5) and optionally attach markdown notes."""
    body: dict[str, Any] = {"rating": rating}
    if notes is not None:
        body["notes"] = notes
    async with _client() as c:
        r = await c.patch(f"/books/{book_id}", json=body)
        r.raise_for_status()
        return _book_summary(r.json())


@mcp.tool()
async def get_stats() -> dict[str, Any]:
    """Return reading summary: counts by status, finished this year, avg rating, top tags."""
    async with _client() as c:
        r = await c.get("/stats")
        r.raise_for_status()
        return r.json()


@mcp.tool()
async def recommend_books(
    mood: str | None = None,
    tag: str | None = None,
    count: int = 3,
) -> dict[str, Any]:
    """Get AI-powered book recommendations based on the user's library.

    Optional mood (e.g. 'cozy', 'brainy') and tag filters refine the results.
    """
    params: dict[str, Any] = {"count": count}
    if mood:
        params["mood"] = mood
    if tag:
        params["tag"] = tag
    async with _client() as c:
        r = await c.get("/recommendations", params=params)
        r.raise_for_status()
        return r.json()


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport == "sse":
        # FastMCP exposes an SSE HTTP server when transport=sse
        mcp.settings.host = HOST
        mcp.settings.port = PORT
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
