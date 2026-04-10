from __future__ import annotations

from datetime import datetime, timezone

from ..models import Book, BookStatus


def apply_status_transition(book: Book, new_status: BookStatus) -> None:
    """Apply side-effects of a status change per spec rules."""
    now = datetime.now(timezone.utc)
    if new_status == BookStatus.reading:
        if book.started_at is None:
            book.started_at = now
        book.finished_at = None
    elif new_status == BookStatus.finished:
        if book.started_at is None:
            book.started_at = now
        book.finished_at = now
    elif new_status == BookStatus.want_to_read:
        book.started_at = None
        book.finished_at = None
    elif new_status == BookStatus.dnf:
        if book.started_at is None:
            book.started_at = now
        book.finished_at = None
    book.status = new_status


async def touch_library(user, session) -> None:
    """Mark the user's library as mutated — invalidates recommendations cache."""
    from datetime import datetime, timezone

    user.library_updated_at = datetime.now(timezone.utc)
    session.add(user)
