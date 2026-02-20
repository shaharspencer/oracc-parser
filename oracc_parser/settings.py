"""
Application settings loaded from environment variables and .env file.

This centralizes all configuration so users can set values in one place.

Priority order:
  1. Environment variables (highest)
  2. .env file (found by walking up from cwd)
  3. Defaults defined here (lowest)

**Default directory layout** (relative to the repo root):

    data/
      cache/         ← parsed tablet JSON cache
      jsonzip/       ← downloaded project ZIP files
    output/          ← exported CSVs, JSONL files

The repo root is determined by locating the nearest `pyproject.toml`
when running from inside the repo (including from notebooks/).
If no `pyproject.toml` is found, cwd is used as fallback.
"""

import os
from functools import lru_cache
from pathlib import Path

# Try to load .env — python-dotenv is optional
try:
    from dotenv import load_dotenv, find_dotenv

    _env_file = find_dotenv(usecwd=True)
    if _env_file:
        load_dotenv(_env_file)
except ImportError:
    pass  # dotenv not installed — rely on OS env vars


def _find_repo_root() -> Path:
    """Return the package root (the directory that contains oracc_parser/).

    Anchored to *this file's location* so paths are stable regardless of
    where Python / Jupyter is launched from.  settings.py lives at
    ``<repo_root>/oracc_parser/settings.py``, so two .parent calls give us
    ``<repo_root>``.
    """
    return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_settings() -> dict:
    """Return a dictionary of all settings, resolved from env / .env / defaults."""
    repo_root = _find_repo_root()

    # Default data_dir is <repo_root>/data — everything data-related lives here
    data_dir = os.getenv("ORACC_DATA_DIR", str(repo_root / "data"))

    # output_dir for user-facing exports
    output_dir = os.getenv("ORACC_OUTPUT_DIR", str(repo_root / "output"))

    return {
        # Zenodo
        "zenodo_record_url": os.getenv(
            "ORACC_ZENODO_RECORD_URL", "https://zenodo.org/records/18643122"
        ),
        # Directories — all data-related paths are under data_dir by default
        "data_dir": data_dir,
        "output_dir": output_dir,
        "cache_dir": os.getenv("ORACC_CACHE_DIR", str(Path(data_dir) / "cache")),
        "jsonzip_dir": os.getenv("ORACC_JSONZIP_DIR", str(Path(data_dir) / "jsonzip")),
        # Cache
        "use_cache": os.getenv("ORACC_USE_CACHE", "true").lower() == "true",
        # Pleiades
        "pleiades_zip": os.getenv("ORACC_PLEIADES_ZIP", ""),
        # Logging
        "log_level": os.getenv("ORACC_LOG_LEVEL", "INFO"),
    }


# Convenience accessors
def data_dir() -> Path:
    """Configured data directory (default: <repo_root>/data)."""
    return Path(get_settings()["data_dir"])


def output_dir() -> Path:
    """Configured output directory (default: <repo_root>/output)."""
    return Path(get_settings()["output_dir"])


def cache_dir() -> Path:
    """Configured cache directory (default: <repo_root>/data/cache)."""
    return Path(get_settings()["cache_dir"])


def jsonzip_dir() -> Path:
    """Configured directory for project ZIP files (default: <repo_root>/data/jsonzip)."""
    return Path(get_settings()["jsonzip_dir"])


def zenodo_url() -> str:
    """Zenodo record URL for pre-downloaded data."""
    return get_settings()["zenodo_record_url"]


def use_cache() -> bool:
    """Whether to prefer cached data."""
    return get_settings()["use_cache"]


def log_level() -> str:
    """Configured log level."""
    return get_settings()["log_level"]


def pleiades_zip_path() -> Path | None:
    """Path to pre-downloaded Pleiades ZIP, or None."""
    p = get_settings()["pleiades_zip"]
    return Path(p) if p else None
