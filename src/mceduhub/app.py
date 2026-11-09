"""Application entry points used by the CLI (and usable from other Python code)."""

from __future__ import annotations

from collections.abc import Iterable

from mceduhub.core.browser import BrowserSession
from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import Credentials, Settings
from mceduhub.models import BookResult
from mceduhub.pages.library_page import LibraryPage
from mceduhub.pages.login_page import LoginPage
from mceduhub.services.book_processor import BookProcessor

log = get_logger("app")


def _session(settings: Settings) -> BrowserSession:
    return BrowserSession(settings.browser, settings.resolve(settings.browser.user_data_dir))


def _login(session: BrowserSession, settings: Settings, credentials: Credentials) -> LibraryPage:
    return LoginPage(session.page, settings).open().login(credentials)


def process_books(settings: Settings, credentials: Credentials, books: Iterable[str]) -> list[BookResult]:
    books = list(books)
    results: list[BookResult] = []
    with _session(settings) as session:
        processor = BookProcessor(_login(session, settings, credentials), settings)
        for n, book in enumerate(books, 1):
            log.info("[%d/%d] %s", n, len(books), book)
            results.append(processor.process(book))
    return results


def list_books(settings: Settings, credentials: Credentials) -> list[str]:
    with _session(settings) as session:
        return _login(session, settings, credentials).book_titles()
