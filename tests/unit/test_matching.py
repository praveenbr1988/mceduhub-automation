import pytest

from mceduhub.core.exceptions import AmbiguousBookError, BookNotFoundError
from mceduhub.utils.matching import match_title

TITLES = [
    "Cambridge Primary English Student Book 4",
    "Cambridge Primary English Workbook 4",
    "Cambridge Primary English Teacher's Guide 4",
]


def test_exact_match_is_case_insensitive():
    assert match_title("cambridge primary english workbook 4", TITLES) == TITLES[1]


def test_unique_partial_match():
    assert match_title("Student Book 4", TITLES) == TITLES[0]


def test_ambiguous_partial_match_raises():
    with pytest.raises(AmbiguousBookError):
        match_title("Book 4", TITLES)


def test_no_match_raises():
    with pytest.raises(BookNotFoundError):
        match_title("Maths Grade 9", TITLES)


def test_exact_match_wins_over_longer_titles():
    titles = ["Book 1", "Book 10"]
    assert match_title("Book 1", titles) == "Book 1"
