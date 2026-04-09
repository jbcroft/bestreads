# Claude-generated tags for books — design

## Context

The book tracker already supports user-defined tags (many-to-many between `Book` and `Tag`, user-scoped, managed through the library UI), but the user's tag vocabulary stays tiny unless they actively curate it. The current library has four tags total: `fantasy`, `literary`, `scifi`, `favorites`. Nearly every book has either no tags or a single genre tag, which makes the Library tag-filter and the Stats top-tags widget near-useless for discovery.

Claude is already integrated for recommendations and can infer a book's genre and main themes from title + author + description. We now fetch descriptions from Open Library (41/50 books have them), so we have enough signal to generate 2–5 meaningful tags per book automatically. This spec designs a feature that runs tag generation on new books as they're added and provides a one-shot backfill script for the existing library.

## Confirmed decisions

| | |
|---|---|
| **Trigger** | Automatic on book add, plus one-shot backfill script for the existing library |
| **Vocabulary control** | Prefer reusing the user's existing tag names verbatim; new tags allowed only when nothing existing fits |
| **Tag categories** | Genre (≥1) + theme/subject, 2–5 tags per book |
| **Merge rule** | Add Claude's tags to any existing ones on the book; never remove |
| **Distinguishability** | None — auto and manual tags are indistinguishable in schema and UI |
| **Failure behavior** | Silent degrade. A network failure or bad response leaves the book with whatever tags it already had; book creation is never blocked. |
| **Model** | `claude-opus-4-6` (the authoritative default from the claude-api skill) |
| **Client config** | `timeout=10, max_retries=0` — same fast-fail pattern as the recommendations fix |

## Non-goals

- No schema change. Tags remain a flat many-to-many; there is no `source` column distinguishing auto from manual, no "pending suggestion" state, no approval workflow.
- No per-book "suggest tags" button in the UI. The feature is entirely background; the user's only interaction is seeing the tag chips on the book detail page.
- No prompt caching. The stable prefix (system prompt + tag vocabulary) is ~300 tokens, below Opus 4.6's 4096-token cacheable-prefix minimum, so `cache_control` would silently no-op. Not worth the complexity.
- No batching in the backfill. Library sizes are small (~50 books); per-book calls at ~1s each are fast enough and keep error isolation clean.
- No automated tests for the backfill script. Same as the existing `backfill_covers.py` / `backfill_descriptions.py` — one-shot scripts verified by running them and checking DB state.

## Architecture

```
POST /books
  ↓
create_book(...)                       backend/app/routers/books.py
  ├─ persist book (phase 1)
  ├─ resolve cover                     services/cover_resolver.resolve_book_cover
  ├─ fetch description                 services/openlibrary.fetch_description
  └─ generate tags (NEW)               services/tag_generator.generate_book_tags
        └─ resolve + merge             services/tags.resolve_or_create_tags
```

One new service module, `backend/app/services/tag_generator.py`, owns everything Claude-facing for tagging. It exposes a single async function:

```python
async def generate_book_tags(
    *,
    title: str,
    author: str,
    description: str | None,
    existing_user_tags: list[str],
) -> list[str]:
    """Returns 2–5 normalized tag names, or [] on any failure."""
```

The module is isolated: it never touches the database, never knows about `Book` or `Tag` ORM models, and can be unit-tested with pure inputs. All persistence stays in the router and the backfill script, going through the existing `resolve_or_create_tags` helper.

## The Claude call

### Inputs

- Title, author, description (may be `None`), and the user's existing tag vocabulary as a `list[str]`.
- Description is critical for theme tags — title + author alone is enough for genre, but themes like `coming-of-age` or `desert` come from the blurb. The fetch runs *after* the description step in `create_book` so Claude sees the blurb we just pulled from Open Library.

### Prompt shape

**System prompt** (stable, ~250 tokens):

