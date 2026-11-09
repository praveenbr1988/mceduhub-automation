"""Resolve a user-supplied book name to exactly one library title."""

from __future__ import annotations

from collections.abc import Iterable

from mceduhub.core.exceptions import AmbiguousBookError, BookNotFoundError


def match_title(query: str, titles: Iterable[str]) -> str:
    """Exact (case-insensitive) match wins; otherwise the query must be a substring of exactly one title."""
    q = query.strip().lower()
    unique = sorted(set(titles))
    exact = [t for t in unique if t.lower() == q]
    if exact:
        return exact[0]
    partial = [t for t in unique if q in t.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise BookNotFoundError(f"No book matches {query!r}. Run 'mceduhub list-books' to see titles.")
    raise AmbiguousBookError(f"{query!r} matches several books, be more specific: {partial}")
