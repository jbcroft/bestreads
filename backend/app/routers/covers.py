from __future__ import annotations

import os
import uuid as uuidlib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..db import get_session
from ..deps import get_auth_user
from ..models import Book, User
from ..schemas import BookRead
from ..services.serializers import book_to_read

router = APIRouter(tags=["covers"])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/books/{book_id}/cover", response_model=BookRead)
async def upload_cover(
    book_id: UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_auth_user),
    session: AsyncSession = Depends(get_session),
) -> BookRead:
    result = await session.execute(
        select(Book)
        .where(Book.id == book_id, Book.user_id == user.id)
        .options(selectinload(Book.tags))
    )
    book = result.scalar_one_or_none()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"Unsupported extension: {ext}")

    os.makedirs(settings.covers_dir, exist_ok=True)
    filename = f"{uuidlib.uuid4().hex}{ext}"
    out_path = Path(settings.covers_dir) / filename
    data = await file.read()
    out_path.write_bytes(data)

    book.cover_image_path = filename
    session.add(book)
    await session.commit()
    await session.refresh(book, attribute_names=["tags"])
    return book_to_read(book)


@router.get("/covers/{filename}")
async def serve_cover(filename: str) -> FileResponse:
    # Prevent traversal
    safe = Path(filename).name
    path = Path(settings.covers_dir) / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Cover not found")
    return FileResponse(str(path))
