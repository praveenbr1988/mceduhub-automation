"""Capture an open e-book, spread by spread, into a single PDF."""

from __future__ import annotations

import hashlib
from pathlib import Path

from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import Settings
from mceduhub.models import BookResult, BookType, Status
from mceduhub.pages.ebook_reader_page import EbookReaderPage
from mceduhub.utils.files import remove_files, safe_name
from mceduhub.utils.pdf import build_pdf

IMAGE_PATTERN = "page_*.jpg"


class EbookCaptureService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.log = get_logger("services.ebook")

    def pdf_path(self, title: str) -> Path:
        return self.settings.output_dir / f"{safe_name(title)}.pdf"

    def image_dir(self, title: str) -> Path:
        return self.settings.output_dir / safe_name(title)

    def capture(self, reader: EbookReaderPage, title: str, query: str) -> BookResult:
        cfg = self.settings.ebook
        image_dir = self.image_dir(title)
        image_dir.mkdir(parents=True, exist_ok=True)
        remove_files(image_dir, IMAGE_PATTERN)
        image_dir.mkdir(parents=True, exist_ok=True)  # remove_files may delete the empty folder

        reader.hide_overlays()
        turns = reader.go_to_front_cover(max_turns=cfg.max_pages)
        if turns:
            self.log.info("Rewound %d spread(s) to the front cover.", turns)

        images: list[Path] = []
        last_hash: str | None = None
        while len(images) < cfg.max_pages:
            path = image_dir / f"page_{len(images) + 1:04d}.jpg"
            digest = hashlib.md5(reader.capture_spread(path, cfg.jpeg_quality)).hexdigest()
            if digest == last_hash:
                path.unlink()  # identical to the previous spread
            else:
                images.append(path)
                last_hash = digest
                self.log.info("Captured %3d  (page %s)", len(images), reader.page_label())
            if reader.is_last_page():
                self.log.info("Reached the last page.")
                break
            reader.next_page()
        else:
            self.log.warning("Stopped at the limit of %d captures.", cfg.max_pages)

        pdf = build_pdf(images, self.pdf_path(title))
        self.log.info("PDF saved: %s (%d pages)", pdf, len(images))
        if not cfg.keep_images:
            remove_files(image_dir, IMAGE_PATTERN)
            self.log.debug("Deleted page images in %s", image_dir)
        return BookResult(query, title, BookType.EBOOK, Status.OK, f"{len(images)} pages", pdf)
