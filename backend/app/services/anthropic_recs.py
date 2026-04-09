from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from ..config import settings
from ..models import Book

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a well-read, thoughtful literary advisor. "
    "Given a reader's library, suggest books they will likely love. "
    "Respond with ONLY a JSON array — no preamble, no explanation, "
    "no markdown fences. Each element must have exactly these keys: "
    '"title", "author", "reason". The "reason" is one sentence (<=200 chars) '
    "that explains the fit based on the reader's taste. "
    "Do not recommend books already in the reader's library."
)


def build_library_summary(books: list[Book]) -> str:
    lines: list[str] = []
    for b in books:
        status = b.status.value if hasattr(b.status, "value") else str(b.status)
        rating = f"rating {b.rating}" if b.rating else "unrated"
        tag_names = [t.name for t in b.tags] if b.tags else []
        tags = f"tags: {', '.join(tag_names)}" if tag_names else "no tags"
        lines.append(f"- {b.title} by {b.author} [{status}, {rating}, {tags}]")
    return "\n".join(lines) if lines else "(empty library)"


def _strip_fences(text: str) -> str:
    # Handles ```json ... ``` or ``` ... ```
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text.strip(), re.DOTALL)
    if m:
        return m.group(1)
    return text.strip()


def _parse_recommendations(text: str) -> list[dict[str, str]]:
    cleaned = _strip_fences(text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find a JSON array embedded in the text
        m = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    out: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        author = str(item.get("author", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if title and author and reason:
            out.append({"title": title, "author": author, "reason": reason})
    return out


async def generate_recommendations(
    books: list[Book],
    *,
    count: int = 3,
    mood: str | None = None,
    tag_filter: str | None = None,
) -> list[dict[str, str]]:
    if not settings.anthropic_api_key:
        return []

    # Fail fast rather than hanging the frontend on the SDK's default 10-minute
    # timeout (and its 2 automatic retries) when the network path to
    # api.anthropic.com is unhealthy. ~10s total worst case.
    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=10.0,
        max_retries=0,
    )
    summary = build_library_summary(books)
    constraints: list[str] = []
    if mood:
        constraints.append(f"The reader is currently in the mood for: {mood}.")
    if tag_filter:
        constraints.append(
            f"Prioritize books that fit this tag/genre: {tag_filter}."
        )
    constraints_text = ("\n".join(constraints) + "\n") if constraints else ""

    user_message = (
        f"Here is the reader's library:\n\n{summary}\n\n"
        f"{constraints_text}"
        f"Suggest exactly {count} book(s). "
        f"Return a JSON array of {count} objects with keys title, author, reason."
    )

    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        # Any SDK-level failure (timeout, connection, auth, rate limit, 5xx)
        # degrades to "no recommendations" rather than a 500 from the router.
        logger.warning("anthropic request failed: %s: %s", type(exc).__name__, exc)
        return []

    text_parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    raw = "\n".join(text_parts)
    return _parse_recommendations(raw)[:count]
