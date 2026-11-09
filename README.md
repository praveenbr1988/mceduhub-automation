# MCEduHub Automation Framework

A Playwright + Python **Page Object Model** framework for the MCEduHub platform. It:

| Book type | What happens when the cover is clicked | What the framework does | Output |
|---|---|---|---|
| **E-books** (Student Books, Workbooks) | The page-flip reader opens | Captures every two-page spread, front cover to back cover, into one PDF | `output/<Book title>.pdf` |
| **Resource books** (Teacher's Guides) | A new tab opens with a list of files | Downloads the selected files (default: ZIPs in "Teacher's Resources", no audio) | `output/<Book title>/` |

The book type is detected automatically, so one book list can mix both.

> Use this only for content your account is licensed to access, and in line with the platform's terms.

---

## Contents

1. [Quick start](#quick-start)
2. [Architecture](#architecture)
3. [Project structure](#project-structure)
4. [Configuration](#configuration)
5. [Command-line usage](#command-line-usage)
6. [Testing](#testing)
7. [Extending the framework](#extending-the-framework)
8. [Troubleshooting](#troubleshooting)

---

## Quick start

```bash
cd /home/praveen/Documents/Projects/McMillan
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"            # installs the package + the `mceduhub` command
playwright install chromium

cp .env.example .env               # then fill in your login details
mceduhub list-books --headless     # check login works
mceduhub run --books "Student Book 4"
```

**VS Code:** `Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv/bin/python`.

---

## Architecture

The code is split into layers. Each layer only uses the layers below it:

```
 cli.py            ← parses arguments, prints the summary, sets the exit code
   │
 app.py            ← entry points: process_books(), list_books()
   │
 services/         ← WORKFLOWS: what to do with a book
   │   BookProcessor            find → skip if done → open → dispatch
   │   EbookCaptureService      rewind → capture spreads → PDF
   │   ResourceDownloadService  list → filter → download → ledger
   │
 pages/            ← PAGE OBJECTS: how to interact with each screen (all locators live here)
   │   LoginPage → LibraryPage → EbookReaderPage | ResourcePage
   │
 core/             ← INFRASTRUCTURE: BrowserSession, BasePage, Settings, logging, exceptions
 utils/            ← PURE HELPERS (no browser): title matching, file filters, PDF, ledger
```

**Design rules**

- **Locators exist only in `pages/`.** If the site changes, only the matching page object needs editing.
- **Page objects return page objects.** `LoginPage.login()` returns a `LibraryPage`, and `LibraryPage.open_book()` returns an `EbookReaderPage` or a `ResourcePage`. That's how type detection works.
- **Services hold the business logic** and never contain selectors.
- **Utilities are pure functions**, so they're unit-tested without a browser.
- **Settings are typed dataclasses** loaded from `config/settings.toml`. Misspelled settings are rejected with a clear error.
- **Secrets live only in `.env`.** The password is hidden in logs and in the `repr`.
- **Errors are typed** (`LoginError`, `BookNotFoundError`, …). One failed book doesn't stop the others, and the run ends with a summary and a non-zero exit code if anything failed.
- **Waits are always Playwright waits** (`BasePage.pause()`), never `time.sleep()`. Sleep blocks Playwright from processing browser events in sync mode.

**Reliability features**

- **Already-captured e-books are skipped.** If the PDF exists, the book is skipped unless you pass `--force`.
- **Downloads resume.** Each Teacher's Guide folder has a `.downloaded.txt` ledger, so an interrupted run carries on where it stopped.
- **The reader is kept on the cover.** It sometimes jumps to the last-read page after opening; the framework detects this and rewinds again.
- **Slow page loads don't end a book early.** The reader greys out the Previous and Next buttons while a spread loads, so "first page" and "last page" are only trusted once the spread has loaded and the button stays disabled.
- **Each run writes a log.** You get concise console output plus a detailed log file in `logs/run_YYYYmmdd_HHMMSS.log`.

---

## Project structure

```
McMillan/
├── pyproject.toml              # package metadata, dependencies, pytest config, `mceduhub` command
├── config/
│   └── settings.toml           # all non-secret settings
├── .env / .env.example         # credentials (git-ignored)
├── books.txt                   # optional book list for --books-file
├── src/mceduhub/
│   ├── cli.py                  # command-line interface
│   ├── app.py                  # high-level entry points
│   ├── models.py               # BookResult, ResourceFile, BookType, Status
│   ├── core/
│   │   ├── settings.py         # typed Settings + Credentials
│   │   ├── browser.py          # BrowserSession (persistent Chromium context)
│   │   ├── base_page.py        # BasePage: pause, is_visible, click_if_visible
│   │   ├── logging_config.py   # console + file logging
│   │   └── exceptions.py       # AutomationError hierarchy
│   ├── pages/
│   │   ├── login_page.py
│   │   ├── library_page.py
│   │   ├── ebook_reader_page.py
│   │   └── resource_page.py
│   ├── services/
│   │   ├── book_processor.py
│   │   ├── ebook_capture.py
│   │   └── resource_download.py
│   └── utils/
│       ├── matching.py         # book name → library title
│       ├── filters.py          # which resource files to download
│       ├── files.py            # safe_name, DownloadLedger, remove_files
│       └── pdf.py              # images → PDF (img2pdf)
├── tests/
│   ├── unit/                   # fast, no browser (run by default)
│   └── integration/            # live site smoke test (opt-in)
├── legacy/                     # the original single-file script (for reference; safe to delete)
├── output/                     # PDFs and downloads (git-ignored)
└── logs/                       # run logs (git-ignored)
```

---

## Configuration

### Credentials: `.env`

| Variable | Description |
|---|---|
| `PLATFORM_USERNAME` | User ID |
| `PLATFORM_PASSWORD` | Password |
| `PLATFORM_SCHOOL_ID` | School ID typed into the School ID box |
| `PLATFORM_SCHOOL_NAME` | School name as shown in the School ID dropdown |

### Settings: `config/settings.toml`

Settings you leave out use the built-in defaults. Command-line options override the file.

| Section | Setting | Default | Meaning |
|---|---|---|---|
| (top) | `books` | `[]` | Default book list |
| `[browser]` | `headless` | `false` | Hide the browser |
| | `device_scale_factor` | `2.0` | `2` = sharp captures; `1` = about 4× smaller PDFs |
| | `viewport_width` / `viewport_height` | `1600` / `900` | Window size |
| | `default_timeout_s` | `30` | Default Playwright timeout |
| `[ebook]` | `wait_after_turn_s` | `0.8` | Settle time after a page loads |
| | `page_load_timeout_s` | `15` | Maximum wait for a page turn |
| | `reader_ready_timeout_s` | `60` | Maximum wait for the reader to open |
| | `max_pages` | `600` | Safety cap of spreads per book |
| | `jpeg_quality` | `90` | Capture quality |
| | `keep_images` | `false` | Keep page JPEGs after the PDF is built |
| `[resources]` | `sections` | `["Teacher's Resources"]` | Only download links under these headings (`[]` = all) |
| | `only_extensions` | `[".zip"]` | Only these file types (`[]` = any) |
| | `skip_names_containing` | `["audio"]` | Skip files whose names contain these words |
| | `download_start_timeout_s` | `60` | Give up on a file if its download doesn't start in time |
| | `new_tab_wait_s` | `6` | How long to wait for a new tab after clicking a cover |
| `[output]` | `output_dir` | `"output"` | Where results go |
| | `log_dir` | `"logs"` | Where run logs go |
| | `force` | `false` | Re-capture e-books whose PDF already exists |

Use another settings file for a single run with `--config path/to/other.toml`.

---

## Command-line usage

After `pip install -e .`, the `mceduhub` command is available. `python -m mceduhub` works too.

```bash
mceduhub list-books                                   # all titles in the library
mceduhub run --books "Student Book 4" "Teacher's Guide 4"
mceduhub run --books-file books.txt --headless
mceduhub run --books "Workbook 2" --force             # re-capture an existing PDF
mceduhub build-pdf --books "Workbook 2"               # rebuild from kept images (no browser)
```

| Option | Commands | Description |
|---|---|---|
| `--books NAME …` | run, build-pdf | Titles, or unique parts of titles (`"Student Book 4"`) |
| `--books-file FILE` | run, build-pdf | One title per line; `#` lines are ignored |
| `--headless` | all | Hidden browser |
| `--output-dir DIR` | all | Write results somewhere else (useful for test runs) |
| `--config FILE` | all | Use a different settings file |
| `-v, --verbose` | all | Show debug messages on the console |
| `--force` | run | Re-capture e-books even if the PDF exists |
| `--keep-images` | run | Keep page JPEGs (needed for `build-pdf`) |
| `--max-pages N` | run | Stop each e-book after N spreads (testing) |
| `--max-files N` | run | Stop each resource book after N files (testing) |

**Exit codes:** `0` = all OK or skipped, `1` = at least one book failed, `2` = configuration error, `130` = interrupted.

**Tip for test runs:** always add `--output-dir /tmp/test-output` together with `--max-pages`/`--max-files`, so that partial test results never mix with your real `output/` folder.

---

## Testing

```bash
pytest                 # unit tests (fast, no browser, no network)
pytest -m live         # live smoke test: logs in and lists books (needs .env)
pytest -v tests/unit/test_filters.py
```

What the unit tests cover:

| Test file | Covers |
|---|---|
| `test_matching.py` | Exact, partial, ambiguous and missing book names |
| `test_filters.py` | Section, extension and audio filters; curly apostrophes |
| `test_files.py` | Safe file names (compatible with existing output), the resume ledger, image cleanup |
| `test_pdf.py` | One PDF page per image; empty input rejected |
| `test_settings.py` | TOML overrides, misspelled keys, the shipped config file, credentials, password masking |

---

## Extending the framework

**The site changed a locator:** edit the constant or locator in the matching file in `pages/`. Nothing else changes.

**A new screen:** add `pages/<name>_page.py` with a class that inherits `BasePage` and keeps its locators in `__init__` or as class constants. Have the page that leads to it return an instance of it.

**A new workflow** (e.g. exporting a table of contents): add a service in `services/` that takes page objects, and call it from `BookProcessor` or a new function in `app.py`. Then add a CLI subcommand in `cli.py`.

**Using it from Python:**

```python
from mceduhub.app import process_books
from mceduhub.core.settings import Settings, Credentials

results = process_books(Settings.load(), Credentials.from_env(), ["Student Book 4"])
for r in results:
    print(r.status, r.title, r.output)
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Missing credentials: …` | Create `.env` from `.env.example`. |
| `Unknown setting(s) in [section]` | There's a typo in `config/settings.toml`; the error lists the valid names. |
| `LoginError` | Check the details in `.env`. The school name must match the dropdown text. |
| `No book matches …` | Run `mceduhub list-books` and copy the title. |
| `… matches several books` | Use a longer part of the title. |
| `E-book reader did not load in time` | The site was slow; try again or increase `reader_ready_timeout_s`. |
| Book shows `SKIPPED` | Its PDF already exists; use `--force` to capture it again. |
| Resource files `FAILED` | Run the same command again; finished files are skipped. |
| Pages look half-drawn | Increase `wait_after_turn_s`. |
| PDFs too large | Set `device_scale_factor = 1.0` and/or `jpeg_quality = 75`. |
| `mceduhub: command not found` | Activate the venv: `source .venv/bin/activate`. |
| Anything else | Open the newest file in `logs/`; it has full details and tracebacks. |
