"""Typed settings loaded from config/settings.toml, with credentials from environment (.env).

Precedence (lowest -> highest): dataclass defaults -> settings.toml -> CLI options.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from mceduhub.core.exceptions import ConfigurationError

# src/mceduhub/core/settings.py -> project root is three levels above "core"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_FILE = PROJECT_ROOT / "config" / "settings.toml"


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str = field(repr=False)  # never printed in logs
    school_id: str
    school_name: str

    ENV_VARS = {
        "username": "PLATFORM_USERNAME",
        "password": "PLATFORM_PASSWORD",
        "school_id": "PLATFORM_SCHOOL_ID",
        "school_name": "PLATFORM_SCHOOL_NAME",
    }

    @classmethod
    def from_env(cls) -> "Credentials":
        missing = [var for var in cls.ENV_VARS.values() if not os.getenv(var)]
        if missing:
            raise ConfigurationError(
                f"Missing credentials: {', '.join(missing)}. Copy .env.example to .env and fill it in."
            )
        return cls(**{attr: os.environ[var] for attr, var in cls.ENV_VARS.items()})


@dataclass
class SiteSettings:
    base_url: str = "https://www.mceduhub.com"
    login_path: str = "/Lead/Login/lms_login.aspx?REASON=denied_empty"

    @property
    def login_url(self) -> str:
        return self.base_url.rstrip("/") + self.login_path


@dataclass
class BrowserSettings:
    headless: bool = False
    viewport_width: int = 1600
    viewport_height: int = 900
    device_scale_factor: float = 2.0
    user_data_dir: str = ".browser-profile"
    default_timeout_s: float = 30.0


@dataclass
class EbookSettings:
    wait_after_turn_s: float = 0.8
    page_load_timeout_s: float = 15.0
    reader_ready_timeout_s: float = 60.0
    max_pages: int = 600
    jpeg_quality: int = 90
    keep_images: bool = False


@dataclass
class ResourceSettings:
    new_tab_wait_s: float = 6.0
    download_start_timeout_s: float = 60.0
    sections: list[str] = field(default_factory=lambda: ["Teacher's Resources"])
    only_extensions: list[str] = field(default_factory=lambda: [".zip"])
    skip_names_containing: list[str] = field(default_factory=lambda: ["audio"])
    max_files: int = 10_000


@dataclass
class OutputSettings:
    output_dir: str = "output"
    log_dir: str = "logs"
    force: bool = False


_SECTIONS: dict[str, type] = {
    "site": SiteSettings,
    "browser": BrowserSettings,
    "ebook": EbookSettings,
    "resources": ResourceSettings,
    "output": OutputSettings,
}


@dataclass
class Settings:
    site: SiteSettings = field(default_factory=SiteSettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    ebook: EbookSettings = field(default_factory=EbookSettings)
    resources: ResourceSettings = field(default_factory=ResourceSettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    books: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        """Load settings from a TOML file. A missing default file means 'use defaults'."""
        config_file = Path(path) if path else DEFAULT_CONFIG_FILE
        if not config_file.exists():
            if path:
                raise ConfigurationError(f"Config file not found: {config_file}")
            return cls()
        try:
            data = tomllib.loads(config_file.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise ConfigurationError(f"Invalid TOML in {config_file}: {e}") from e

        unknown = set(data) - set(_SECTIONS) - {"books"}
        if unknown:
            raise ConfigurationError(f"Unknown section(s) in {config_file.name}: {sorted(unknown)}")
        sections = {name: _build(klass, data.get(name, {}), name) for name, klass in _SECTIONS.items()}
        return cls(**sections, books=list(data.get("books", [])))

    @staticmethod
    def resolve(path: str | Path) -> Path:
        """Resolve a configured path relative to the project root."""
        p = Path(path)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def output_dir(self) -> Path:
        return self.resolve(self.output.output_dir)


def _build(klass: type, values: dict[str, Any], section: str):
    valid = {f.name for f in fields(klass)}
    bad = set(values) - valid
    if bad:
        raise ConfigurationError(f"Unknown setting(s) in [{section}]: {sorted(bad)}. Valid: {sorted(valid)}")
    return klass(**values)
