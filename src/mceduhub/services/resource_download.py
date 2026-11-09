"""Download the selected files from a resource page (Teacher's Guides)."""

from __future__ import annotations

from mceduhub.core.logging_config import get_logger
from mceduhub.core.settings import Settings
from mceduhub.models import BookResult, BookType, Status
from mceduhub.pages.resource_page import ResourcePage
from mceduhub.utils.files import DownloadLedger, safe_name
from mceduhub.utils.filters import select_resource_files


class ResourceDownloadService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.log = get_logger("services.resources")

    def download_all(self, page: ResourcePage, title: str, query: str) -> BookResult:
        cfg = self.settings.resources
        dest = self.settings.output_dir / safe_name(title)
        ledger = DownloadLedger(dest)

        files = page.list_files()
        selected, excluded = select_resource_files(
            files, cfg.sections, cfg.only_extensions, cfg.skip_names_containing
        )
        self.log.info("Resource page: %d files, %d selected.", len(files), len(selected))
        for f, reason in excluded:
            self.log.debug("Excluded (%s): %s", reason, f.name)

        downloaded = already = failed = 0
        for f in selected:
            if downloaded >= cfg.max_files:
                self.log.warning("Stopped at the limit of %d files.", cfg.max_files)
                break
            if f.name in ledger:
                already += 1
                continue
            try:
                path = page.download(f, dest)
                ledger.add(f.name)
                downloaded += 1
                self.log.info("Downloaded %s (%.1f MB)", path.name, path.stat().st_size / 1_048_576)
            except Exception as e:  # one bad file must not stop the rest
                failed += 1
                self.log.error("Failed %s: %s", f.name, str(e).splitlines()[0])

        if already:
            self.log.info("Skipped %d file(s) already downloaded earlier.", already)
        status = Status.PARTIAL if failed else Status.OK
        detail = f"{downloaded} downloaded, {already} already had, {failed} failed"
        return BookResult(query, title, BookType.RESOURCES, status, detail, dest)
