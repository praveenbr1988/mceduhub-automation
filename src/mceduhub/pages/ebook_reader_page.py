"""E-book reader (page-flip viewer, three iframes deep).

main page
└── #iframe_viewer                 ("Close" pop-up)
    └── #iframeUseTheme
        └── iframe                 ("Stay on this page" prompt)
            └── lms-ebook.mceapps.com reader frame
                 #layout-page  (the two-page spread)
                 #next_page / #prev_page  (class "disabled" at the ends)
                 #page_input   (page label)
"""

from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Frame, Page, TimeoutError as PlaywrightTimeout

from mceduhub.core.base_page import BasePage
from mceduhub.core.exceptions import ReaderNotReadyError
from mceduhub.core.settings import Settings


class EbookReaderPage(BasePage):
    VIEWER_IFRAME = "#iframe_viewer"
    THEME_IFRAME = "#iframeUseTheme"
    READER_FRAME_URL_PART = "lms-ebook"
    NEXT_BUTTON = "#next_page"
    PREV_BUTTON = "#prev_page"
    PAGE_LABEL_INPUT = "#page_input"
    PAGE_AREA = "#layout-page"
    OVERLAYS = "#epub-bookmark-left, #epub-bookmark-right, .tooltiptext"

    def __init__(self, page: Page, settings: Settings):
        super().__init__(page, settings)
        viewer = page.frame_locator(self.VIEWER_IFRAME)
        self.close_popup_button = viewer.get_by_role("button", name="Close")
        self.stay_on_page_button = (
            viewer.frame_locator(self.THEME_IFRAME).frame_locator("iframe").get_by_text("Stay on this page")
        )
        self._frame: Frame | None = None

    # ---- frame access -----------------------------------------------------
    def _find_reader_frame(self) -> Frame | None:
        return next((f for f in self.page.frames if self.READER_FRAME_URL_PART in f.url), None)

    @property
    def frame(self) -> Frame:
        if self._frame is None or self._frame.is_detached():
            self._frame = self._find_reader_frame()
            if self._frame is None:
                raise ReaderNotReadyError("E-book reader frame not found.")
        return self._frame

    # ---- loading ----------------------------------------------------------
    def wait_until_ready(self) -> "EbookReaderPage":
        """Dismiss pop-ups (they appear in varying order) until the reader is idle for 3 s."""
        deadline = time.time() + self.settings.ebook.reader_ready_timeout_s
        ready_since: float | None = None
        while time.time() < deadline:
            if self.click_if_visible(self.close_popup_button) or self.click_if_visible(self.stay_on_page_button):
                ready_since = None
            frame = self._find_reader_frame()
            if frame and self.is_visible(frame.locator(self.NEXT_BUTTON)):
                ready_since = ready_since or time.time()
                if time.time() - ready_since > 3:
                    self._frame = frame
                    return self
            self.pause(0.5)
        raise ReaderNotReadyError("E-book reader did not load in time.")

    def hide_overlays(self) -> None:
        """Hide bookmark ribbons and tooltips so they don't appear in captures."""
        self.frame.add_style_tag(content=f"{self.OVERLAYS} {{ display: none !important; }}")

    # ---- state ------------------------------------------------------------
    def _is_disabled(self, selector: str) -> bool:
        btn = self.frame.locator(selector)
        return btn.is_disabled() or "disabled" in (btn.get_attribute("class") or "").split()

    def _confirmed_disabled(self, selector: str, settle_s: float = 1.5) -> bool:
        """The reader greys out both buttons while a spread is loading, so a single
        'disabled' reading is not trustworthy. Wait for the spread to load, then
        require the button to stay disabled for settle_s."""
        self._wait_for_images()
        if not self._is_disabled(selector):
            return False
        self.pause(settle_s)
        self._wait_for_images()
        return self._is_disabled(selector)

    def is_first_page(self) -> bool:
        return self._confirmed_disabled(self.PREV_BUTTON)

    def is_last_page(self) -> bool:
        return self._confirmed_disabled(self.NEXT_BUTTON)

    def page_label(self) -> str:
        try:
            return self.frame.locator(self.PAGE_LABEL_INPUT).input_value(timeout=2000)
        except PlaywrightTimeout:
            return "?"

    # ---- navigation -------------------------------------------------------
    def _spread_signature(self) -> str:
        """Page label + image sources of the current spread. Changes on every page turn,
        even between unnumbered spreads (cover / inside cover all show '-')."""
        try:
            srcs = self.frame.locator(self.PAGE_AREA).evaluate(
                "a => [...a.querySelectorAll('img')].map(i => i.currentSrc || i.src).join('|')"
            )
        except PlaywrightTimeout:
            srcs = ""
        return f"{self.page_label()}#{srcs}"

    def _wait_for_turn(self, before: str, timeout_s: float) -> None:
        deadline = time.time() + timeout_s
        while self._spread_signature() == before and time.time() < deadline:
            self.pause(0.15)

    def _wait_for_images(self) -> bool:
        """Wait until every image in the current spread has loaded. Returns False on timeout."""
        try:
            self.frame.wait_for_function(
                """sel => { const a = document.querySelector(sel);
                            return a && [...a.querySelectorAll('img')].every(i => i.complete); }""",
                arg=self.PAGE_AREA,
                timeout=self.settings.ebook.page_load_timeout_s * 1000,
            )
            return True
        except PlaywrightTimeout:
            return False

    def wait_for_page_render(self) -> None:
        """Wait until the spread has loaded, then a short settle delay."""
        if not self._wait_for_images():
            self.log.warning("Images still loading on page %s - capturing anyway", self.page_label())
        self.pause(self.settings.ebook.wait_after_turn_s)

    def next_page(self) -> None:
        before = self._spread_signature()
        self.frame.locator(self.NEXT_BUTTON).click()
        self._wait_for_turn(before, self.settings.ebook.page_load_timeout_s)
        self.wait_for_page_render()

    def go_to_front_cover(self, max_turns: int, attempts: int = 3) -> int:
        """Rewind to the cover and make sure the reader stays there.

        The reader may jump to the last-read page a few seconds after opening,
        so after rewinding we wait and verify, rewinding again if it moved.
        """
        total = 0
        for attempt in range(1, attempts + 1):
            total += self.rewind_to_start(max_turns)
            self.pause(2.0)
            if self.is_first_page():
                return total
            self.log.warning("Reader moved to page %s after rewinding - rewinding again (%d)",
                             self.page_label(), attempt)
        raise ReaderNotReadyError("Could not keep the reader on the front cover.")

    def rewind_to_start(self, max_turns: int) -> int:
        """Go back to the front cover. Returns the number of spreads turned."""
        turns = 0
        while turns < max_turns and not self.is_first_page():
            before = self._spread_signature()
            self.frame.locator(self.PREV_BUTTON).click()
            self._wait_for_turn(before, self.settings.ebook.page_load_timeout_s)
            turns += 1
        self.wait_for_page_render()
        return turns

    # ---- capture ----------------------------------------------------------
    def capture_spread(self, path: Path, jpeg_quality: int) -> bytes:
        """Screenshot only the book pages (no toolbars) to a JPEG file."""
        self.page.mouse.move(5, 5)  # keep the cursor off the pages
        return self.frame.locator(self.PAGE_AREA).screenshot(path=path, type="jpeg", quality=jpeg_quality)
