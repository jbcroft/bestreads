# Claude-generated tags for books — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically generate 2–5 genre + theme tags for books via Claude on every book add, and provide a one-shot backfill script to tag the existing library.

**Architecture:** A new service module `backend/app/services/tag_generator.py` makes the Claude call and returns a normalized list of tag names. A third opportunistic enrichment step in `create_book` (after cover and description fetch) loads the user's existing tag vocabulary, calls the service, and merges results via the existing `resolve_or_create_tags` helper. A `backend/scripts/backfill_tags.py` one-shot script applies the same flow to every book in the database. All failures degrade silently — book creation is never blocked.

**Tech Stack:** FastAPI, SQLAlchemy async, anthropic Python SDK 0.92.0, pytest, Docker Compose, PostgreSQL.

**Full spec:** `docs/superpowers/specs/2026-04-09-claude-tag-generator-design.md`

---

## File Structure

### New files
- `backend/app/services/tag_generator.py` — Claude call + pure normalizer. No DB, no ORM imports.
- `backend/scripts/backfill_tags.py` — one-shot backfill, mirrors `backfill_covers.py` / `backfill_descriptions.py`.
- `backend/tests/test_tag_normalize.py` — pure unit tests for the normalizer.

### Modified files
- `backend/app/services/tags.py` — append `load_user_tag_names` helper (one function, ~8 lines).
- `backend/app/routers/books.py` — add the third opportunistic enrichment block in `create_book`, after the description fetch.
- `backend/tests/test_smoke.py` — add a conditional auto-tag assertion block after the existing book-creation assertions.

### Unchanged
- No schema changes, no alembic migrations.
- No frontend changes — `BookDetail.tsx` and the library tag filter already render tags however they appear on a book.
- No changes to `anthropic_recs.py` or the recommendations feature.

---

## Task 1: Normalizer helper with unit tests (TDD)

**Files:**
- Create: `backend/app/services/tag_generator.py` (first pass — just the normalizer and its supporting constants)
- Create: `backend/tests/test_tag_normalize.py`

The normalizer is a pure function with real edge cases. Writing its tests first gives us fast, deterministic feedback on any regressions to tag style rules.

- [ ] **Step 1: Create the test file with failing tests**

Create `backend/tests/test_tag_normalize.py`:

```python
from app.services.tag_generator import _normalize_tags


def test_lowercases_and_dedupes():
    assert _normalize_tags(["Fantasy", "fantasy", "FANTASY"]) == ["fantasy"]


def test_hyphens_collapse_whitespace():
    assert _normalize_tags(["coming of age"]) == ["coming-of-age"]


def test_accepts_already_hyphenated():
    assert _normalize_tags(["sci-fi", "coming-of-age"]) == ["sci-fi", "coming-of-age"]


def test_rejects_punctuation_other_than_hyphen():
    # sci-fi is fine, sci_fi and sci/fi are not
    assert _normalize_tags(["sci-fi", "sci_fi", "sci/fi"]) == ["sci-fi"]


def test_drops_meta_tags():
    assert _normalize_tags(["fantasy", "favorites", "to-read", "tbr", "recommended"]) == ["fantasy"]


def test_drops_uk_spelling_meta_tag():
    assert _normalize_tags(["favourites", "fantasy"]) == ["fantasy"]


def test_caps_at_five():
    result = _normalize_tags(["a", "b", "c", "d", "e", "f", "g"])
    assert len(result) == 5
    assert result == ["a", "b", "c", "d", "e"]


def test_rejects_too_long():
    assert _normalize_tags(["a" * 31]) == []


def test_allows_max_length():
    assert _normalize_tags(["a" * 30]) == ["a" * 30]


def test_rejects_empty_strings():
    assert _normalize_tags(["", " ", "fantasy"]) == ["fantasy"]


def test_rejects_non_string_entries():
    # Defensive — should not crash on mixed types
    assert _normalize_tags(["fantasy", None, 42, {"x": 1}]) == ["fantasy"]


def test_preserves_order_of_first_occurrence():
    assert _normalize_tags(["scifi", "fantasy", "scifi", "literary"]) == ["scifi", "fantasy", "literary"]


def test_rejects_leading_hyphen():
    # Regex requires [a-z0-9] as the first character
    assert _normalize_tags(["-fantasy"]) == []


def test_empty_input():
    assert _normalize_tags([]) == []
```

