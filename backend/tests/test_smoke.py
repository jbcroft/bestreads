"""End-to-end smoke test for the book tracker stack.

Expects FastAPI to be reachable on http://localhost:8000 (or BASE_URL).
Run after `docker compose up --build`:

    pip install httpx pytest pytest-asyncio
    pytest backend/tests/test_smoke.py -v

This test exercises the full request path: register → login → add books
(crossing the 5-book threshold) → status transitions → tag → dashboard
reads → search → stats → recommendations → API key regeneration.
Recommendations degrades gracefully if ANTHROPIC_API_KEY is unset.
"""
from __future__ import annotations

import os
import uuid

import httpx
import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000") + "/api/v1"


def _rand(n: int = 8) -> str:
    return uuid.uuid4().hex[:n]


@pytest.mark.asyncio
async def test_full_stack_smoke() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as c:
        # --- healthz ---
        r = await c.get("/healthz")
        assert r.status_code == 200, r.text

        # --- register ---
        username = f"smoke_{_rand()}"
        email = f"{username}@example.com"
        r = await c.post(
            "/auth/register",
            json={"username": username, "email": email, "password": "s3cretpw"},
        )
        assert r.status_code == 201, r.text

        # --- login ---
        r = await c.post(
            "/auth/login",
            json={"username_or_email": username, "password": "s3cretpw"},
        )
        assert r.status_code == 200, r.text
        tokens = r.json()
        access = tokens["access_token"]
        auth = {"Authorization": f"Bearer {access}"}

        # --- create 5 books ---
        book_ids: list[str] = []
        sample = [
            ("The Name of the Wind", "Patrick Rothfuss", ["fantasy"]),
            ("Piranesi", "Susanna Clarke", ["fantasy", "favorites"]),
            ("The Remains of the Day", "Kazuo Ishiguro", ["literary"]),
            ("Project Hail Mary", "Andy Weir", ["scifi"]),
            ("The Shadow of the Wind", "Carlos Ruiz Zafón", ["literary"]),
        ]
        for title, author, tags in sample:
            r = await c.post(
                "/books",
                json={"title": title, "author": author, "tag_names": tags},
                headers=auth,
            )
            assert r.status_code == 201, r.text
            book_ids.append(r.json()["id"])

        # --- status transitions ---
        r = await c.post(f"/books/{book_ids[0]}/start", headers=auth)
        assert r.status_code == 200 and r.json()["status"] == "reading"

        r = await c.post(f"/books/{book_ids[1]}/finish", headers=auth)
        assert r.status_code == 200
        assert r.json()["status"] == "finished"
        assert r.json()["finished_at"] is not None

        r = await c.post(f"/books/{book_ids[1]}/reset", headers=auth)
        assert r.json()["status"] == "want_to_read"
        assert r.json()["finished_at"] is None

        # --- rate + notes (PATCH) ---
        r = await c.patch(
            f"/books/{book_ids[2]}",
            json={"rating": 5, "notes": "## Loved it\n\nGorgeous prose."},
            headers=auth,
        )
        assert r.status_code == 200
        assert r.json()["rating"] == 5

        # --- list by status ---
        r = await c.get("/books", params={"status": "reading"}, headers=auth)
        assert r.status_code == 200
        reading = r.json()
        assert len(reading) == 1

        # --- tag filter ---
        r = await c.get("/books", params={"tag": "fantasy"}, headers=auth)
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # --- full-text search ---
        r = await c.get("/search", params={"q": "wind"}, headers=auth)
        assert r.status_code == 200
        grouped = r.json()
        total = (
            len(grouped["want_to_read"]) + len(grouped["reading"]) + len(grouped["finished"])
        )
        assert total >= 1

        # --- stats ---
        r = await c.get("/stats", headers=auth)
        assert r.status_code == 200
        stats = r.json()
        assert stats["total_books"] == 5
        assert "by_status" in stats
        assert len(stats["finished_by_month"]) == 12

        # --- recommendations: must at least respond sanely ---
        r = await c.get("/recommendations", params={"count": 3}, headers=auth)
        assert r.status_code == 200
        recs = r.json()
        assert "available" in recs
        # When ANTHROPIC_API_KEY is set AND reachable, recommendations should be
        # available:true with 3 items. Otherwise, available:false is acceptable.
        if recs["available"]:
            assert len(recs["recommendations"]) >= 1
            for item in recs["recommendations"]:
                assert item["title"] and item["author"] and item["reason"]

        # --- API key regeneration ---
        r = await c.post("/settings/api-key/regenerate", headers=auth)
        assert r.status_code == 200
        plain_key = r.json()["api_key"]
        assert plain_key.startswith("bt_")

        # Key should now work as a bearer token (MCP auth path)
        api_key_auth = {"Authorization": f"Bearer {plain_key}"}
        r = await c.get("/books", headers=api_key_auth)
        assert r.status_code == 200
        assert len(r.json()) == 5