> You are a book classifier. Given a book's title, author, and description, produce a small set of concise tags covering its genre and main themes or subject matter.
>
> Hard constraints:
> - Return 2 to 5 tags total.
> - Include at least one genre tag (e.g. scifi, fantasy, mystery, literary, historical-fiction, nonfiction, memoir).
> - The remaining tags should describe themes or subject matter (e.g. politics, economics, coming-of-age, dystopia, space-opera, ww2).
> - Tag style: lowercased ASCII; short (1–2 words); hyphen-separated if multi-word; never include spaces, punctuation, or capitals.
> - Never produce meta or personal tags like `favorites`, `to-read`, `classic`, `recommended`.
> - STRONGLY prefer reusing tags from the user's existing vocabulary when any fit. Only invent a new tag when no existing tag fits.

**User message** (varies per book):

> The user's existing tag vocabulary: `["fantasy", "literary", "scifi", "favorites"]`
>
> Tag this book:
> - Title: Dune
> - Author: Frank Herbert
> - Description: Set on the desert planet Arrakis…

### Response format — structured output

Use `output_config.format` with a JSON schema instead of manual fence-stripping and regex parsing. This guarantees the response is a valid JSON object matching the schema:

```python
output_config={
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["tags"],
            "additionalProperties": False,
        },
    },
}
```

The Claude API's JSON schema subset does not support `minItems`/`maxItems`, so the "2–5 tags" rule is enforced in the prompt and clamped client-side in the normalizer.

### Client-side normalizer

Even with a schema-constrained response, we defensively normalize before accepting. Implemented as a private pure function in `tag_generator.py`:

```python
_META_TAG_BLACKLIST = {"favorites", "favourites", "to-read", "tbr", "read", "classic", "recommended", "wishlist"}

def _normalize_tags(raw: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        t = t.strip().lower()
        if not t:
            continue
        t = re.sub(r"\s+", "-", t)                # collapse whitespace to hyphens
        if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{0,29}", t):
            continue                              # reject punctuation / too long
        if t in _META_TAG_BLACKLIST:
            continue
        if t in seen:
            continue                              # dedupe preserving first occurrence
        seen.add(t)
        out.append(t)
    return out[:5]                                # hard cap
```

### Cost

Per-call: ~400 input tokens × $5/1M + ~30 output tokens × $25/1M ≈ **$0.003 per book**. A 50-book backfill is ~$0.15. Negligible.

## Integration: `create_book` wiring

After the existing description-fetch block in `backend/app/routers/books.py`, add a third opportunistic enrichment step:

```python
# Opportunistic tag generation via Claude.
try:
    from ..services.tag_generator import generate_book_tags
    existing = await load_user_tag_names(session, user.id)
    suggested = await generate_book_tags(
        title=book.title,
        author=book.author,
        description=book.description,
        existing_user_tags=existing,
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
```

Notes on the wiring:

- **Tag generation runs on every `POST /books`**, even when the user passes explicit `tag_names` in the payload. Claude's suggestions merge on top of user-provided tags. This follows the merge decision.
- **Vocabulary loader in `services/tags.py`** next to `resolve_or_create_tags`, not in `tag_generator.py`. Keeps DB queries in one place.
- **Commit + refresh after merging** is consistent with the existing cover/description enrichment steps — needed because `book.tags` is a relationship with async-lazy-load quirks.
- **`touch_library` after merging** because adding tags mutates the library (invalidates the recommendations cache), matching the pattern in the transition and update code paths.
- **Silent failure**: the outer `try/except Exception` catches anything the service might raise (API failures, bugs) so book creation is never blocked by tagging.

### New helper: `services/tags.py`

```python
async def load_user_tag_names(session: AsyncSession, user_id: UUID) -> list[str]:
    """All tag names owned by a user, alphabetized for determinism."""
    result = await session.execute(
        select(Tag.name).where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return [row[0] for row in result.all()]
```

Loads every tag the user has ever created, not only tags currently applied to books — if the user created a tag but hasn't applied it yet, Claude should still see it as a candidate to reuse. Alphabetized so the prompt is deterministic across calls (helps reproducibility when debugging and would help prompt caching if we ever hit the minimum-prefix threshold).

## Backfill script

New file: `backend/scripts/backfill_tags.py`. Mirrors the existing `backfill_covers.py` and `backfill_descriptions.py` scripts.

