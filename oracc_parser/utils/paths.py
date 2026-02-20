"""
Cross-platform path utilities using importlib.resources.

Bundled reference CSVs are accessed via importlib.resources so they work
regardless of where the package is installed. Output/cache directories
are configurable.
"""

import os
from importlib import resources
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Bundled reference data (inside oracc_parser/data/)
# ---------------------------------------------------------------------------

_DATA_PKG = "oracc_parser.data"


def _data_file(filename: str) -> Path:
    """Return the path to a bundled reference CSV."""
    return resources.files(_DATA_PKG).joinpath(filename)


def get_sign_readings() -> pd.DataFrame:
    """Load the sign-readings lookup table."""
    return pd.read_csv(_data_file("sign_readings.csv"), dtype=str)


def get_pos_tags() -> pd.DataFrame:
    """Load the POS-tag meanings table."""
    return pd.read_csv(_data_file("pos_tags.csv"), dtype=str)


def get_languages() -> pd.DataFrame:
    """Load the languages summary table."""
    return pd.read_csv(_data_file("languages.csv"), dtype=str)


def get_projects_metadata() -> pd.DataFrame:
    """Load ORACC project metadata (project names, languages, etc.)."""
    return pd.read_csv(_data_file("projects_metadata.csv"), dtype=str)


def get_provenience(pleiades_only: bool = True) -> pd.DataFrame:
    """Load the consolidated provenance table (merged from two original CSVs).

    Args:
        pleiades_only: If True (default), return only rows that have a real
            Pleiades ID (a numeric string like ``"874754"``).  Rows with
            placeholder values such as ``"-"``, ``"?"``, or empty are dropped.
            Pass ``False`` to get the full table (used internally for pipeline
            provenience lookup).

    Returns:
        DataFrame with columns: ``raw_provenience``, ``normalized_city``,
        ``pleiades_id``, ``pleiades_title``, ``lat``, ``lon``.
    """
    df = pd.read_csv(_data_file("provenience.csv"), dtype=str)
    if pleiades_only:
        # Keep only rows whose pleiades_id is a clean numeric string
        df = df[df["pleiades_id"].str.strip().str.match(r"^\d+$", na=False)].copy()
        df = df.reset_index(drop=True)
    return df



def get_period_mapping() -> pd.DataFrame:
    """Load the period-to-year mapping table."""
    return pd.read_csv(_data_file("period_mapping.csv"))



def get_zip_dir(base: str | None = None) -> Path:
    """Return the directory for downloaded ORACC project ZIPs.

    Args:
        base: Custom directory. Defaults to configured ``ORACC_JSONZIP_DIR``
            (set via ``.env`` or environment variable).
    """
    if base:
        p = Path(base)
    else:
        from oracc_parser.settings import jsonzip_dir
        p = jsonzip_dir()

    p.mkdir(parents=True, exist_ok=True)
    return p
