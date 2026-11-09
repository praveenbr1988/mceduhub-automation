"""Domain models shared across pages, services and the CLI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class BookType(str, Enum):
    EBOOK = "e-book"            # page-flip reader -> captured to PDF
    RESOURCES = "resources"     # opens a file list in a new tab -> files downloaded
    UNKNOWN = "unknown"


class Status(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ResourceFile:
    index: int      # position among the page's download links
    name: str       # link text, e.g. "1 Cambridge PRI ENG TG4 TG.zip"
    section: str    # heading the link sits under, e.g. "Teacher's Resources"


@dataclass
class BookResult:
    query: str
    title: str
    book_type: BookType
    status: Status
    detail: str = ""
    output: Path | None = None