- [ ] **Step 2: Run tests to verify they fail with ImportError**

Run from the repo root:
```bash
cd backend && python -m pytest tests/test_tag_normalize.py -v
```

Expected output: ImportError / ModuleNotFoundError on `app.services.tag_generator` — the module doesn't exist yet. This confirms the tests are wired up and would fail until we implement.

- [ ] **Step 3: Create `backend/app/services/tag_generator.py` with the normalizer**

Create the file with just the normalizer scaffolding (we'll add the Claude call in Task 3):

```python
"""Claude-backed tag generator for books.

Given a book's metadata and the user's existing tag vocabulary, asks
Claude to produce 2-5 concise genre + theme tags. All failures degrade
silently to an empty list — tag generation must never block book
creation.
"""
from __future__ import annotations

import re

# Tags that Claude must not produce (prompt tells it not to, but we
# defensively filter too in case it slips one through).
_META_TAG_BLACKLIST = {
    "favorites",
    "favourites",
    "to-read",
    "tbr",
    "read",
    "classic",
    "recommended",
    "wishlist",
}

# Valid tag shape: lowercased ASCII, starts with alnum, allows hyphens,
# total length 1-30 chars.
_TAG_RE = re.compile(r"[a-z0-9][a-z0-9\-]{0,29}")


def _normalize_tags(raw: list) -> list[str]:
    """Clean and clamp a raw tag list from Claude into our style.

    - Lowercases
    - Collapses whitespace runs to hyphens
    - Rejects anything with punctuation other than hyphens
    - Rejects meta/personal tags (favorites, to-read, etc.)
    - Dedupes (preserving first-occurrence order)
    - Caps the result at 5 tags
    """
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        if not isinstance(t, str):
            continue
        t = t.strip().lower()
        if not t:
            continue
        t = re.sub(r"\s+", "-", t)
        if not _TAG_RE.fullmatch(t):
            continue
        if t in _META_TAG_BLACKLIST:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:5]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd backend && python -m pytest tests/test_tag_normalize.py -v
```

Expected output: All 14 tests pass. If any fail, read the assertion carefully and fix the implementation — the tests are the source of truth.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/tag_generator.py backend/tests/test_tag_normalize.py
git commit -m "$(cat <<'MSG'
feat(tags): add Claude tag normalizer helper with unit tests

Pure function that clamps a raw list of tag strings into our tag
style: lowercased ASCII, hyphen-separated multi-word, no
punctuation other than hyphens, dedup preserving order, max length
30 chars, capped at 5 tags. Rejects meta/personal tags
(favorites, to-read, tbr, recommended, etc.).

First step of the Claude tag generator feature — later tasks add
the Claude API call and wire it into create_book.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 2: `load_user_tag_names` helper

**Files:**
- Modify: `backend/app/services/tags.py` — append one helper function after `resolve_or_create_tags`

Loads the user's complete tag vocabulary alphabetized. Used by both `create_book` (to pass into the Claude prompt) and the backfill script.

No tests — consistent with `resolve_or_create_tags` which is already un-unit-tested. Will be exercised end-to-end in Task 5's smoke test.

- [ ] **Step 1: Append the helper to `backend/app/services/tags.py`**

After the existing `resolve_or_create_tags` function (below line 39), append:

```python


async def load_user_tag_names(session: AsyncSession, user_id: UUID) -> list[str]:
    """Return every tag name owned by a user, alphabetized.

    Loads ALL of the user's tags, not just tags currently applied to
    books — if the user created a tag but hasn't attached it to
    anything yet, the tag generator should still see it as a candidate
    for reuse. Alphabetized so the Claude prompt is deterministic
    across calls (aids reproducibility when debugging).
    """
    result = await session.execute(
        select(Tag.name).where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return [row[0] for row in result.all()]
```

The file already imports `select`, `AsyncSession`, `UUID`, and `Tag`, so no new imports are needed. Verify by re-reading the top of the file if unsure.

- [ ] **Step 2: Verify the module still imports cleanly**

Run:
```bash
cd backend && python -c "from app.services.tags import load_user_tag_names, resolve_or_create_tags; print('ok')"
```

Expected output: `ok`

If you see an ImportError, check that `AsyncSession`, `UUID`, `select`, and `Tag` are all already imported at the top of the file.

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/tags.py
git commit -m "$(cat <<'MSG'
feat(tags): add load_user_tag_names helper

Returns all tag names owned by a user, alphabetized for determinism.
Loads every tag the user has created, including unattached ones, so
the upcoming Claude tag generator can see the full vocabulary when
deciding whether to reuse an existing tag.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 3: `generate_book_tags` Claude call

**Files:**
- Modify: `backend/app/services/tag_generator.py` — append the async `generate_book_tags` function and supporting constants

Second pass on the service module. Adds the actual Claude API call, the prompt template, and the response parsing (manual JSON with fence-stripping, matching `anthropic_recs._parse_recommendations` rather than structured outputs — see spec's "Response format" section for rationale).

No unit tests for this function — it's thin wiring over a network call, and mocking `AsyncAnthropic` would be more code than the function itself. Covered end-to-end by the smoke test in Task 6.

- [ ] **Step 1: Add imports to `backend/app/services/tag_generator.py`**

At the top of the file, replace:

```python
from __future__ import annotations

import re
```

with:

```python
from __future__ import annotations

import json
import logging
import re

import anthropic
from anthropic import AsyncAnthropic

from ..config import settings

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Add the prompt constants after `_TAG_RE`**

Insert after `_TAG_RE = re.compile(...)` and before `def _normalize_tags`:

```python
_SYSTEM_PROMPT = (
    "You are a book classifier. Given a book's title, author, and description, "
    "produce a small set of concise tags covering its genre and main themes or "
    "subject matter.\n\n"
    "Respond with ONLY a JSON array of tag strings — no preamble, no "
    "explanation, no markdown code fences.\n\n"
    "Hard constraints:\n"
    "- Return 2 to 5 tags total.\n"
    "- Include at least one genre tag (e.g. scifi, fantasy, mystery, literary, "
    "historical-fiction, nonfiction, memoir).\n"
    "- The remaining tags should describe themes or subject matter "
    "(e.g. politics, economics, coming-of-age, dystopia, space-opera, ww2).\n"
    "- Tag style: lowercased ASCII; short (1-2 words); hyphen-separated if "
    "multi-word; never include spaces, punctuation, or capitals.\n"
    "- Never produce meta or personal tags like favorites, to-read, classic, "
    "recommended.\n"
    "- STRONGLY prefer reusing tags from the user's existing vocabulary when "
    "any fit. Only invent a new tag when no existing tag fits."
)
```

- [ ] **Step 3: Add the parser helper after `_normalize_tags`**

At the end of the file, add:

```python


def _parse_tag_array(text: str) -> list[str]:
    """Parse Claude's response into a list of raw tag strings.

    Handles the common failure modes: markdown fences, leading/trailing
    whitespace, and responses that embed the JSON array inside other
    prose. Returns [] if nothing usable can be extracted.
    """
    if not text:
        return []
    cleaned = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: find the first [...] block and try that
        bracket_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not bracket_match:
            return []
        try:
            data = json.loads(bracket_match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    return data
```

- [ ] **Step 4: Add the `generate_book_tags` async function at the end of the file**

Append:

```python


async def generate_book_tags(
    *,
    title: str,
    author: str,
    description: str | None,
    existing_user_tags: list[str],
) -> list[str]:
    """Return 2-5 normalized tags for a book, or [] on any failure.

    Never raises — all exceptions (API failures, parse errors, bad
    responses) are logged and swallowed, returning an empty list. The
    caller is responsible for persisting any tags it does receive.
    """
    if not settings.anthropic_api_key:
        return []

    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=10.0,
        max_retries=0,
    )

    vocab_json = json.dumps(existing_user_tags)
    desc_line = (
        f"- Description: {description}"
        if description
        else "- Description: (none provided)"
    )
    user_message = (
        f"The user's existing tag vocabulary: {vocab_json}\n\n"
        f"Tag this book:\n"
        f"- Title: {title}\n"
        f"- Author: {author}\n"
        f"{desc_line}"
    )

    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        logger.warning(
            "claude tag generation failed for %r: %s: %s",
            title,
            type(exc).__name__,
            exc,
        )
        return []

    raw_text = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            raw_text += block.text

    raw_tags = _parse_tag_array(raw_text)
    normalized = _normalize_tags(raw_tags)
    if not normalized:
        logger.warning(
            "claude tag response failed normalization for %r: raw=%r",
            title,
            raw_text,
        )
    return normalized
```

- [ ] **Step 5: Verify the normalizer tests still pass and the module imports cleanly**

Run:
```bash
cd backend && python -m pytest tests/test_tag_normalize.py -v
cd backend && python -c "from app.services.tag_generator import generate_book_tags, _normalize_tags, _parse_tag_array; print('ok')"
```

Expected: all normalizer tests still pass, and the import prints `ok`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/tag_generator.py
git commit -m "$(cat <<'MSG'
feat(tags): add Claude tag generator service

async generate_book_tags(title, author, description, existing_user_tags)
returns 2-5 normalized tags for a book by asking Claude to classify it.

- System prompt includes hard constraints on style and count, plus
  strict-reuse instruction for the user's existing tag vocabulary.
- Uses the same timeout=10, max_retries=0 pattern as the recent
  recommendations fix to fail fast when the Docker-to-Anthropic
  network path is wedged.
- Manual JSON parsing with fence-stripping, mirroring anthropic_recs.
  _parse_recommendations — the installed SDK version doesn't expose
  the structured-output param, so we stick with the proven pattern.
- All failures (API errors, parse failures, empty normalized result)
  are logged at WARN and return []. Never raises.

Covered end-to-end by the smoke test in a later task; the pure
normalizer is covered by the existing unit tests.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 4: Wire tag generation into `create_book`

**Files:**
- Modify: `backend/app/routers/books.py` — add a third opportunistic enrichment block after the description fetch block (around line 149)

This is where the feature actually activates on new book adds. The block sits AFTER the description fetch so Claude sees the Open Library blurb we just pulled.

- [ ] **Step 1: Re-read the current state of `create_book` to confirm line numbers**

Run:
```bash
sed -n '99,155p' backend/app/routers/books.py
```

You should see the `create_book` function ending with the description-fetch block:

```python
    # Opportunistic description fetch from Open Library.
    if not book.description:
        from ..services.openlibrary import fetch_description

        try:
            desc = await fetch_description(
                title=book.title,
                author=book.author,
                isbn=book.isbn,
            )
        except Exception:
            desc = None
        if desc:
            book.description = desc
            session.add(book)
            await session.commit()
            await session.refresh(book, attribute_names=["tags"])

    return book_to_read(book)
```

If your line numbers differ, locate this block and adapt the Edit below accordingly.

- [ ] **Step 2: Insert the tag generation block before `return book_to_read(book)`**

Edit `backend/app/routers/books.py`. Find:

```python
        if desc:
            book.description = desc
            session.add(book)
            await session.commit()
            await session.refresh(book, attribute_names=["tags"])

    return book_to_read(book)
```

Replace with:

```python
        if desc:
            book.description = desc
            session.add(book)
            await session.commit()
            await session.refresh(book, attribute_names=["tags"])

    # Opportunistic tag generation via Claude. Runs on every POST /books,
    # even when the user passed explicit tag_names — Claude's tags merge
    # on top of manual ones. Failure degrades silently.
    try:
        from ..services.tag_generator import generate_book_tags
        from ..services.tags import load_user_tag_names

        existing_vocab = await load_user_tag_names(session, user.id)
        suggested = await generate_book_tags(
            title=book.title,
            author=book.author,
            description=book.description,
            existing_user_tags=existing_vocab,
        )
    except Exception:
        suggested = []

    if suggested:
        new_tags = await resolve_or_create_tags(session, user.id, suggested)
        existing_ids = {t.id for t in book.tags}
        actually_new = [t for t in new_tags if t.id not in existing_ids]
        if actually_new:
            for t in actually_new:
                book.tags.append(t)
            session.add(book)
            await touch_library(user, session)
            await session.commit()
            await session.refresh(book, attribute_names=["tags"])

    return book_to_read(book)
```

- [ ] **Step 3: Verify the module still imports cleanly**

Run:
```bash
cd backend && python -c "from app.routers.books import create_book; print('ok')"
```

Expected: `ok`. If you see an ImportError, the most likely cause is that `resolve_or_create_tags` or `touch_library` isn't already imported at the top of the file. Check the existing imports — both should already be there from the existing tag-resolution and status-transition code paths.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/books.py
git commit -m "$(cat <<'MSG'
feat(books): wire Claude tag generation into create_book

Third opportunistic enrichment step, after cover resolution and
description fetch. Loads the user's existing tag vocabulary, calls
generate_book_tags, resolves returned names to Tag rows via the
existing resolve_or_create_tags helper, and merges into book.tags
add-only (never removes existing tags).

- Runs on every POST /books, even when the user passed explicit
  tag_names — Claude's tags merge on top of manual ones.
- Only commits and touches library timestamp when actually-new tags
  were added, avoiding spurious recommendations cache invalidation
  when Claude's suggestions all happen to already be on the book.
- Outer try/except Exception defensively catches non-SDK bugs so
  book creation is never blocked by tagging failures.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 5: Backfill script

**Files:**
- Create: `backend/scripts/backfill_tags.py`

Mirrors `backfill_covers.py` and `backfill_descriptions.py`. Iterates every user, loads their vocabulary once, processes all their books, commits at the end.

- [ ] **Step 1: Create `backend/scripts/backfill_tags.py`**

```python
"""Backfill Claude-generated tags for every book in the database.

Iterates every user, loads their current tag vocabulary once, and runs
generate_book_tags against each of their books. Merges returned tags
into the book's tag set add-only — never removes existing tags.

Safe and idempotent in the add-only sense: re-runs won't duplicate
tags. However, Claude is non-deterministic, so re-runs MAY add new
tags that didn't appear on the first run. If that becomes noisy,
add a --only-untagged flag (not shipped on day one).

Known limitation: for very large libraries (10,000+ books) we'd want
periodic flush/commit; current implementation commits once at the end
of the whole run.

Usage (inside the running fastapi container):

    docker compose exec fastapi python scripts/backfill_tags.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Make the parent app/ package importable when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import Book, User  # noqa: E402
from app.services.tag_generator import generate_book_tags  # noqa: E402
from app.services.tags import load_user_tag_names, resolve_or_create_tags  # noqa: E402
from app.services.transitions import touch_library  # noqa: E402


async def main() -> int:
    async with SessionLocal() as session:
        users_result = await session.execute(select(User))
        users = list(users_result.scalars().all())
        if not users:
            print("No users found.")
            return 0

        for user in users:
            vocab = await load_user_tag_names(session, user.id)
            books_result = await session.execute(
                select(Book)
                .where(Book.user_id == user.id)
                .options(selectinload(Book.tags))
            )
            books = list(books_result.scalars().unique().all())

            print(f"[{user.username}] {len(books)} books, vocab={vocab}")

            added_total = 0
            for book in books:
                try:
                    suggested = await generate_book_tags(
                        title=book.title,
                        author=book.author,
                        description=book.description,
                        existing_user_tags=vocab,
                    )
                except Exception as exc:
                    print(f"  !!  {book.title}: {type(exc).__name__}: {exc}")
                    continue

                if not suggested:
                    print(f"  --  {book.title} (no tags)")
                    continue

                new_tags = await resolve_or_create_tags(
                    session, user.id, suggested
                )
                existing_ids = {t.id for t in book.tags}
                actually_new = [t for t in new_tags if t.id not in existing_ids]
                if actually_new:
                    for t in actually_new:
                        book.tags.append(t)
                    session.add(book)
                    added_total += len(actually_new)
                    names = [t.name for t in book.tags]
                    print(f"  OK  {book.title} -> {names}")
                else:
                    print(f"  ~~  {book.title} (all suggestions already present)")

            if added_total:
                await touch_library(user, session)
                print(f"[{user.username}] {added_total} new tags added")
            else:
                print(f"[{user.username}] no changes")

        await session.commit()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

- [ ] **Step 2: Verify the script parses as valid Python**

Run from the repo root:
```bash
python3 -c "import ast; ast.parse(open('backend/scripts/backfill_tags.py').read()); print('ok')"
```

Expected: `ok`. This is a cheap syntax check — the script can't be imported directly from the host because it depends on the fastapi app package.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/backfill_tags.py
git commit -m "$(cat <<'MSG'
feat(tags): add one-shot backfill script for Claude tags

Iterates every user, loads their tag vocabulary once, runs
generate_book_tags against each of their books, and merges results
into book.tags add-only. Skips books where Claude returned nothing,
prints per-book status (OK / skip / ~~ all already present / !!
error), commits once at the end, touches library timestamps per user.

Idempotent in the add-only sense; Claude non-determinism means
re-runs may add additional tags over time. Known limitation: single
batched commit at the end, fine for hundreds of books but would
need flush/commit chunks for 10,000+.

Run with:
  docker compose exec fastapi python scripts/backfill_tags.py

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 6: Smoke test extension

**Files:**
- Modify: `backend/tests/test_smoke.py` — add a new book-creation block after the existing list-by-status assertion

End-to-end proof that a `POST /books` on the running stack comes back with a populated `tags` field when Anthropic is reachable, and still succeeds (with `tags` as an empty list) when it isn't.

- [ ] **Step 1: Re-read the smoke test to find the insertion point**

Run:
```bash
sed -n '95,115p' backend/tests/test_smoke.py
```

You'll see:

```python
        # --- list by status ---
        r = await c.get("/books", params={"status": "reading"}, headers=auth)
        assert r.status_code == 200
        reading = r.json()
        assert len(reading) == 1

        # --- tag filter ---
        r = await c.get("/books", params={"tag": "fantasy"}, headers=auth)
```

We'll insert between the `--- list by status ---` block and the `--- tag filter ---` block.

- [ ] **Step 2: Insert the auto-tag assertion block**

Edit `backend/tests/test_smoke.py`. Find:

```python
        # --- list by status ---
        r = await c.get("/books", params={"status": "reading"}, headers=auth)
        assert r.status_code == 200
        reading = r.json()
        assert len(reading) == 1

        # --- tag filter ---
```

Replace with:

```python
        # --- list by status ---
        r = await c.get("/books", params={"status": "reading"}, headers=auth)
        assert r.status_code == 200
        reading = r.json()
        assert len(reading) == 1

        # --- auto-tag: new books get Claude-generated tags if the Anthropic
        #     API is reachable. If not, the feature silently degrades and we
        #     only assert that book creation still succeeds and the tags
        #     field is still present as a list.
        r = await c.post(
            "/books",
            json={"title": "Dune", "author": "Frank Herbert"},
            headers=auth,
        )
        assert r.status_code == 201, r.text
        dune = r.json()
        assert isinstance(dune["tags"], list)
        if dune["tags"]:
            # Claude path worked — assert style properties
            tag_names = [t["name"] for t in dune["tags"]]
            for name in tag_names:
                assert name == name.lower(), f"tag not lowercased: {name}"
                assert " " not in name, f"tag contains space: {name}"
                assert len(name) <= 30, f"tag too long: {name}"
            assert len(tag_names) <= 5, f"too many tags: {tag_names}"

        # --- tag filter ---
```

- [ ] **Step 3: Verify the file still parses**

```bash
python3 -c "import ast; ast.parse(open('backend/tests/test_smoke.py').read()); print('ok')"
```

Expected: `ok`.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_smoke.py
git commit -m "$(cat <<'MSG'
test(smoke): add conditional auto-tag assertion for new books

Adds a POST /books block for 'Dune by Frank Herbert' and asserts:
- book creation still succeeds (201)
- the tags field is still a list
- if tags came back, all names are lowercased, space-free, <=30 chars
- and there are at most 5 of them

Assertion is conditional on 'if dune[\"tags\"]:' so the smoke test
stays runnable even when the current Docker-to-Anthropic network
issue blocks the Claude call. Same pattern the test file already
uses for the /recommendations endpoint.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
MSG
)"
```

---

## Task 7: End-to-end verification

No commit for this task — it's a verification pass that confirms Tasks 1–6 landed correctly. If any step fails, fix the issue in the relevant earlier task, commit, and re-run this task.

**Files:** none modified directly.

- [ ] **Step 1: Run the unit tests for the normalizer**

```bash
cd backend && python -m pytest tests/test_tag_normalize.py -v
```

Expected: all 14 tests pass. If any fail, check the `_normalize_tags` implementation in `backend/app/services/tag_generator.py` against the test expectations.

- [ ] **Step 2: Rebuild the fastapi container with the new code**

```bash
docker compose up --build -d fastapi
```

Expected: build succeeds, container starts. Tail logs briefly to confirm no startup errors:

```bash
docker compose logs fastapi 2>&1 | tail -20
```

Expected: `Application startup complete.` and `Uvicorn running on http://0.0.0.0:8000`. No tracebacks.

- [ ] **Step 3: Manual POST /books smoke test**

Run a quick Python one-liner against the running API to create a fresh book and confirm tags come back:

```bash
python3 <<'PY'
import httpx, uuid
BASE = "http://localhost:8001/api/v1"
u = f"tagtest_{uuid.uuid4().hex[:6]}"
with httpx.Client(base_url=BASE, timeout=60.0) as c:
    c.post("/auth/register", json={"username": u, "email": f"{u}@ex.com", "password": "s3cretpw"})
    r = c.post("/auth/login", json={"username_or_email": u, "password": "s3cretpw"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = c.post("/books", json={"title": "Neuromancer", "author": "William Gibson"}, headers=h)
    print("status:", r.status_code)
    b = r.json()
    print("title:", b["title"])
    print("tags:", [t["name"] for t in b["tags"]])
    print("cover:", b.get("cover_url"))
    print("description:", (b.get("description") or "")[:100])
PY
```

Expected outcome in a healthy environment: `status: 201`, a non-empty `tags` list (something like `['scifi', 'cyberpunk', 'ai']`), a populated cover URL, and a populated description.

Expected outcome when Anthropic is unreachable (current state): `status: 201`, `tags: []`, cover and description still populated. The feature degrades silently — this is a pass, not a fail.

In either case the request must return 201, not 500. If it 500s, check the fastapi logs for an unhandled exception and trace it back to Task 4's wiring.

- [ ] **Step 4: Inspect the database for the test book's tags**

```bash
docker compose exec -T postgres psql -U booktracker -d booktracker -c "SELECT b.title, array_agg(t.name ORDER BY t.name) AS tags FROM books b LEFT JOIN book_tags bt ON bt.book_id = b.id LEFT JOIN tags t ON t.id = bt.tag_id WHERE b.title = 'Neuromancer' GROUP BY b.title ORDER BY b.title DESC LIMIT 1;"
```

Expected in healthy environment: one row with `title = Neuromancer` and `tags = {scifi,cyberpunk,ai}` or similar. Empty array `{NULL}` is acceptable if Anthropic is unreachable — confirms the degraded-success path.

- [ ] **Step 5: Run the backfill script against the existing library**

```bash
docker compose exec -T fastapi python scripts/backfill_tags.py
```

Expected output pattern:

```
[justin] NN books, vocab=['fantasy', 'favorites', 'literary', 'scifi']
  OK  Dune -> ['scifi', 'literary', 'desert', 'coming-of-age']
  OK  1984 -> ['scifi', 'literary', 'dystopia']
  ...
  --  The Race to the Future... (no tags)
  !!  <some book>: APITimeoutError: ...
  ...
[justin] NN new tags added
```

If Anthropic is reachable: expect `OK` on most books, a few `--` or `!!` for niche titles. The existing user tags (`fantasy`, `literary`, `scifi`) should be heavily reused — eyeball a few of the output lines to confirm Claude isn't inventing `sci-fi` alongside existing `scifi`, etc. If sprawl is obvious, the system prompt may need tightening (out of scope for this task — file as a follow-up).

If Anthropic is unreachable: expect all `!!` lines, final `no changes`. Still counts as a pass — the failure mode is correct.

- [ ] **Step 6: Post-backfill DB check**

Count tags per name for the user with the most books (which is the "real" user — all the test-smoke-run users each have at most 5 books):

```bash
docker compose exec -T postgres psql -U booktracker -d booktracker -c "WITH biggest AS (SELECT user_id FROM books GROUP BY user_id ORDER BY count(*) DESC LIMIT 1) SELECT t.name, count(bt.book_id) AS uses FROM tags t LEFT JOIN book_tags bt ON bt.tag_id = t.id WHERE t.user_id = (SELECT user_id FROM biggest) GROUP BY t.name ORDER BY uses DESC, t.name;"
```

Expected: your original four tags (`fantasy`, `literary`, `scifi`, `favorites`) plus any new tags Claude created during the backfill. Tag counts should be sensible (not every book is `fantasy`, etc.). If Anthropic was unreachable during the backfill, the result should be unchanged from before the backfill ran.

- [ ] **Step 7: Run the full smoke test suite against the running stack**

```bash
BASE_URL=http://localhost:8001 python3 -m pytest backend/tests/test_smoke.py -v
```

Expected: either all tests pass, or only the pre-existing `/recommendations` 500 (documented Docker networking issue — unrelated to this feature) fails. The new auto-tag assertion block must not be the failing step.

- [ ] **Step 8: Final working-tree check**

```bash
git status
git log --oneline -8
```

Expected: working tree clean (aside from `frontend/tsconfig.tsbuildinfo` as always), and `git log --oneline -8` shows six new commits from Tasks 1–6 on top of the previous HEAD.

---

## Summary of commits produced

After all tasks complete, `git log --oneline` should show these six new commits (most recent last):

1. `feat(tags): add Claude tag normalizer helper with unit tests`
2. `feat(tags): add load_user_tag_names helper`
3. `feat(tags): add Claude tag generator service`
4. `feat(books): wire Claude tag generation into create_book`
5. `feat(tags): add one-shot backfill script for Claude tags`
6. `test(smoke): add conditional auto-tag assertion for new books`

Task 7 (verification) produces no commits.
