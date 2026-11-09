"""Live smoke tests against the real site. Not run by default.

    pytest -m live
"""

from dataclasses import replace

import pytest
from dotenv import load_dotenv

from mceduhub.app import list_books
from mceduhub.core.settings import PROJECT_ROOT, Credentials, Settings

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")
    s = Settings.load()
    s.browser = replace(s.browser, headless=True)
    return s


def test_login_and_list_books(settings):
    titles = list_books(settings, Credentials.from_env())
    assert titles, "library should list at least one book"
    assert all(isinstance(t, str) and t for t in titles)
