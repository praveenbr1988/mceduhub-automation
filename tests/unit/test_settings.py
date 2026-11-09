import pytest

from mceduhub.core.exceptions import ConfigurationError
from mceduhub.core.settings import Credentials, Settings


def test_defaults_when_no_file():
    s = Settings()
    assert s.resources.only_extensions == [".zip"]
    assert s.site.login_url.endswith("lms_login.aspx?REASON=denied_empty")


def test_toml_overrides_defaults(tmp_path):
    cfg = tmp_path / "s.toml"
    cfg.write_text('books = ["Book A"]\n[browser]\nheadless = true\n[resources]\nonly_extensions = []\n')
    s = Settings.load(cfg)
    assert s.books == ["Book A"]
    assert s.browser.headless is True
    assert s.resources.only_extensions == []
    assert s.ebook.max_pages == 600  # untouched default


def test_unknown_setting_is_rejected(tmp_path):
    cfg = tmp_path / "s.toml"
    cfg.write_text("[browser]\nheadles = true\n")
    with pytest.raises(ConfigurationError, match="headles"):
        Settings.load(cfg)


def test_explicit_missing_file_is_an_error(tmp_path):
    with pytest.raises(ConfigurationError):
        Settings.load(tmp_path / "nope.toml")


def test_shipped_config_file_is_valid():
    Settings.load()  # config/settings.toml must always parse


def test_credentials_from_env(monkeypatch):
    for var, value in [("PLATFORM_USERNAME", "u"), ("PLATFORM_PASSWORD", "secret"),
                       ("PLATFORM_SCHOOL_ID", "s"), ("PLATFORM_SCHOOL_NAME", "School")]:
        monkeypatch.setenv(var, value)
    creds = Credentials.from_env()
    assert creds.username == "u"
    assert "secret" not in repr(creds)


def test_missing_credentials_lists_variables(monkeypatch):
    monkeypatch.delenv("PLATFORM_PASSWORD", raising=False)
    monkeypatch.setenv("PLATFORM_USERNAME", "u")
    with pytest.raises(ConfigurationError, match="PLATFORM_PASSWORD"):
        Credentials.from_env()
