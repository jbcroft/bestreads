"""Claude-backed tag generator for books.

Given a book's metadata and the user's existing tag vocabulary, asks
Claude to produce 2-5 concise genre + theme tags. All failures degrade
silently to an empty list — tag generation must never block book
creation.
"""
from __future__ import annotations

import re

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
