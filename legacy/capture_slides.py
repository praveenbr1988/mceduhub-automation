"""Capture MCEduHub e-books page by page and save one PDF per book.

Usage:
    python capture_slides.py --books "Cambridge Primary English Student Book 4"
    python capture_slides.py --books "Book A" "Book B"
    python capture_slides.py --books-file books.txt
    python capture_slides.py                       # uses BOOKS in config.py
    python capture_slides.py --list-books          # print every book title in the library
Options:
    --headless        run the browser hidden
    --max-pages N     stop each book after N screenshots (handy for a quick test)
    --pdf-only        rebuild PDFs from already captured images (no browser)
    --keep-images     keep the page images after the PDF is built (deleted by default)
    --max-files N     download at most N files per resource book, e.g. Teacher's Guides (testing)
    --force           capture again even if the book's PDF already exists (skipped by default)

Books that open in a new tab with a list of files (Teacher's Guides) are downloaded
file by file into output/<book>/ instead of being captured as pages.
"""

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

import img2pdf
from dotenv import load_dotenv
from playwright.sync_api import Frame, Page, TimeoutError as PWTimeout, sync_playwright

import config

PROJECT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def safe_name(name: str) -> str:
    return re.sub(r"[^\w\-. ]", "_", name).strip() or "book"


def click_if_visible(locator, timeout_ms: int) -> bool:
    try:
        locator.first.wait_for(state="visible", timeout=timeout_ms)
        locator.first.click()
        return True
    except PWTimeout:
        return False


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"{name} is missing. Copy .env.example to .env and fill it in.")
    return value


# ---------------------------------------------------------------------------
# Login & library
# ---------------------------------------------------------------------------
def login(page: Page) -> None:
    print("Opening login page...")
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    user_box = page.get_by_role("textbox", name="User ID")
    try:
        user_box.wait_for(state="visible", timeout=10000)
    except PWTimeout:
        print("Already logged in (saved session).")
        return

    print("Logging in...")
    user_box.fill(env("PLATFORM_USERNAME"))
    school = page.get_by_role("combobox", name="School ID")
    school.fill(env("PLATFORM_SCHOOL_ID"))
    page.get_by_text(env("PLATFORM_SCHOOL_NAME"), exact=False).first.click()
    page.get_by_role("textbox", name="Password").fill(env("PLATFORM_PASSWORD"))
    page.get_by_role("button", name="Sign In").click()
    try:
        page.wait_for_url(lambda url: "lms_login" not in url.lower(), timeout=30000)
    except PWTimeout:
        sys.exit("Login failed - still on the login page. Check the details in .env.")
    click_if_visible(page.get_by_role("button", name="Later"), 8000)  # "update profile" style prompt
    print("Logged in.")


def library_titles(page: Page) -> list[str]:
    page.get_by_role("img").first.wait_for(state="visible", timeout=30000)
    page.wait_for_timeout(1500)
    return [t for t in page.locator("img[alt]").evaluate_all("els => els.map(e => e.alt.trim())") if t]


def go_to_library(page: Page, library_url: str) -> None:
    page.goto(library_url, wait_until="domcontentloaded")
    click_if_visible(page.get_by_role("button", name="Later"), 2000)


def find_book_cover(page: Page, book: str):
    titles = library_titles(page)
    exact = [t for t in titles if t.lower() == book.lower()]
    partial = [t for t in titles if book.lower() in t.lower()]
    matches = exact or partial
    unique = sorted(set(matches))
    if not unique:
        raise RuntimeError(f"Book not found. Use --list-books to see the exact titles.")
    if len(unique) > 1:
        raise RuntimeError(f"Name matches several books, be more specific: {unique}")
    return page.get_by_role("img", name=unique[0], exact=True).first, unique[0]


# ---------------------------------------------------------------------------
# Opening a book
# ---------------------------------------------------------------------------
def ebook_frame(page: Page) -> Frame | None:
    for f in page.frames:
        if config.EBOOK_FRAME_URL_PART in f.url:
            return f
    return None


