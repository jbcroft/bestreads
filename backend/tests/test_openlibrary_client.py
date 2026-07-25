import httpx
import pytest

from app.config import settings
from app.services import openlibrary


def test_client_sends_descriptive_user_agent():
    client = openlibrary._client()
    ua = client.headers.get("user-agent")
    # Must be our configured agent, never the httpx/library default that
    # Open Library throttles or blocks.
    assert ua == settings.openlibrary_user_agent
    assert "python-httpx" not in (ua or "")


@pytest.mark.asyncio
async def test_search_books_sends_user_agent(monkeypatch):
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["user-agent"] = request.headers.get("user-agent", "")
        return httpx.Response(
            200,
            json={
                "docs": [
                    {
                        "title": "Dune",
                        "author_name": ["Frank Herbert"],
                        "first_publish_year": 1965,
                        "isbn": ["9780441013593"],
                        "cover_i": 1,
                    }
                ]
            },
        )

    def fake_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={"User-Agent": settings.openlibrary_user_agent},
        )

    monkeypatch.setattr(openlibrary, "_client", fake_client)

    results = await openlibrary.search_books("dune", limit=5)

    assert captured["user-agent"] == settings.openlibrary_user_agent
    assert "python-httpx" not in captured["user-agent"]
    assert results and results[0]["title"] == "Dune"
    assert results[0]["author"] == "Frank Herbert"
