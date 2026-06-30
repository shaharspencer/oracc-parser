"""
Application settings and directory paths.

This centralizes configuration. To change where your data is stored or where
the parser outputs files, override these variables at runtime or set the
``ORACC_DATA_DIR`` environment variable before importing the package.

Example in a notebook or script::

    import oracc_parser.settings as settings
    from pathlib import Path
    settings.DATA_DIR = Path("/my/data/dir")

Or via environment variable (set before running Python)::

    ORACC_DATA_DIR=/my/data/dir python my_script.py

**Default directory layout** (created in your working directory on first use):

    oracc_data/          <-- DATA_DIR
      catalogues/        <-- CATALOGUE_DIR (project catalogue CSVs)
      oracc_csvs/        <-- WORD_CSV_DIR (downloaded word-level CSVs)
      cache/             <-- CACHE_DIR (parsed tablet JSON cache)
      jsonzip/           <-- JSONZIP_DIR (downloaded ORACC JSON ZIPs)
      output/            <-- OUTPUT_DIR (exported CSVs, JSONL files)

Note: the bundled reference CSVs (pos_tags, provenience, period_mapping, etc.)
are shipped inside the package itself and are always available without any
download — they are NOT stored in DATA_DIR.
"""
from __future__ import annotations

import os
from pathlib import Path


def _default_data_dir() -> Path:
    """Resolve the default data directory.

    Priority:
    1. ``ORACC_DATA_DIR`` environment variable (explicit user override).
    2. ``./enriched_data`` in the current working directory, if it already
       exists (backwards-compatible for users who cloned the repo).
    3. ``./oracc_data`` in the current working directory (clean install default).
    """
    env = os.environ.get("ORACC_DATA_DIR", "").strip()
    if env:
        return Path(env)
    legacy = Path.cwd() / "enriched_data"
    if legacy.exists():
        return legacy
    return Path.cwd() / "oracc_data"


# --- Global Configuration Variables ---

DATA_DIR: Path = _default_data_dir()
OUTPUT_DIR: Path = DATA_DIR / "output"

CACHE_DIR: Path = DATA_DIR / "cache"
JSONZIP_DIR: Path = DATA_DIR / "jsonzip"
WORD_CSV_DIR: Path = DATA_DIR / "oracc_csvs"
CATALOGUE_DIR: Path = DATA_DIR / "catalogues"

# URL for downloading reference data (Zenodo)
ZENODO_RECORD_URL: str = "https://zenodo.org/records/20625379"

# Should the parser use cached output?
USE_CACHE: bool = True

# Logging
LOG_LEVEL: str = "INFO"

# Optional Zip for Pleiades (if manually downloaded)
PLEIADES_ZIP: Path | None = None


# --- Convenience Accessors ---
# These functions dynamically return the current value of the global variables
# above, so runtime overrides (settings.DATA_DIR = ...) take effect everywhere.

def data_dir() -> Path:
    global DATA_DIR
    return DATA_DIR

def output_dir() -> Path:
    global OUTPUT_DIR
    return OUTPUT_DIR

def cache_dir() -> Path:
    global CACHE_DIR
    return CACHE_DIR

def jsonzip_dir() -> Path:
    global JSONZIP_DIR
    return JSONZIP_DIR

def word_csv_dir() -> Path:
    global WORD_CSV_DIR
    return WORD_CSV_DIR

def catalogue_dir() -> Path:
    global CATALOGUE_DIR
    return CATALOGUE_DIR

def zenodo_url() -> str:
    global ZENODO_RECORD_URL
    return ZENODO_RECORD_URL

def use_cache() -> bool:
    global USE_CACHE
    return USE_CACHE

def log_level() -> str:
    global LOG_LEVEL
    return LOG_LEVEL

def pleiades_zip_path() -> Path | None:
    global PLEIADES_ZIP
    return PLEIADES_ZIP
