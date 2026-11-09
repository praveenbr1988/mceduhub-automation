"""Settings for capturing MCEduHub e-books.

Login details live in .env (see .env.example), not here.
You normally only need to edit BOOKS (or pass --books on the command line).
"""

# ---------------------------------------------------------------------------
# Books to capture (used when --books / --books-file is not given).
# Use the exact title shown under the book cover in the library.
# ---------------------------------------------------------------------------
BOOKS = [
    # "Cambridge Primary English Student Book 4",
    # "Cambridge Primary English Workbook 4",
]

# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------
LOGIN_URL = "https://www.mceduhub.com/Lead/Login/lms_login.aspx?REASON=denied_empty"

# Content player structure (found by inspecting the site - change only if the site changes)
VIEWER_IFRAME = "#iframe_viewer"           # outer content-player iframe
THEME_IFRAME = "#iframeUseTheme"            # second-level iframe ("Stay on this page" prompt lives below it)
EBOOK_FRAME_URL_PART = "lms-ebook"          # the e-book reader iframe's URL contains this
NEXT_BUTTON = "#next_page"
PREV_BUTTON = "#prev_page"
PAGE_INPUT = "#page_input"                  # page number box in the reader toolbar
PAGE_AREA = "#layout-page"                  # the book pages (what gets screenshotted)

# Resource books (Teacher's Guides) open in a NEW TAB listing downloadable files
NEW_TAB_WAIT = 6                            # seconds to wait for a new tab after clicking a cover
RESOURCE_FRAME = "#ebook-frame"             # iframe holding the file list
RESOURCE_LINK = "a.link-download"           # each downloadable file link
DOWNLOAD_TIMEOUT = 60                       # max seconds for a download to START after clicking
                                            # (if nothing starts, the file is marked FAILED and skipped)

# Only download links under these section headings (case-insensitive, exact heading text).
# The top section "Teacher's Resources" holds the ZIPs; the other sections
# ("1 Teacher's Guide", "2 Term 1", ...) contain the same files unzipped.
# Empty list [] = all sections.
RESOURCE_SECTIONS = ["Teacher's Resources"]

# Only download files with these extensions (case-insensitive). [] = any type.
ONLY_EXTENSIONS = [".zip"]

# Files whose name contains any of these words are NOT downloaded (case-insensitive).
# e.g. ["audio"] skips "Cambridge PRI ENG SB1 Audio.zip". Add more, e.g. [".pptx", "docx"].
# Empty list [] = download everything.
SKIP_FILES_CONTAINING = ["audio"]

# Elements hidden before capture so they don't appear on the pages
HIDE_ELEMENTS = "#epub-bookmark-left, #epub-bookmark-right, .tooltiptext"

# ---------------------------------------------------------------------------
# Timing & limits
# ---------------------------------------------------------------------------
WAIT_AFTER_CLICK = 0.8      # extra seconds after a page has loaded, before the screenshot
PAGE_LOAD_TIMEOUT = 15      # max seconds to wait for a page turn / images to load
MAX_PAGES = 600             # safety cap of screenshots per book

# ---------------------------------------------------------------------------
# Browser & output
# ---------------------------------------------------------------------------
VIEWPORT = {"width": 1600, "height": 900}
DEVICE_SCALE_FACTOR = 2     # 2 = sharper images (2x pixels). 1 = smaller files.
JPEG_QUALITY = 90           # 1-100
HEADLESS = False            # True = hidden browser (or use --headless)
USER_DATA_DIR = ".browser-profile"
OUTPUT_DIR = "output"       # output/<book>/page_0001.jpg ... and output/<book>.pdf
KEEP_IMAGES = False         # False = delete a book's page images once its PDF is saved (or use --keep-images)
