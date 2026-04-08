from __future__ import annotations

from ..config import settings
from ..models import Book
from ..schemas import BookRead, TagRead


def cover_url_for(cover_image_path: str | None) -> str | None:
    if not cover_image_path:
        return None
    # cover_image_path is a bare filename relative to covers_dir
    return f"{settings.covers_url_prefix}/{cover_image_path}"


def book_to_read(book: Book) -> BookRead:
    return BookRead(
        id=book.id,
        title=book.title,
        author=book.author,
        isbn=book.isbn,
        page_count=book.page_count,
        description=book.description,
        cover_url=cover_url_for(book.cover_image_path),
        status=book.status.value if hasattr(book.status, "value") else str(book.status),
        rating=book.rating,
        notes=book.notes,
        date_added=book.date_added,
        started_at=book.started_at,
        finished_at=book.finished_at,
        tags=[TagRead(id=t.id, name=t.name) for t in book.tags],
    )
