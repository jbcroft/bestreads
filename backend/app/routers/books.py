from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, BookStatus, Tag, User, book_tags
from ..schemas import (
    BookCreate,
    BookRead,
    BookTagsUpdate,
    BookUpdate,
)
from ..services.serializers import book_to_read
from ..services.tags import resolve_or_create_tags
from ..services.transitions import apply_status_transition, touch_library

router = APIRouter(prefix="/books", tags=["books"])


async def _load_book(session: AsyncSession, book_id: UUID, user: User) -> Book:
    result = await session.execute(
        select(Book)
        .where(Book.id == book_id, Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


SortField = Literal["date_added", "title", "author", "rating", "finished_at"]


@router.get("", response_model=list[BookRead])
async def list_books(
    status_filter: BookStatus | None = Query(default=None, alias="status"),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
    min_rating: int | None = Query(default=None, ge=1, le=5),
    sort: SortField = Query(default="date_added"),
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> list[BookRead]:
    stmt = (
        select(Book)
        .where(Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    if status_filter is not None:
        stmt = stmt.where(Book.status == status_filter)
    if min_rating is not None:
        stmt = stmt.where(Book.rating >= min_rating)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            (Book.title.ilike(pattern))
            | (Book.author.ilike(pattern))
            | (Book.notes.ilike(pattern))
        )
    if tag:
        stmt = (
            stmt.join(book_tags, book_tags.c.book_id == Book.id)
            .join(Tag, Tag.id == book_tags.c.tag_id)
            .where(Tag.name == tag, Tag.user_id == user.id)
        )

    sort_col = {
        "date_added": Book.date_added.desc(),
        "title": Book.title.asc(),
        "author": Book.author.asc(),
        "rating": Book.rating.desc().nulls_last(),
        "finished_at": Book.finished_at.desc().nulls_last(),
    }[sort]
    stmt = stmt.order_by(sort_col)

    result = await session.execute(stmt)
    books = result.scalars().unique().all()
    return [book_to_read(b) for b in books]


@router.get("/{book_id}", response_model=BookRead)
async def get_book(
    book_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    return book_to_read(book)


@router.post("", response_model=BookRead, status_code=status.HTTP_201_CREATED)
async def create_book(
    payload: BookCreate,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = Book(
        user_id=user.id,
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        page_count=payload.page_count,
        description=payload.description,
        status=BookStatus(payload.status),
        rating=payload.rating,
        notes=payload.notes,
        cover_image_path=payload.cover_image_path,
    )
    # Apply transition side-effects so started_at/finished_at are coherent
    apply_status_transition(book, BookStatus(payload.status))

    # Resolve tags BEFORE adding the book to the session so we can set the
    # collection on the transient instance (assigning to .tags on a persistent
    # instance would trigger a sync lazy-load under async.)
    tag_list: list[Tag] = []
    if payload.tag_names:
        tag_list = await resolve_or_create_tags(session, user.id, payload.tag_names)
    book.tags = tag_list

    session.add(book)
    await touch_library(user, session)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])

    # Opportunistic cover download if ISBN provided and no cover yet
    if book.isbn and not book.cover_image_path:
        try:
            from ..services.openlibrary import download_cover

            local = await download_cover(book.isbn)
            if local:
                book.cover_image_path = local
                session.add(book)
                await session.commit()
                await session.refresh(book, attribute_names=["tags"])
        except Exception:
            pass

    return book_to_read(book)


@router.patch("/{book_id}", response_model=BookRead)
async def update_book(
    book_id: UUID,
    payload: BookUpdate,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    data = payload.model_dump(exclude_unset=True)

    touched_library = False

    for field, value in data.items():
        if field == "status" and value is not None:
            apply_status_transition(book, BookStatus(value))
            touched_library = True
        else:
            setattr(book, field, value)
            if field == "rating":
                touched_library = True

    if touched_library:
        await touch_library(user, session)

    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    book = await _load_book(session, book_id, user)
    await session.delete(book)
    await touch_library(user, session)
    await session.commit()


# ---------- Status transitions ----------


@router.post("/{book_id}/start", response_model=BookRead)
async def start_book(
    book_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    apply_status_transition(book, BookStatus.reading)
    await touch_library(user, session)
    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)


@router.post("/{book_id}/finish", response_model=BookRead)
async def finish_book(
    book_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    apply_status_transition(book, BookStatus.finished)
    await touch_library(user, session)
    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)


@router.post("/{book_id}/reset", response_model=BookRead)
async def reset_book(
    book_id: UUID,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    apply_status_transition(book, BookStatus.want_to_read)
    await touch_library(user, session)
    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)


# ---------- Book tags (replace set) ----------


@router.patch("/{book_id}/tags", response_model=BookRead)
async def set_book_tags(
    book_id: UUID,
    payload: BookTagsUpdate,
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    book = await _load_book(session, book_id, user)
    tags = await resolve_or_create_tags(session, user.id, payload.tag_names)
    book.tags = tags
    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)
