from __future__ import annotations

import os
import re
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


# ---------- Descriptions ----------


def _normalize_description(raw: object) -> str | None:
    """Open Library returns descriptions as either a string or a {type,value} dict."""
    if isinstance(raw, dict):
        raw = raw.get("value")
    if not isinstance(raw, str):
        return None
    return raw.strip() or None


def _short_description(text: str, max_chars: int = 500) -> str:
    """Trim an Open Library description down to a brief display blurb.

    Takes the first paragraph, strips wiki/markdown artifacts, and caps at
    ``max_chars`` ending on a sentence boundary when possible.
    """
    # Strip inline markdown links: [text](url) -> text
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Strip trailing "([source][1])" style wiki footnotes
    cleaned = re.sub(r"\s*\(?\[[^\]]+\]\[\d+\]\)?", "", cleaned)
    # Strip markdown bold/italic emphasis (*, **, ***). Order matters: strip
    # longest runs first so we don't leave orphaned single asterisks.
    cleaned = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", cleaned)
    # Strip markdown heading markers (#) and blockquote markers (>) at line starts.
    cleaned = re.sub(r"(?m)^\s*[>#]+\s*", "", cleaned)
    # Strip "-- from Wikipedia" style signoffs at the end of the first paragraph
    cleaned = re.sub(r"\s*--+\s*from .*$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # First paragraph only — OL descriptions often have 2-3 paragraphs with
    # marketing fluff after the plot summary.
    first_para = cleaned.split("\n\n", 1)[0]
    # Collapse any internal line breaks into single spaces.
    first_para = re.sub(r"\s+", " ", first_para).strip()
    # Strip any leading punctuation left behind by earlier stripping passes
    # (e.g. "**Title:**" → ": ..." after bold-strip).
    first_para = re.sub(r"^[:\-–—\s]+", "", first_para)

    if len(first_para) <= max_chars:
        return first_para

    # Hard cap: trim to max_chars, then walk back to the nearest sentence
    # boundary if one is reasonably close.
    window = first_para[:max_chars]
    last_sentence_end = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if last_sentence_end > max_chars * 0.5:
        return window[: last_sentence_end + 1].strip()
    return window.rstrip() + "…"


async def _fetch_work_description(client: httpx.AsyncClient, work_key: str) -> str | None:
    """Fetch description from a /works/{key}.json endpoint."""
    # work_key looks like "/works/OL893415W"; normalize to full URL
    path = work_key if work_key.startswith("/") else f"/{work_key}"
    data = await _fetch_json(client, f"{OPEN_LIBRARY_BASE}{path}.json")
    if not data:
        return None
    return _normalize_description(data.get("description"))


def _significant_words(s: str) -> set[str]:
    """Lowercase content-word tokens with stopwords and short words stripped."""
    stop = {"a", "an", "the", "of", "and", "or", "to", "in", "on", "for", "with", "at", "by"}
    tokens = re.findall(r"[a-z0-9]+", s.lower())
    return {t for t in tokens if t not in stop and len(t) > 1}


def _is_confident_match(
    *, requested_title: str, requested_author: str, doc: dict
) -> bool:
    """Decide whether an Open Library search hit plausibly represents the
    requested book. Requires either a strong title match OR a weaker title
    match backed up by an author match.

    This is the guard that prevents Open Library from gluing a random book's
    description onto an unrelated title. Failure modes it catches:
    - "The AI Engineering Bible" → "A Christmas Carol" (no real match)
    - "The Shadow of the Wind" → "The Name of the Wind" (only "wind" in common)
    """
    cand_title = str(doc.get("title") or "")
    cand_authors = [str(a).lower() for a in (doc.get("author_name") or [])]

    req_title_words = _significant_words(requested_title)
    cand_title_words = _significant_words(cand_title)
    if not req_title_words:
        title_ratio = 1.0
    else:
        title_ratio = len(req_title_words & cand_title_words) / len(req_title_words)

    # Strong title match: most of the requested significant words are present.
    if title_ratio >= 0.8:
        return True

    # Otherwise, require the author to match alongside at least a 50% title overlap.
    req_author_norm = requested_author.lower().strip()
    if not req_author_norm or not cand_authors:
        return False
    author_match = any(
        req_author_norm in a or a in req_author_norm for a in cand_authors
    )
    return author_match and title_ratio >= 0.5


async def fetch_description(
    *,
    title: str,
    author: str,
    isbn: str | None,
) -> str | None:
    """Resolve a brief description for a book from Open Library.

    Strategy:
      1. If ISBN is known, hit /isbn/{isbn}.json (edition-level description).
      2. Otherwise, search.json by title + author, take the first hit with a
         work ``key``, and fetch /works/{key}.json.
      3. Fall back to title-only search if the combined query returns nothing
         useful (same ranking-quirk workaround used in the cover resolver).

    Returns a trimmed 1-paragraph blurb or ``None``.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # 1. ISBN edition endpoint
        if isbn:
            edition = await _fetch_json(client, f"{OPEN_LIBRARY_BASE}/isbn/{isbn}.json")
            if edition:
                desc = _normalize_description(edition.get("description"))
                if desc:
                    return _short_description(desc)
                # Edition might reference a work — try that
                works = edition.get("works") or []
                if works and isinstance(works[0], dict):
                    work_key = works[0].get("key")
                    if work_key:
                        desc = await _fetch_work_description(client, work_key)
                        if desc:
                            return _short_description(desc)

        # 2. & 3. Title+author then title-only search
        queries: list[str] = []
        combined = f"{title} {author}".strip()
        if combined:
            queries.append(combined)
        if title and title.strip() not in queries:
            queries.append(title.strip())

        for query in queries:
            try:
                r = await client.get(
                    f"{OPEN_LIBRARY_BASE}/search.json",
                    params={"q": query, "limit": 5},
                    timeout=10.0,
                )
            except httpx.RequestError:
                continue
            if r.status_code != 200:
                continue
            docs = r.json().get("docs", []) or []

            def _lang_ok(doc: dict) -> bool:
                langs = doc.get("language") or []
                return "eng" in langs if langs else True  # Accept unknown lang

            # Keep only confident matches, prefer English, preserve rank.
            confident = [
                d
                for d in docs
                if _is_confident_match(
                    requested_title=title, requested_author=author, doc=d
                )
            ]
            ordered = [d for d in confident if _lang_ok(d)] + [
                d for d in confident if not _lang_ok(d)
            ]

            for doc in ordered:
                work_key = doc.get("key")
                if not work_key:
                    continue
                desc = await _fetch_work_description(client, work_key)
                if desc:
                    return _short_description(desc)

    return None
