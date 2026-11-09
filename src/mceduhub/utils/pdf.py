"""Build PDFs from captured page images."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import img2pdf


def build_pdf(images: Sequence[Path], output: Path) -> Path:
    """Write images (in order) into one PDF, one image per page.

    img2pdf embeds JPEGs without re-encoding: lossless and low memory even for 100+ large pages.
    """
    if not images:
        raise ValueError("No images to put in the PDF.")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(img2pdf.convert([str(p) for p in images]))
    return output
