"""Decide which resource files to download."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from mceduhub.models import ResourceFile


def normalize(text: str) -> str:
    """Case-insensitive comparison that treats a curly apostrophe (’) like a straight one (')."""
    return text.replace("’", "'").strip().lower()


def select_resource_files(
    files: Iterable[ResourceFile],
    sections: Sequence[str] = (),
    only_extensions: Sequence[str] = (),
    skip_names_containing: Sequence[str] = (),
) -> tuple[list[ResourceFile], list[tuple[ResourceFile, str]]]:
    """Split files into (selected, excluded-with-reason). An empty filter list means 'no filter'."""
    wanted_sections = {normalize(s) for s in sections}
    extensions = tuple(e.lower() for e in only_extensions)
    skip_words = [w.lower() for w in skip_names_containing]

    selected: list[ResourceFile] = []
    excluded: list[tuple[ResourceFile, str]] = []
    for f in files:
        name = f.name.lower()
        if wanted_sections and normalize(f.section) not in wanted_sections:
            excluded.append((f, f"section '{f.section}'"))
        elif extensions and not name.endswith(extensions):
            excluded.append((f, f"not {', '.join(extensions)}"))
        elif any(w in name for w in skip_words):
            excluded.append((f, "name filter"))
        else:
            selected.append(f)
    return selected, excluded