def click_cover(page: Page, cover) -> Page | None:
    """Click a book cover. Returns the new tab if one opened (resource list), else None (e-book reader)."""
    try:
        with page.context.expect_page(timeout=config.NEW_TAB_WAIT * 1000) as new_tab:
            cover.click()
        tab = new_tab.value
        tab.wait_for_load_state("load")
        return tab
    except PWTimeout:
        return None


def open_book(page: Page) -> Frame:
    """Wait for the e-book reader (after the cover was clicked) and dismiss its pop-ups."""
    viewer = page.frame_locator(config.VIEWER_IFRAME)
    close_btn = viewer.get_by_role("button", name="Close")
    stay_btn = viewer.frame_locator(config.THEME_IFRAME).frame_locator("iframe").get_by_text("Stay on this page")

    # Pop-ups appear in varying order/timing; keep dismissing them until the reader is idle.
    deadline = time.time() + 60
    ready_since = None
    while time.time() < deadline:
        if close_btn.count() and close_btn.first.is_visible():
            close_btn.first.click()
            ready_since = None
        if stay_btn.count() and stay_btn.first.is_visible():
            stay_btn.first.click()
            ready_since = None
        ep = ebook_frame(page)
        if ep and ep.locator(config.NEXT_BUTTON).count() and ep.locator(config.NEXT_BUTTON).is_visible():
            ready_since = ready_since or time.time()
            if time.time() - ready_since > 3:   # reader visible and no pop-up for 3 s
                return ep
        page.wait_for_timeout(500)
    raise RuntimeError("E-book reader did not load (this item may not be an e-book).")


# ---------------------------------------------------------------------------
# Capturing
# ---------------------------------------------------------------------------
def is_disabled(ep: Frame, selector: str) -> bool:
    btn = ep.locator(selector)
    return btn.is_disabled() or "disabled" in (btn.get_attribute("class") or "").split()


def page_label(ep: Frame) -> str:
    try:
        return ep.locator(config.PAGE_INPUT).input_value(timeout=2000)
    except PWTimeout:
        return "?"


def wait_for_turn(page: Page, ep: Frame, before: str) -> None:
    """After clicking next/prev: wait for the page number to change and images to load."""
    deadline = time.time() + config.PAGE_LOAD_TIMEOUT
    while page_label(ep) == before and time.time() < deadline:
        page.wait_for_timeout(200)
    try:
        ep.wait_for_function(
            """sel => { const a = document.querySelector(sel);
                        return a && [...a.querySelectorAll('img')].every(i => i.complete); }""",
            arg=config.PAGE_AREA,
            timeout=config.PAGE_LOAD_TIMEOUT * 1000,
        )
    except PWTimeout:
        print("  (images still loading - capturing anyway)")
    page.wait_for_timeout(int(config.WAIT_AFTER_CLICK * 1000))


def rewind_to_start(page: Page, ep: Frame) -> None:
    turns = 0
    while not is_disabled(ep, config.PREV_BUTTON) and turns < config.MAX_PAGES:
        before = page_label(ep)
        ep.locator(config.PREV_BUTTON).click()
        deadline = time.time() + 5
        while page_label(ep) == before and time.time() < deadline:
            page.wait_for_timeout(100)
        turns += 1
    if turns:
        print(f"  Rewound {turns} spread(s) to the first page.")


