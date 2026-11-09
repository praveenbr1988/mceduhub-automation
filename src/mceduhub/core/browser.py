"""Browser lifecycle: one persistent Chromium context per run (keeps the login session)."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright

from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import BrowserSettings

log = get_logger("browser")


class BrowserSession:
    """Context manager owning Playwright, the browser context and the main page.

    with BrowserSession(settings.browser, profile_dir) as session:
        session.page.goto(...)
    """

    def __init__(self, settings: BrowserSettings, profile_dir: Path):
        self.settings = settings
        self.profile_dir = profile_dir
        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        log.debug("Starting browser (headless=%s, profile=%s)", self.settings.headless, self.profile_dir)
        self._playwright = sync_playwright().start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                str(self.profile_dir),
                headless=self.settings.headless,
                viewport={"width": self.settings.viewport_width, "height": self.settings.viewport_height},
                device_scale_factor=self.settings.device_scale_factor,
                accept_downloads=True,
            )
            self.context.set_default_timeout(self.settings.default_timeout_s * 1000)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        except Exception:
            self._playwright.stop()
            raise
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self.context:
                self.context.close()
        finally:
            if self._playwright:
                self._playwright.stop()
            log.debug("Browser closed")
