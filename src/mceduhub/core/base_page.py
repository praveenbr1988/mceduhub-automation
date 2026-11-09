"""BasePage: shared behaviour for all page objects.

Rule: Playwright's sync API only processes browser events while a Playwright call
is running, so waits must use `self.pause()` (page.wait_for_timeout), never time.sleep().
"""

from __future__ import annotations

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeout

from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import Settings


class BasePage:
    def __init__(self, page: Page, settings: Settings):
        self.page = page
        self.settings = settings
        self.log = get_logger(f"pages.{type(self).__name__}")

    def pause(self, seconds: float) -> None:
        self.page.wait_for_timeout(int(seconds * 1000))

    @staticmethod
    def is_visible(locator: Locator, timeout_s: float = 0) -> bool:
        """True if the element becomes visible within timeout_s (0 = check now)."""
        if timeout_s <= 0:
            try:
                return locator.first.count() > 0 and locator.first.is_visible()
            except PlaywrightTimeout:
                return False
        try:
            locator.first.wait_for(state="visible", timeout=timeout_s * 1000)
            return True
        except PlaywrightTimeout:
            return False

    def click_if_visible(self, locator: Locator, timeout_s: float = 0) -> bool:
        """Click an optional element (pop-ups etc.) if it shows up. Returns whether it was clicked."""
        if self.is_visible(locator, timeout_s):
            locator.first.click()
            return True
        return False
