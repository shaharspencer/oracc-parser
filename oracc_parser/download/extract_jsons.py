"""
Extract JSON text files and catalogue from downloaded ORACC project ZIPs.
"""

import json
import os
import zipfile
from typing import Optional

from pydantic import BaseModel, Field

from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_zip_dir

logger = get_logger()


class ProjectData(BaseModel):
    """Container for JSON text files and catalogue extracted from a ZIP."""

    json_files: list[dict] = Field(default_factory=list)
    project_catalogue: Optional[dict] = None


def extract_from_zip(project: str, zip_dir=None) -> ProjectData:
    """Extract all corpus JSONs and the catalogue from a project ZIP.

    Args:
        project: Project path, e.g. ``"saao/saa01"``.
        zip_dir: Directory containing the ZIPs. Defaults to ``get_zip_dir()``.

    Returns:
        ProjectData with parsed JSON dicts and catalogue.
    """
    if zip_dir is None:
        zip_dir = get_zip_dir()

    result = ProjectData()
    zipf = os.path.join(str(zip_dir), f"{project.replace('/', '-')}.zip")

    if not os.path.exists(zipf):
        logger.error(f"ZIP file not found: {zipf}")
        return result

    try:
        with zipfile.ZipFile(zipf) as z:
            if not z.namelist():
                logger.error(f"ZIP file is empty: {zipf}")
                return result

            # Extract corpus JSON files
            json_files = [
                name for name in z.namelist()
                if "corpusjson" in name and name.endswith(".json")
            ]

            for fn in json_files:
                try:
                    raw = z.read(fn).decode("utf-8")
                    data = json.loads(raw)
                    result.json_files.append(data)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Error reading {fn}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error with {fn}: {e}")

            # Extract catalogue
            catalogue_files = [
                name for name in z.namelist()
                if name.endswith("catalogue.json")
            ]
            if catalogue_files:
                try:
                    cat_raw = z.read(catalogue_files[0]).decode("utf-8")
                    result.project_catalogue = json.loads(cat_raw)
                except Exception as e:
                    logger.error(f"Failed to parse catalogue.json: {e}")
            else:
                logger.warning(f"catalogue.json not found in {zipf}")

    except zipfile.BadZipFile as e:
        logger.error(f"Malformed ZIP file {zipf}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error opening {zipf}: {e}")

    return result
