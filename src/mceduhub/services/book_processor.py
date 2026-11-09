"""Orchestrates one book end to end: find it, skip if done, open it, dispatch to the right service."""

from __future__ import annotations

from mceduhub.core.exceptions import AutomationError
from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import Settings
from mceduhub.models import BookResult, BookType, Status
from mceduhub.pages.library_page import LibraryPage
from mceduhub.pages.resource_page import ResourcePage
from mceduhub.services.ebook_capture import EbookCaptureService
from mceduhub.services.resource_download import ResourceDownloadService
from mceduhub.utils.matching import match_title


class BookProcessor:
    def __init__(self, library: LibraryPage, settings: Settings):
        self.library = library
        self.settings = settings
        self.ebooks = EbookCaptureService(settings)
        self.resources = ResourceDownloadService(settings)
        self.log = get_logger("services.processor")

    def process(self, query: str) -> BookResult:
        title = query
        try:
            self.library.open()
            title = match_title(query, self.library.book_titles())
            if title != query:
                self.log.info("Matched: %s", title)

            pdf = self.ebooks.pdf_path(title)
            if pdf.exists() and not self.settings.output.force:
                self.log.info("PDF already exists - skipping (use --force to capture again).")
                return BookResult(query, title, BookType.EBOOK, Status.SKIPPED, "PDF already exists", pdf)

            view = self.library.open_book(title)
            if isinstance(view, ResourcePage):
                try:
                    return self.resources.download_all(view, title, query)
                finally:
                    view.close()
            return self.ebooks.capture(view, title, query)

        except AutomationError as e:
            self.log.error("%s", e)
            return BookResult(query, title, BookType.UNKNOWN, Status.FAILED, str(e))
        except Exception as e:  # unexpected: keep the full traceback in the log file
            self.log.exception("Unexpected error")
            return BookResult(query, title, BookType.UNKNOWN, Status.FAILED, str(e).splitlines()[0])
