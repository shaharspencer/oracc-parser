"""
Application settings and directory paths.

This centralizes configuration. To change where your data is stored or where 
the parser outputs files, simply override these variables at runtime or edit this file directly.

Example in a notebook:
    import oracc_parser.settings as settings
    from pathlib import Path
    settings.DATA_DIR = Path("D:/my_custom_oracc_data")

**Default directory layout** (relative to the repo root):

    enriched_data/   <-- DATA_DIR
      cache/         <-- CACHE_DIR (parsed tablet JSON cache)
      jsonzip/       <-- JSONZIP_DIR (downloaded project ZIP files)
    output/          <-- OUTPUT_DIR (exported CSVs, JSONL files, at repo root)
"""
from __future__ import annotations

from pathlib import Path


def _find_repo_root() -> Path:
    """Return the package root (the directory that contains oracc_parser/)."""
    return Path(__file__).resolve().parent.parent

# --- Global Configuration Variables ---

# Base directories
REPO_ROOT: Path = _find_repo_root()
DATA_DIR: Path = REPO_ROOT / "enriched_data"
OUTPUT_DIR: Path = REPO_ROOT / "output"

# Specific data subdirectories
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


# --- Convenience Accessors for Backwards Compatibility ---
# These functions dynamically return the current value of the global variables above,
# ensuring that runtime overrides (like settings.DATA_DIR = ...) take effect everywhere.

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