```python
async def main() -> int:
    async with SessionLocal() as session:
        users = await session.execute(select(User))
        for user in users.scalars().all():
            vocab = await load_user_tag_names(session, user.id)
            books = (await session.execute(
                select(Book)
                .where(Book.user_id == user.id)
                .options(selectinload(Book.tags))
            )).scalars().unique().all()

            print(f"[{user.username}] {len(books)} books, vocab={vocab}")
            added = 0
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

                new_tags = await resolve_or_create_tags(session, user.id, suggested)
                existing_ids = {t.id for t in book.tags}
                actually_new = [t for t in new_tags if t.id not in existing_ids]
                for t in actually_new:
                    book.tags.append(t)
                session.add(book)
                added += len(actually_new)
                names = [t.name for t in book.tags]
                print(f"  OK  {book.title} -> {names}")

            if added:
                await touch_library(user, session)
        await session.commit()
    return 0
```

Run with:

```
docker compose exec fastapi python scripts/backfill_tags.py
```

### Correctness notes

- **Vocabulary loaded once per user per run**, not per book. This means a new tag Claude invents on book #1 (e.g., `dystopia`) won't be visible as "existing" when Claude is called for book #2 in the same run. In practice the existing tags from the seed vocabulary carry most of the style signal, and rare drift (`dystopia` on one book, `dystopian` on another) is tolerable. Accepted trade-off vs. re-querying the DB after every book.
- **Idempotent on re-run** because merge is add-only. Re-running the script won't duplicate tags (`resolve_or_create_tags` returns existing rows by name). However, Claude is non-deterministic, so re-runs *may* add additional tags that didn't appear on the first run. This is documented in the script header.
- **Batched commit at the end of the whole run**, with a single `touch_library` call per user at the end of their batch. Fine for libraries of hundreds; for very large libraries (10,000+ books) we'd want periodic flush — flagged in the script header as a known limitation but not fixed preemptively (YAGNI).
- **Per-book `try/except Exception`** so one bad call never aborts the run. Matches the pattern in the cover and description backfills.

## Failure modes

All five failure classes degrade the same way: the book still exists, with whatever tags it already had.

| Failure | Where | Behavior |
|---|---|---|
| Anthropic API unreachable (current Docker state) | `AsyncAnthropic.messages.create` → `APITimeoutError` / `APIConnectionError` | `tag_generator` catches `anthropic.APIError`, logs warning, returns `[]`. |
| Auth / rate-limit / 5xx from Claude | Same | Same. Warning in logs names the concrete exception type. |
| Response normalized to empty list | Normalizer rejects everything | Returns `[]`. Logged at warning level with the raw response so prompt regressions are debuggable. |
| Response has >5 tags | Normalizer clamps | Silent, correct. |
| Response tags already on the book | Merge loop's `if t.id not in existing_ids` | Silent, correct — no duplicates. |

Nested defense-in-depth:

1. Inside `generate_book_tags`: `try/except anthropic.APIError` → log → return `[]`.
2. Inside `create_book`: outer `try/except Exception` around the service call, defensively catching non-SDK bugs so the router can never 500 on tag failures.
3. Inside `backfill_tags.py`: per-book `try/except Exception` with stderr log, continues to the next book.

Logging pattern copies `services/anthropic_recs.py`:

```python
logger = logging.getLogger(__name__)
# ...
logger.warning("claude tag generation failed for %s: %s: %s", title, type(exc).__name__, exc)
logger.warning("claude tag response failed normalization for %s: raw=%r", title, raw)
```

## Testing

One small unit test file for the pure normalizer function, plus additions to the existing smoke test for end-to-end coverage. No mocks, no new test infrastructure.

### Unit: `backend/tests/test_tag_normalize.py` (new file)

```python
from app.services.tag_generator import _normalize_tags

def test_lowercases_and_dedupes():
    assert _normalize_tags(["Fantasy", "fantasy", "FANTASY"]) == ["fantasy"]

def test_hyphens_collapse_whitespace():
    assert _normalize_tags(["coming of age"]) == ["coming-of-age"]

def test_rejects_punctuation_except_hyphen():
    assert _normalize_tags(["sci-fi", "sci_fi", "sci/fi"]) == ["sci-fi"]

def test_drops_meta_tags():
    assert _normalize_tags(["fantasy", "favorites", "to-read"]) == ["fantasy"]

def test_caps_at_five():
    assert len(_normalize_tags(["a", "b", "c", "d", "e", "f", "g"])) == 5

def test_rejects_too_long():
    assert _normalize_tags(["a" * 31]) == []

def test_rejects_empty_strings():
    assert _normalize_tags(["", " ", "fantasy"]) == ["fantasy"]

def test_preserves_order_of_first_occurrence():
    assert _normalize_tags(["scifi", "fantasy", "scifi"]) == ["scifi", "fantasy"]
```

