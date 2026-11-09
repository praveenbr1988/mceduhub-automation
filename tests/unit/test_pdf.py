import re

import pytest
from PIL import Image

from mceduhub.utils.pdf import build_pdf


def make_jpeg(path, color):
    Image.new("RGB", (200, 120), color).save(path, "JPEG")
    return path


def test_build_pdf_one_page_per_image(tmp_path):
    images = [make_jpeg(tmp_path / f"p{i}.jpg", c) for i, c in enumerate(["red", "green", "blue"])]
    pdf = build_pdf(images, tmp_path / "out" / "book.pdf")
    data = pdf.read_bytes()
    assert data.startswith(b"%PDF")
    # every page object has "/Type /Page" (the page tree is "/Type /Pages")
    assert len(re.findall(rb"/Type\s*/Page(?!s)", data)) == 3


def test_build_pdf_rejects_empty_list(tmp_path):
    with pytest.raises(ValueError):
        build_pdf([], tmp_path / "x.pdf")
