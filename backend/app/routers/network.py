from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, User
from ..schemas import NetworkResponse
from ..services.segmentation import BookData, build_network_graph
from ..services.serializers import cover_url_for

router = APIRouter(prefix="/network", tags=["network"])


@router.get("", response_model=NetworkResponse)
async def get_network(
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> NetworkResponse:
    result = await session.execute(
        select(Book)
        .where(Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    books = result.scalars().unique().all()

    book_data = [
        BookData(
            id=str(b.id),
            title=b.title,
            author=b.author,
            description=b.description,
            tags=[t.name for t in b.tags],
            rating=b.rating,
            cover_url=cover_url_for(b.cover_image_path),
        )
        for b in books
    ]

    return build_network_graph(book_data)