Runs with plain `pytest backend/tests/test_tag_normalize.py`. No docker, no DB, no network.

### Integration: extension to `backend/tests/test_smoke.py`

Add after the existing book-creation block:

```python
# --- auto-tag: new books come back with Claude-generated tags if Anthropic
#     is reachable. If not, feature silently degrades — we just assert the
#     tags field is still a list.
r = await c.post(
    "/books",
    json={"title": "Dune", "author": "Frank Herbert"},
    headers=auth,
)
assert r.status_code == 201
dune = r.json()
assert isinstance(dune["tags"], list)
if dune["tags"]:
    tag_names = [t["name"] for t in dune["tags"]]
    for name in tag_names:
        assert name == name.lower()
        assert " " not in name
    assert len(tag_names) <= 5
```

The conditional assertion-if-reachable pattern matches how the existing smoke test handles the `/recommendations` endpoint — keeps the test runnable even when the current Docker/Anthropic networking issue is unresolved.

### Not tested

- **The Claude prompt text.** Not snapshot-tested. Prompt regressions show up as tag quality drops, not test failures.
- **`generate_book_tags` with mocked `AsyncAnthropic`.** Thin wrapper over a network call; mocks would be more code than the function itself.
- **`resolve_or_create_tags` or the merge loop in `create_book`.** Already exercised by existing book-creation paths; the merge loop is 4 lines of straightforward set-membership.
- **The backfill script.** Same as `backfill_covers.py` / `backfill_descriptions.py` — verified manually by running it and inspecting the database.

## Files touched

### New

- `backend/app/services/tag_generator.py` — the service module (Claude call + normalizer)
- `backend/scripts/backfill_tags.py` — the one-shot backfill script
- `backend/tests/test_tag_normalize.py` — unit tests for the normalizer

### Modified

- `backend/app/services/tags.py` — add `load_user_tag_names(session, user_id)` helper
- `backend/app/routers/books.py` — add the third opportunistic enrichment step in `create_book`
- `backend/tests/test_smoke.py` — extend with the Dune tag assertion block

No schema changes, no migrations, no frontend changes.

## End-to-end verification plan

1. **Unit**: `pytest backend/tests/test_tag_normalize.py` — all tests pass.
2. **Image build**: `docker compose up --build -d fastapi` — fastapi rebuilds cleanly with the new files.
3. **Manual smoke test**:
   - `POST /books {"title": "Dune", "author": "Frank Herbert"}` against the running stack.
   - Response includes a populated `tags` array (assuming Anthropic network is healthy).
   - Verify returned tag names look genre+theme shaped and lowercase.
4. **DB inspection**: `SELECT title, array_agg(t.name) FROM books b LEFT JOIN book_tags bt ON bt.book_id=b.id LEFT JOIN tags t ON t.id=bt.tag_id WHERE b.title='Dune' GROUP BY b.title;` — new tags present.
5. **Backfill**: `docker compose exec fastapi python scripts/backfill_tags.py`. Expect to see `OK` lines for most existing books with sensible tag lists; `!!` or `--` lines for books Claude couldn't tag. Check final DB state: the four existing user tags (`fantasy`, `literary`, `scifi`, `favorites`) are reused heavily in the output, and new tags that appear (e.g., `dystopia`, `coming-of-age`, `space-opera`) look reasonable and match the established style.
6. **Failure mode check**: even with the current Docker networking issue blocking the Anthropic API, confirm `POST /books` still returns 201 and books are created without tags — i.e., the feature degrades cleanly.
7. **Smoke test**: `BASE_URL=http://localhost:8001 python3 -m pytest backend/tests/test_smoke.py -v` — existing tests still pass, new Dune assertion passes.
