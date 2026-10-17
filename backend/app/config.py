"""Environment-backed configuration with safe defaults for the local prototype."""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "skillscope.db"


class ConfigurationError(ValueError):
    """Raised for unsupported or unsafe application configuration."""


def resolve_database_path(database_url: str | None = None) -> Path:
    """Resolve the supported SQLite URL; relative paths are anchored to the project root.

    The application currently supports file-backed SQLite only. A memory database would be
    lost between repository connections and is therefore rejected rather than misleadingly
    appearing persistent.
    """
    raw = (database_url if database_url is not None else os.getenv("SKILLSCOPE_DATABASE_URL", "")).strip()
    if not raw:
        legacy_path = os.getenv("SKILLSCOPE_DATABASE_PATH", "").strip()
        candidate = Path(legacy_path).expanduser() if legacy_path else DEFAULT_DATABASE_PATH
        return candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()

    if raw in {"sqlite:///:memory:", "sqlite://"}:
        raise ConfigurationError("SKILLSCOPE_DATABASE_URL must point to a file-backed SQLite database.")
    prefix = "sqlite:///"
    if not raw.startswith(prefix):
        raise ConfigurationError("Only file-backed SQLite URLs (sqlite:///...) are supported by this prototype.")
    path_text = raw[len(prefix):]
    if not path_text or "\x00" in path_text:
        raise ConfigurationError("SKILLSCOPE_DATABASE_URL contains an invalid SQLite path.")
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def seed_demo_enabled() -> bool:
    """Default to synthetic fixtures in development and off in production."""
    configured = os.getenv("SKILLSCOPE_SEED_DEMO")
    if configured is not None:
        return configured.strip().casefold() in {"1", "true", "yes", "on"}
    return os.getenv("SKILLSCOPE_ENV", "development").strip().casefold() != "production"


def external_cache_ttl_seconds() -> int:
    raw = os.getenv("SKILLSCOPE_SOURCE_CACHE_TTL_SECONDS", "86400")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError("SKILLSCOPE_SOURCE_CACHE_TTL_SECONDS must be an integer.") from exc
    if not 0 <= value <= 31_536_000:
        raise ConfigurationError("SKILLSCOPE_SOURCE_CACHE_TTL_SECONDS must be between 0 and 31536000 seconds.")
    return value
