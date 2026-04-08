from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, BookStatus, User
from ..schemas import SearchResponse
from ..services.serializers import book_to_read

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1),
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    # Use PostgreSQL FTS against the generated search_vector column on books.
    ts_query = func.plainto_tsquery("english", q)
    stmt = (
        select(Book)
        .where(Book.user_id == user.id)
        .where(Book.search_vector.op("@@")(ts_query))
        .options(selectinload(Book.tags))
        .order_by(Book.date_added.desc())
    )
    result = await session.execute(stmt)
    books = result.scalars().unique().all()

    grouped: dict[str, list] = {
        "want_to_read": [],
        "reading": [],
        "finished": [],
    }
    for b in books:
        key = b.status.value if hasattr(b.status, "value") else str(b.status)
        grouped[key].append(book_to_read(b))

    return SearchResponse(**grouped)
