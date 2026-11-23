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
      translations/      <-- TRANSLATIONS_DIR (cached HTML translation pages)
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

TRANSLATIONS_DIR: Path = DATA_DIR / "translations"
JSONZIP_DIR: Path = DATA_DIR / "jsonzip"
WORD_CSV_DIR: Path = DATA_DIR / "oracc_csvs"
CATALOGUE_DIR: Path = DATA_DIR / "catalogues"

# --- Zenodo dataset ---
# The concept record stands for "every version" of the dataset: Zenodo resolves
# it to the newest published version, so a new dataset version reaches users
# without a new package release.
ZENODO_CONCEPT_ID: str = "18643121"

# Pin a specific dataset version by setting this to that version's record URL,
# e.g. "https://zenodo.org/records/24336925" (or set the ORACC_ZENODO_RECORD_URL
# environment variable). None means: use the newest version.
ZENODO_RECORD_URL: str | None = os.environ.get("ORACC_ZENODO_RECORD_URL", "").strip() or None

# Used only when the newest version cannot be looked up (Zenodo unreachable).
# Keep it pointing at a published version; it does not need to be the newest.
ZENODO_FALLBACK_RECORD_ID: str = "24462772"

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

def translations_dir() -> Path:
    global TRANSLATIONS_DIR
    return TRANSLATIONS_DIR

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
    """Record URL to download from: the pinned version, else the concept record.

    The concept record URL is resolved to the newest version by
    ``oracc_parser.download.fetch_data.resolve_record_id()``.
    """
    global ZENODO_RECORD_URL, ZENODO_CONCEPT_ID
    return ZENODO_RECORD_URL or f"https://zenodo.org/records/{ZENODO_CONCEPT_ID}"

def zenodo_is_pinned() -> bool:
    """True when a specific dataset version was chosen instead of the newest."""
    global ZENODO_RECORD_URL
    return bool(ZENODO_RECORD_URL)

def log_level() -> str:
    global LOG_LEVEL
    return LOG_LEVEL

def pleiades_zip_path() -> Path | None:
    global PLEIADES_ZIP
    return PLEIADES_ZIP

def get_settings() -> dict:
    """Return current settings as a plain dict (useful for inspection/debugging)."""
    return {
        "data_dir": str(DATA_DIR),
        "translations_dir": str(TRANSLATIONS_DIR),
        "jsonzip_dir": str(JSONZIP_DIR),
        "word_csv_dir": str(WORD_CSV_DIR),
        "catalogue_dir": str(CATALOGUE_DIR),
        "zenodo_record_url": zenodo_url(),
        "zenodo_version": "pinned" if zenodo_is_pinned() else "newest",
        "log_level": LOG_LEVEL,
    }
