import pytest

from mceduhub.models import ResourceFile


@pytest.fixture
def teacher_guide_files() -> list[ResourceFile]:
    """A realistic slice of a Teacher's Guide resource page."""
    rows = [
        ("1 Cambridge PRI ENG TG4 TG.zip", "Teacher's Resources"),
        ("5 Cambridge PRI ENG SB4 WB4 Suggested Answers.zip", "Teacher's Resources"),
        ("6 Cambridge PRI ENG S4 Exam Papers.zip", "Teacher's Resources"),
        ("Cambridge PRI ENG SB4 Audio.zip", "Teacher's Resources"),
        ("Cambridge PRI ENG TG4 BLM.pdf", "1 Teacher's Guide"),
        ("Cambridge PRI ENG TG4 SOW.docx", "1 Teacher's Guide"),
        ("Cambridge PRI ENG TG4 Unit1.pptx", "2 Term 1"),
    ]
    return [ResourceFile(i, name, section) for i, (name, section) in enumerate(rows)]
