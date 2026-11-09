"""Library (home) page: grid of book covers."""

from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from mceduhub.core.base_page import BasePage
from mceduhub.core.settings import Settings
from mceduhub.pages.ebook_reader_page import EbookReaderPage
from mceduhub.pages.resource_page import ResourcePage


class LibraryPage(BasePage):
    def __init__(self, page: Page, settings: Settings, home_url: str):
        super().__init__(page, settings)
        self.home_url = home_url
        self.later_button = page.get_by_role("button", name="Later")
        # Only book thumbnails - the page also has hidden app-download images (Windows, iOS, ...)
        self.covers = page.locator(".thumbnail-image-wrapper img[alt]")

    def cover(self, title: str):
        return self.page.get_by_role("img", name=title, exact=True).first

    def open(self) -> "LibraryPage":
        self.page.goto(self.home_url, wait_until="domcontentloaded")
        self.click_if_visible(self.later_button, timeout_s=2)
        return self

    def book_titles(self) -> list[str]:
        self.covers.first.wait_for(state="visible", timeout=30_000)
        self.pause(1.5)  # covers render progressively
        alts = self.covers.evaluate_all("els => els.map(e => e.alt.trim())")
        return [a for a in alts if a]

    def open_book(self, title: str) -> EbookReaderPage | ResourcePage:
        """Click a cover. Resource books open a new tab; e-books open the in-page reader."""
        try:
            with self.page.context.expect_page(timeout=self.settings.resources.new_tab_wait_s * 1000) as tab_info:
                self.cover(title).click()
            tab = tab_info.value
            tab.wait_for_load_state("load")
            self.log.debug("Opened in a new tab -> resource page")
            return ResourcePage(tab, self.settings)
        except PlaywrightTimeout:
            self.log.debug("No new tab -> e-book reader")
            return EbookReaderPage(self.page, self.settings).wait_until_ready()
