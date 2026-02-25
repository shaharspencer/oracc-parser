"""
Pleiades gazetteer scraper.

Downloads and caches individual Pleiades place entries by numeric ID.
Entries are stored as JSON files inside a single ZIP archive
(``<data_dir>/pleiades_scraped_data.zip``) so repeated calls are fast.

Usage::

    from oracc_parser.download.pleiades import PleiadesData

    # Fetch the title of a place
    title = PleiadesData.get_city_title("874621")  # → "Nineveh/Ninos"

    # Fetch the full JSON for a place
    data = PleiadesData.get_place_json("874621")

    # Look up the Pleiades ID from a normalized city name
    pid = PleiadesData.get_id_by_city("Nineveh")

Ported from ``src/data_acquisition_and_saving/get_plaides_data.py``.
"""

import json
import zipfile
from pathlib import Path
from typing import Any

import requests

from oracc_parser.settings import data_dir
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_provenience

logger = get_logger()

# ---------------------------------------------------------------------------
# Default ZIP path
# ---------------------------------------------------------------------------

def _pleiades_zip_path() -> Path:
    """Return the path to the Pleiades cache ZIP inside the data directory.

    First checks ``ORACC_PLEIADES_ZIP`` env / .env setting; falls back to
    ``<data_dir>/pleiades_scraped_data.zip``.
    """
    from oracc_parser.settings import pleiades_zip_path

    configured = pleiades_zip_path()
    if configured:
        return configured
    return data_dir() / "pleiades_scraped_data.zip"


# ---------------------------------------------------------------------------
# Lazy-loaded provenience lookup: city_name → pleiades_id
# ---------------------------------------------------------------------------

_city_to_id: dict[str, str] | None = None


def _ensure_city_map() -> dict[str, str]:
    global _city_to_id
    if _city_to_id is None:
        df = get_provenience(pleiades_only=True)
        _city_to_id = dict(zip(df["normalized_city"], df["pleiades_id"]))
    return _city_to_id


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def _load_from_zip(pleiades_id: str, zip_path: Path) -> dict | None:
    """Return the cached JSON for *pleiades_id* from the ZIP, or None."""
    if not zip_path.exists():
        return None
    filename = f"{pleiades_id}.json"
    try:
        with zipfile.ZipFile(zip_path, mode="r") as zf:
            if filename in zf.namelist():
                with zf.open(filename) as f:
                    return json.load(f)
    except Exception as e:
        logger.warning(f"could not read {filename} from {zip_path}: {e}")
    return None


def _save_to_zip(pleiades_id: str, data: dict, zip_path: Path) -> None:
    """Append *data* as ``<pleiades_id>.json`` to *zip_path*."""
    filename = f"{pleiades_id}.json"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, mode="a") as zf:
            zf.writestr(filename, json.dumps(data, indent=2, ensure_ascii=False))
        logger.debug(f"saved {filename} to {zip_path}")
    except Exception as e:
        logger.error(f"could not save {filename} to {zip_path}: {e}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PleiadesData:
    """Thin wrapper around the Pleiades REST API with local ZIP caching."""

    # Base URL for individual place JSON
    BASE_URL = "https://pleiades.stoa.org/places/{pid}/json"

    @staticmethod
    def get_place_json(pleiades_id: str) -> dict[str, Any] | None:
        """Fetch (or load from cache) the full Pleiades JSON for *pleiades_id*.

        Returns ``None`` if the entry cannot be fetched.
        """
        pleiades_id = str(pleiades_id).strip()
        logger.debug(f"get_place_json: {pleiades_id}")

        zip_path = _pleiades_zip_path()

        # 1. Cache hit
        cached = _load_from_zip(pleiades_id, zip_path)
        if cached is not None:
            logger.debug(f"{pleiades_id}.json loaded from cache")
            return cached

        # 2. Download
        url = PleiadesData.BASE_URL.format(pid=pleiades_id)
        try:
            logger.info(f"downloading Pleiades entry {pleiades_id} …")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            if data:
                _save_to_zip(pleiades_id, data, zip_path)
                return data
            else:
                logger.error(f"empty JSON returned for Pleiades ID {pleiades_id}")
        except requests.RequestException as e:
            logger.error(f"HTTP error fetching Pleiades ID {pleiades_id}: {e}")
        except Exception as e:
            logger.error(f"unexpected error for Pleiades ID {pleiades_id}: {e}")

        return None

    @staticmethod
    def get_city_title(pleiades_id: str) -> str | None:
        """Return the ``title`` field from the Pleiades entry, or None."""
        data = PleiadesData.get_place_json(pleiades_id)
        if data:
            return data.get("title")
        return None

    @staticmethod
    def get_id_by_city(city_name: str) -> str | None:
        """Return the Pleiades ID for a normalized city name.

        Looks up ``oracc_parser/enriched_data/provenience.csv``.  Returns ``None`` if
        the city is not found or has no Pleiades ID.
        """
        return _ensure_city_map().get(city_name)

    @staticmethod
    def scrape_missing(pleiades_ids: list[str]) -> dict[str, dict | None]:
        """Download and cache Pleiades entries for a list of IDs.

        Returns a mapping of ``pleiades_id → JSON dict`` (or None for failures).
        Useful for bulk re-scraping IDs that were not previously downloaded.
        """
        results: dict[str, dict | None] = {}
        for pid in pleiades_ids:
            results[pid] = PleiadesData.get_place_json(pid)
        return results