def capture_book(page: Page, ep: Frame, out_dir: Path, max_pages: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("page_*.jpg"):
        old.unlink()

    ep.add_style_tag(content=f"{config.HIDE_ELEMENTS} {{ display: none !important; }}")
    rewind_to_start(page, ep)
    wait_for_turn(page, ep, before="")

    area = ep.locator(config.PAGE_AREA)
    files: list[Path] = []
    last_hash = None

    while len(files) < max_pages:
        page.mouse.move(5, 5)  # keep the cursor off the pages (no hover effects)
        path = out_dir / f"page_{len(files) + 1:04d}.jpg"
        data = area.screenshot(path=path, type="jpeg", quality=config.JPEG_QUALITY)
        digest = hashlib.md5(data).hexdigest()
        label = page_label(ep)
        if digest == last_hash:
            path.unlink()  # identical to previous capture - don't keep duplicates
        else:
            files.append(path)
            last_hash = digest
            print(f"  Captured {len(files):>3}  (page {label})")

        if is_disabled(ep, config.NEXT_BUTTON):
            print("  Reached the last page.")
            break
        ep.locator(config.NEXT_BUTTON).click()
        wait_for_turn(page, ep, before=label)
    else:
        print(f"  Stopped at the limit of {max_pages} captures.")
    return files


def build_pdf(images: list[Path], output: Path) -> None:
    if not images:
        raise RuntimeError("No images to put in the PDF.")
    output.write_bytes(img2pdf.convert([str(p) for p in images]))
    print(f"  PDF saved: {output.resolve()} ({len(images)} pages)")


def download_resources(tab: Page, out_dir: Path, max_files: int) -> tuple[int, int, int]:
    """Download every file listed on a resource page (e.g. Teacher's Guides).

    Returns (downloaded, skipped, failed). Finished links are recorded in
    out_dir/.downloaded.txt so an interrupted run can resume without re-downloading.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    done_file = out_dir / ".downloaded.txt"
    done = set(done_file.read_text(encoding="utf-8").splitlines()) if done_file.exists() else set()

    links = tab.frame_locator(config.RESOURCE_FRAME).locator(config.RESOURCE_LINK)
    links.first.wait_for(state="visible", timeout=30000)
    all_names = [t.strip() for t in links.all_inner_texts()]

    # Which section heading each link sits under: walk the page text in order; any text
    # that is not inside a link is a heading, and links take the most recent heading.
    sections = tab.frame_locator(config.RESOURCE_FRAME).locator("body").evaluate(
        """(body, linkSel) => {
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
        }""",
        config.RESOURCE_LINK,
    )
    norm = lambda s: s.replace("’", "'").strip().lower()  # treat curly ’ like '
    wanted = [norm(s) for s in config.RESOURCE_SECTIONS]
    items = [(i, n) for i, (n, s) in enumerate(zip(all_names, sections))
             if not wanted or norm(s) in wanted]
    print(f"  Resource page with {len(all_names)} files; {len(items)} in section(s) {config.RESOURCE_SECTIONS or 'ALL'}.")

    skip_words = [w.lower() for w in config.SKIP_FILES_CONTAINING]
    exts = tuple(e.lower() for e in config.ONLY_EXTENSIONS)
    downloaded = skipped = failed = 0
    names = all_names
    for i, name in items:
        if downloaded >= max_files:
            print(f"  Stopped at the limit of {max_files} files.")
            break
        if exts and not name.lower().endswith(exts):
            print(f"  [{i + 1}/{len(names)}] SKIPPED (not {', '.join(exts)}) {name}")
            continue
        if any(w in name.lower() for w in skip_words):
            print(f"  [{i + 1}/{len(names)}] SKIPPED (filter) {name}")
            continue
        if name in done:
            skipped += 1
            continue
        try:
            with tab.expect_download(timeout=config.DOWNLOAD_TIMEOUT * 1000) as dl:
                links.nth(i).click()
            d = dl.value
            target = out_dir / d.suggested_filename
            d.save_as(target)
            size_mb = target.stat().st_size / 1_048_576
            print(f"  [{i + 1}/{len(names)}] {d.suggested_filename}  ({size_mb:.1f} MB)")
            with done_file.open("a", encoding="utf-8") as f:
                f.write(name + "\n")
            downloaded += 1
        except Exception as e:
            print(f"  [{i + 1}/{len(names)}] FAILED {name}: {str(e).splitlines()[0]}")
            failed += 1
    if skipped:
        print(f"  Skipped {skipped} file(s) already downloaded earlier.")
    return downloaded, skipped, failed


def delete_images(image_dir: Path) -> None:
    """Remove a book's page images (only called after its PDF was written)."""
    for img in image_dir.glob("page_*.jpg"):
        img.unlink()
    try:
        image_dir.rmdir()  # only succeeds if the folder is now empty
    except OSError:
        pass
    print("  Deleted page images.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def get_books(args) -> list[str]:
    if args.books:
        return args.books
    if args.books_file:
        lines = Path(args.books_file).read_text(encoding="utf-8").splitlines()
        return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    return list(config.BOOKS)


def main():
    ap = argparse.ArgumentParser(description="Capture MCEduHub e-books into PDFs.")
    ap.add_argument("--books", nargs="+", metavar="NAME", help="book titles (quote titles with spaces)")
    ap.add_argument("--books-file", metavar="FILE", help="text file with one book title per line")
    ap.add_argument("--list-books", action="store_true", help="print all book titles in the library and exit")
    ap.add_argument("--headless", action="store_true", help="run the browser hidden")
    ap.add_argument("--max-pages", type=int, default=config.MAX_PAGES, help="max captures per book")
    ap.add_argument("--pdf-only", action="store_true", help="rebuild PDFs from captured images, no browser")
    ap.add_argument("--keep-images", action="store_true", help="keep the page images after the PDF is built")
    ap.add_argument("--max-files", type=int, default=10_000, help="max files downloaded per resource book (testing)")
    ap.add_argument("--force", action="store_true", help="capture again even if the book's PDF already exists")
    args = ap.parse_args()

    load_dotenv(PROJECT_DIR / ".env")
    out_root = PROJECT_DIR / config.OUTPUT_DIR
    books = get_books(args)
    if not books and not args.list_books:
        sys.exit("No books given. Use --books, --books-file, or fill BOOKS in config.py. "
                 "Run with --list-books to see the titles.")

    results: dict[str, str] = {}

    if args.pdf_only:
        for book in books:
            # Accept the full title or a unique part of it, like the capture does.
            dirs = [d for d in out_root.glob("*/") if safe_name(book).lower() in d.name.lower()]
            exact = [d for d in dirs if d.name.lower() == safe_name(book).lower()]
            folder = (exact or dirs)[0] if len(exact or dirs) == 1 else out_root / safe_name(book)
            images = sorted(folder.glob("page_*.jpg"))
            try:
                build_pdf(images, out_root / f"{folder.name}.pdf")
                results[book] = "OK"
            except Exception as e:
                results[book] = f"FAILED: {e}"
    else:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(PROJECT_DIR / config.USER_DATA_DIR),
                headless=args.headless or config.HEADLESS,
                viewport=config.VIEWPORT,
                device_scale_factor=config.DEVICE_SCALE_FACTOR,
            )
            page = context.pages[0] if context.pages else context.new_page()
            login(page)
            library_url = page.url

            if args.list_books:
                print("\nBooks in the library:")
                for t in library_titles(page):
                    print(f"  {t}")
                context.close()
                return

            for n, book in enumerate(books, 1):
                print(f"\n[{n}/{len(books)}] {book}")
                try:
                    go_to_library(page, library_url)
                    cover, title = find_book_cover(page, book)
                    if title != book:
                        print(f"  Matched: {title}")
                    pdf_path = out_root / f"{safe_name(title)}.pdf"
                    if pdf_path.exists() and not args.force:
                        print(f"  PDF already exists - skipping (use --force to capture again).")
                        results[book] = "SKIPPED (PDF already exists)"
                        continue
                    tab = click_cover(page, cover)
                    if tab:  # opened in a new tab -> list of downloadable files
                        try:
                            ok, skipped, failed = download_resources(tab, out_root / safe_name(title), args.max_files)
                        finally:
                            tab.close()
                        status = f"{ok} downloaded, {skipped} already had, {failed} failed"
                        results[book] = ("OK" if not failed else "PARTIAL") + f" ({status})"
                        continue

                    ep = open_book(page)
                    image_dir = out_root / safe_name(title)
                    images = capture_book(page, ep, image_dir, args.max_pages)
                    build_pdf(images, out_root / f"{safe_name(title)}.pdf")
                    results[book] = f"OK ({len(images)} pages)"
                    if not (args.keep_images or config.KEEP_IMAGES):
                        delete_images(image_dir)
                except Exception as e:
                    print(f"  ERROR: {e}")
                    results[book] = f"FAILED: {str(e).splitlines()[0]}"

            context.close()

    print("\nSummary")
    for book, status in results.items():
        print(f"  {book}: {status}")


if __name__ == "__main__":
    main()
