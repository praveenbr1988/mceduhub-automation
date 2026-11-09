"""Command-line interface.

    mceduhub run --books "Student Book 4" "Teacher's Guide 3"
    mceduhub run --books-file books.txt --headless
    mceduhub list-books
    mceduhub build-pdf --books "Student Book 4"
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from dotenv import load_dotenv

from mceduhub import __version__
from mceduhub.app import list_books, process_books
from mceduhub.core.exceptions import AutomationError
from mceduhub.core.logging_config import get_logger, setup_logging
from mceduhub.core.settings import PROJECT_ROOT, Credentials, Settings
from mceduhub.models import BookResult, Status
from mceduhub.services.ebook_capture import IMAGE_PATTERN
from mceduhub.utils.matching import match_title
from mceduhub.utils.pdf import build_pdf

log = get_logger("cli")


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, help="settings file (default: config/settings.toml)")
    common.add_argument("--headless", action="store_true", help="run the browser hidden")
    common.add_argument("--output-dir", help="where PDFs/files are written (default from settings)")
    common.add_argument("-v", "--verbose", action="store_true", help="show debug messages on the console")

    books = argparse.ArgumentParser(add_help=False)
    books.add_argument("--books", nargs="+", metavar="NAME", help="book titles or unique parts of titles")
    books.add_argument("--books-file", type=Path, metavar="FILE", help="text file, one title per line (# = comment)")

    p = argparse.ArgumentParser(prog="mceduhub", description="MCEduHub e-book capture and resource download.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", parents=[common, books], help="capture e-books / download resources")
    run.add_argument("--force", action="store_true", help="re-capture e-books whose PDF already exists")
    run.add_argument("--max-pages", type=int, help="max spreads per e-book (testing)")
    run.add_argument("--max-files", type=int, help="max files per resource book (testing)")
    run.add_argument("--keep-images", action="store_true", help="keep page images after building the PDF")

    sub.add_parser("list-books", parents=[common], help="print every title in the library")
    sub.add_parser("build-pdf", parents=[common, books], help="rebuild PDFs from kept page images (no browser)")
    return p


def _apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    if args.headless:
        settings.browser = replace(settings.browser, headless=True)
    if args.output_dir:
        settings.output = replace(settings.output, output_dir=args.output_dir)
    if getattr(args, "force", False):
        settings.output = replace(settings.output, force=True)
    if getattr(args, "max_pages", None):
        settings.ebook = replace(settings.ebook, max_pages=args.max_pages)
    if getattr(args, "keep_images", False):
        settings.ebook = replace(settings.ebook, keep_images=True)
    if getattr(args, "max_files", None) is not None:
        settings.resources = replace(settings.resources, max_files=args.max_files)
    return settings


def _book_list(args: argparse.Namespace, settings: Settings) -> list[str]:
    if args.books:
        return args.books
    if args.books_file:
        lines = args.books_file.read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    return list(settings.books)


def _print_summary(results: list[BookResult]) -> None:
    if not results:
        return
    width = max(len(r.title) for r in results)
    log.info("Summary")
    for r in results:
        log.info("  %-8s %-*s  %s", r.status.value, width, r.title, r.detail)


def _cmd_build_pdf(settings: Settings, books: list[str]) -> list[BookResult]:
    from mceduhub.models import BookType

    out = settings.output_dir
    folders = {d.name: d for d in out.iterdir() if d.is_dir()} if out.exists() else {}
    results = []
    for book in books:
        try:
            name = match_title(book.replace("'", "_"), folders)
            images = sorted(folders[name].glob(IMAGE_PATTERN))
            pdf = build_pdf(images, out / f"{name}.pdf")
            log.info("PDF saved: %s (%d pages)", pdf, len(images))
            results.append(BookResult(book, name, BookType.EBOOK, Status.OK, f"{len(images)} pages", pdf))
        except (AutomationError, ValueError) as e:
            log.error("%s: %s", book, e)
            results.append(BookResult(book, book, BookType.EBOOK, Status.FAILED, str(e)))
    return results


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    load_dotenv(PROJECT_ROOT / ".env")
    try:
        settings = _apply_overrides(Settings.load(args.config), args)
        log_file = setup_logging(settings.resolve(settings.output.log_dir), args.verbose)
        log.debug("Log file: %s", log_file)

        if args.command == "list-books":
            for title in list_books(settings, Credentials.from_env()):
                print(title)
            return 0

        books = _book_list(args, settings)
        if not books:
            log.error("No books given. Use --books, --books-file, or 'books' in config/settings.toml.")
            return 2

        if args.command == "build-pdf":
            results = _cmd_build_pdf(settings, books)
        else:
            results = process_books(settings, Credentials.from_env(), books)

        _print_summary(results)
        log.info("Full log: %s", log_file)
        return 1 if any(r.status is Status.FAILED for r in results) else 0

    except AutomationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nInterrupted. Finished books/files are kept; run again to resume.", file=sys.stderr)
        return 130
    except Exception as e:  # unexpected: short message on screen, full traceback in the log file
        log.exception("Unexpected error")
        print(f"ERROR: {str(e).splitlines()[0]} (details in the log file under logs/)", file=sys.stderr)
        return 1
