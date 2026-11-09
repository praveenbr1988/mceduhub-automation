"""Page objects: the ONLY place that knows about the site's locators and structure."""

from mceduhub.pages.ebook_reader_page import EbookReaderPage
from mceduhub.pages.library_page import LibraryPage
from mceduhub.pages.login_page import LoginPage
from mceduhub.pages.resource_page import ResourcePage

__all__ = ["LoginPage", "LibraryPage", "EbookReaderPage", "ResourcePage"]
