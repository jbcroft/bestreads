"""Claude-backed tag generator for books.

Given a book's metadata and the user's existing tag vocabulary, asks
Claude to produce 2-5 concise genre + theme tags. All failures degrade
silently to an empty list — tag generation must never block book
creation.
"""
from __future__ import annotations

import json
import logging
import re

import anthropic
from anthropic import AsyncAnthropic

from ..config import settings

logger = logging.getLogger(__name__)

# Tags that Claude must not produce (prompt tells it not to, but we
# defensively filter too in case it slips one through).
_META_TAG_BLACKLIST = {
    "favorites",
    "favourites",
    "to-read",
    "tbr",
    "read",
    "classic",
    "recommended",
    "wishlist",
}

# Valid tag shape: lowercased ASCII, starts with alnum, allows hyphens,
# total length 1-30 chars.
_TAG_RE = re.compile(r"[a-z0-9][a-z0-9\-]{0,29}")


_SYSTEM_PROMPT = (
    "You are a book classifier. Given a book's title, author, and description, "
    "produce a small set of concise tags covering its genre and main themes or "
    "subject matter.\n\n"
    "Respond with ONLY a JSON array of tag strings — no preamble, no "
    "explanation, no markdown code fences.\n\n"
    "Hard constraints:\n"
    "- Return 2 to 5 tags total.\n"
    "- Include at least one genre tag (e.g. scifi, fantasy, mystery, literary, "
    "historical-fiction, nonfiction, memoir).\n"
    "- The remaining tags should describe themes or subject matter "
    "(e.g. politics, economics, coming-of-age, dystopia, space-opera, ww2).\n"
    "- Tag style: lowercased ASCII; short (1-2 words); hyphen-separated if "
    "multi-word; never include spaces, punctuation, or capitals.\n"
    "- Never produce meta or personal tags like favorites, to-read, classic, "
    "recommended.\n"
    "- STRONGLY prefer reusing tags from the user's existing vocabulary when "
    "any fit. Only invent a new tag when no existing tag fits."
)


def _normalize_tags(raw: list) -> list[str]:
    """Clean and clamp a raw tag list from Claude into our style.

    - Lowercases
    - Collapses whitespace runs to hyphens
    - Rejects anything with punctuation other than hyphens
    - Rejects meta/personal tags (favorites, to-read, etc.)
    - Dedupes (preserving first-occurrence order)
    - Caps the result at 5 tags
    """
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        if not isinstance(t, str):
            continue
        t = t.strip().lower()
        if not t:
            continue
        t = re.sub(r"\s+", "-", t)
        if not _TAG_RE.fullmatch(t):
            continue
        if t in _META_TAG_BLACKLIST:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:5]


def _parse_tag_array(text: str) -> list[str]:
    """Parse Claude's response into a list of raw tag strings.

    Handles the common failure modes: markdown fences, leading/trailing
    whitespace, and responses that embed the JSON array inside other
    prose. Returns [] if nothing usable can be extracted.
    """
    if not text:
        return []
    cleaned = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: find the first [...] block and try that
        bracket_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if not bracket_match:
            return []
        try:
            data = json.loads(bracket_match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, list):
        return []
    return data


async def generate_book_tags(
    *,
    title: str,
    author: str,
    description: str | None,
    existing_user_tags: list[str],
) -> list[str]:
    """Return 2-5 normalized tags for a book, or [] on any failure.

    Never raises — all exceptions (API failures, parse errors, bad
    responses) are logged and swallowed, returning an empty list. The
    caller is responsible for persisting any tags it does receive.
    """
    if not settings.anthropic_api_key:
        return []

    client = AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        timeout=10.0,
        max_retries=0,
    )

    # Defensive coerce: callers are typed list[str] but this is the only
    # place in the never-raises function that could raise on bad input.
    vocab_json = json.dumps([str(t) for t in existing_user_tags])
    desc_line = (
        f"- Description: {description}"
        if description
        else "- Description: (none provided)"
    )
    user_message = (
        f"The user's existing tag vocabulary: {vocab_json}\n\n"
        f"Tag this book:\n"
        f"- Title: {title}\n"
        f"- Author: {author}\n"
        f"{desc_line}"
    )

    try:
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=200,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        logger.warning(
            "claude tag generation failed for %r: %s: %s",
            title,
            type(exc).__name__,
            exc,
        )
        return []

    raw_text = ""
    for block in message.content:
        if getattr(block, "type", None) == "text":
            raw_text += block.text

    raw_tags = _parse_tag_array(raw_text)
    normalized = _normalize_tags(raw_tags)
    if not normalized:
        logger.warning(
            "claude tag response failed normalization for %r: raw=%r",
            title,
            raw_text,
        )
    return normalized
