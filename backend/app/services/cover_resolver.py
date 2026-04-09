"""Cover resolution cascade.

Given the metadata we have about a book, try each available strategy in
priority order to locate and download a cover image. Returns the saved
filename (relative to covers_dir) on success, or None if nothing worked.

Strategy order:
    1. Explicit cover_url from the client (Quick-Add path)
    2. ISBN-based lookup against Open Library's covers CDN
    3. Title + author full-text search on Open Library, take the first
       result that has a cover (Manual-Add fallback)
"""
from __future__ import annotations

from .openlibrary import download_cover, download_cover_from_url, search_books


async def resolve_book_cover(
    *,
    title: str,
    author: str,
    isbn: str | None,
    cover_url: str | None,
) -> str | None:
    """Return a saved cover filename, or None if nothing could be resolved."""
    # 1. Explicit URL (Quick-Add chose an Open Library search result)
    if cover_url:
        try:
            fn = await download_cover_from_url(cover_url)
        except Exception:
            fn = None
        if fn:
            return fn

    # 2. ISBN cover lookup
    if isbn:
        try:
            fn = await download_cover(isbn)
        except Exception:
            fn = None
        if fn:
            return fn

    # 3. Title + author search fallback. Look through the top few results
    # instead of just the first one — Open Library's ranking sometimes
    # surfaces secondary literature (e.g. academic commentary) above the
    # primary work, and those entries often have no cover art.
    #
    # We also try a title-only query as a second pass, because appending
    # the author occasionally demotes the primary work (e.g. "1Q84 Haruki
    # Murakami" ranks Japanese commentary above the novel itself).
    queries = []
    combined = f"{title} {author}".strip()
    if combined:
        queries.append(combined)
    if title and title.strip() not in queries:
        queries.append(title.strip())

    for query in queries:
        try:
            results = await search_books(query, limit=5)
        except Exception:
            results = []
        for item in results:
            candidate = item.get("cover_url")
            if not candidate:
                continue
            try:
                fn = await download_cover_from_url(candidate)
            except Exception:
                fn = None
            if fn:
                return fn

    return None
