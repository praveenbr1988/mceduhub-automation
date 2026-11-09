"""Login page: User ID + School ID (autocomplete) + Password."""

from __future__ import annotations

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from mceduhub.core.base_page import BasePage
from mceduhub.core.exceptions import LoginError
from mceduhub.core.settings import Credentials, Settings
from mceduhub.pages.library_page import LibraryPage


class LoginPage(BasePage):
    LOGIN_URL_MARKER = "lms_login"

    def __init__(self, page: Page, settings: Settings):
        super().__init__(page, settings)
        self.user_id_input = page.get_by_role("textbox", name="User ID")
        self.school_id_input = page.get_by_role("combobox", name="School ID")
        self.password_input = page.get_by_role("textbox", name="Password")
        self.sign_in_button = page.get_by_role("button", name="Sign In")
        self.later_button = page.get_by_role("button", name="Later")  # post-login prompt

    def school_option(self, school_name: str):
        return self.page.get_by_text(school_name).first

    def _select_school(self, credentials: Credentials, attempts: int = 3) -> None:
        """Type the School ID and pick the school from the autocomplete list.

        The list sometimes doesn't appear after a plain fill(), so retry by typing key by key.
        """
        option = self.school_option(credentials.school_name)
        for attempt in range(1, attempts + 1):
            self.school_id_input.fill("")
            if attempt == 1:
                self.school_id_input.fill(credentials.school_id)
            else:
                self.school_id_input.press_sequentially(credentials.school_id, delay=120)
            if self.is_visible(option, timeout_s=8):
                option.click()
                return
            self.log.debug("School list not shown (attempt %d), retrying", attempt)
        raise LoginError(f"School '{credentials.school_name}' did not appear in the School ID list.")

    def open(self) -> "LoginPage":
        self.page.goto(self.settings.site.login_url, wait_until="domcontentloaded")
        return self

    def login(self, credentials: Credentials) -> LibraryPage:
        """Log in (or reuse the saved session) and return the library page."""
        if not self.is_visible(self.user_id_input, timeout_s=10):
            self.log.info("Already logged in (saved session).")
        else:
            self.log.info("Logging in as %s", credentials.username)
            self.user_id_input.fill(credentials.username)
            self._select_school(credentials)
            self.password_input.fill(credentials.password)
            self.sign_in_button.click()
            try:
                self.page.wait_for_url(lambda url: self.LOGIN_URL_MARKER not in url.lower(), timeout=30_000)
            except PlaywrightTimeout as e:
                raise LoginError("Still on the login page - check the details in .env.") from e
            self.click_if_visible(self.later_button, timeout_s=8)
            self.log.info("Logged in.")
        return LibraryPage(self.page, self.settings, home_url=self.page.url)
