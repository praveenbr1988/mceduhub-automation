"""Resource page (Teacher's Guides): a new tab listing downloadable files under section headings."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from mceduhub.core.base_page import BasePage
from mceduhub.core.settings import Settings
from mceduhub.models import ResourceFile

# Walks the page text in document order: any text outside a download link is a heading;
# each link is tagged with the most recent heading.
_LINK_SECTIONS_JS = """(body, linkSel) => {
    const links = new Set(body.querySelectorAll(linkSel));
    const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
    let heading = "", out = new Map();
    while (walker.nextNode()) {
        const n = walker.currentNode, text = n.textContent.trim();
        if (!text) continue;
        const link = n.parentElement.closest(linkSel);
        if (link && links.has(link)) { if (!out.has(link)) out.set(link, heading); }
        else heading = text;
    }
    return [...body.querySelectorAll(linkSel)].map(a => out.get(a) || "");
}"""


class ResourcePage(BasePage):
    CONTENT_IFRAME = "#ebook-frame"
    DOWNLOAD_LINK = "a.link-download"

    def __init__(self, page: Page, settings: Settings):
        super().__init__(page, settings)
        self.content = page.frame_locator(self.CONTENT_IFRAME)
        self.download_links = self.content.locator(self.DOWNLOAD_LINK)

    def list_files(self) -> list[ResourceFile]:
        self.download_links.first.wait_for(state="visible", timeout=30_000)
        names = [t.strip() for t in self.download_links.all_inner_texts()]
        sections = self.content.locator("body").evaluate(_LINK_SECTIONS_JS, self.DOWNLOAD_LINK)
        return [ResourceFile(index=i, name=n, section=s) for i, (n, s) in enumerate(zip(names, sections))]

    def download(self, file: ResourceFile, dest_dir: Path) -> Path:
        """Click a file link and save the download under its original filename."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        timeout_ms = self.settings.resources.download_start_timeout_s * 1000
        with self.page.expect_download(timeout=timeout_ms) as download_info:
            self.download_links.nth(file.index).click()
        download = download_info.value
        target = dest_dir / download.suggested_filename
        download.save_as(target)  # waits for the download to finish
        return target

    def close(self) -> None:
        self.page.close()
