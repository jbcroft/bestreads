from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import BookStatus

BookStatusLiteral = Literal["want_to_read", "reading", "finished"]

# ---------- Users / Auth ----------


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    avatar_url: str | None = None
    created_at: datetime


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ApiKeyMasked(BaseModel):
    api_key: str | None


class ApiKeyPlain(BaseModel):
    api_key: str


# ---------- Tags ----------


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class BookTagsUpdate(BaseModel):
    tag_names: list[str] = Field(default_factory=list)


# ---------- Books ----------


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    author: str = Field(min_length=1, max_length=512)
    isbn: str | None = None
    page_count: int | None = None
    description: str | None = None
    status: BookStatusLiteral = "want_to_read"
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
    tag_names: list[str] | None = None
    cover_image_path: str | None = None  # pre-downloaded filename (from /lookup)
    cover_url: str | None = None  # remote URL to fetch opportunistically


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    isbn: str | None = None
    page_count: int | None = None
    description: str | None = None
    status: BookStatusLiteral | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    author: str
    isbn: str | None
    page_count: int | None
    description: str | None
    cover_url: str | None = None
    status: BookStatusLiteral
    rating: int | None
    notes: str | None
    date_added: datetime
    started_at: datetime | None
    finished_at: datetime | None
    tags: list[TagRead] = Field(default_factory=list)


# ---------- Stats / Search ----------


class MonthCount(BaseModel):
    month: str
    count: int


class TagCount(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total_books: int
    by_status: dict[str, int]
    finished_this_year: int
    avg_rating: float | None
    top_tags: list[TagCount]
    finished_by_month: list[MonthCount]


class SearchResponse(BaseModel):
    want_to_read: list[BookRead]
    reading: list[BookRead]
    finished: list[BookRead]


# ---------- Lookup ----------


class LookupResult(BaseModel):
    title: str
    author: str
    isbn: str | None = None
    page_count: int | None = None
    description: str | None = None
    cover_image_path: str | None = None
    cover_url: str | None = None


class LookupSearchItem(BaseModel):
    title: str
    author: str
    year: int | None = None
    isbn: str | None = None
    cover_url: str | None = None


# ---------- Recommendations ----------


class RecommendationItem(BaseModel):
    title: str
    author: str
    reason: str


class RecommendationsResponse(BaseModel):
    available: bool
    message: str | None = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    generated_at: datetime | None = None
