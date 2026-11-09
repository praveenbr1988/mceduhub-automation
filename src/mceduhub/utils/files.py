"""File-system helpers."""

from __future__ import annotations

import re
from pathlib import Path


def safe_name(name: str) -> str:
    """Turn a book title into a safe file/folder name ("Teacher's Guide 1" -> "Teacher_s Guide 1")."""
    return re.sub(r"[^\w\-. ]", "_", name).strip() or "book"


class DownloadLedger:
    """Records finished downloads in a text file so interrupted runs can resume."""

    FILENAME = ".downloaded.txt"

    def __init__(self, folder: Path):
        self.path = folder / self.FILENAME
        self._done: set[str] = (
            set(self.path.read_text(encoding="utf-8").splitlines()) if self.path.exists() else set()
        )

    def __contains__(self, name: str) -> bool:
        return name in self._done

    def __len__(self) -> int:
        return len(self._done)

    def add(self, name: str) -> None:
        if name in self._done:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(name + "\n")
        self._done.add(name)


def remove_files(folder: Path, pattern: str) -> int:
    """Delete files matching pattern in folder, then the folder itself if empty. Returns count deleted."""
    count = 0
    for f in folder.glob(pattern):
        f.unlink()
        count += 1
    try:
        folder.rmdir()
    except OSError:
        pass  # not empty or doesn't exist
    return count
