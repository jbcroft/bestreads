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
