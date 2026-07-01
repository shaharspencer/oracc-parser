"""
Download ORACC project ZIPs from the ORACC server.

Supports downloading specific projects by name or filtering by language
from the projects metadata table.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
from tqdm import tqdm

from oracc_parser.models.config import RunConfig
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_projects_metadata, get_zip_dir

logger = get_logger()

ORACC_BASE_URL = "http://oracc.museum.upenn.edu"


def download_zip(project: str, output_dir: Path | None = None) -> Path | None:
    """Download a single ORACC project ZIP file.

    Args:
        project: Project path, e.g. ``"saao/saa01"``.
        output_dir: Directory to save the ZIP. Defaults to ``get_zip_dir()``.

    Returns:
        Path to the downloaded ZIP file, or None on failure.
    """
    if output_dir is None:
        output_dir = get_zip_dir()

    url = f"{ORACC_BASE_URL}/json/{project.strip('/')}.zip"
    filename = project.replace("/", "-") + ".zip"
    dest = output_dir / filename

    if dest.exists():
        logger.info(f"Already downloaded: {dest}")
        return dest

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        logger.info(f"Downloading {url} ...")
        # SSL verification disabled because ORACC often has expired/invalid certs
        resp = requests.get(url, stream=True, timeout=60, verify=False)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, desc=filename, leave=False
        ) as bar:
             for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))

        logger.info(f"Saved: {dest}")
        return dest

    except requests.RequestException as e:
        logger.error(f"Failed to download {project}: {e}")
        if dest.exists():
            os.remove(dest)
        return None



def get_live_project_list() -> list[str]:
    """Fetch the current list of public projects from ORACC servers.

    Returns:
        List of project names (e.g. ``"saao/saa01"``).
    """
    url = f"{ORACC_BASE_URL}/projects.json"
    try:

        resp = requests.get(url, verify=False, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        projects = data.get("public", [])
        logger.info(f"Fetched {len(projects)} projects from ORACC")
        return projects
    except Exception as e:
        logger.error(f"Failed to fetch project list: {e}")
        return []


def update_project_metadata() -> list[str]:
    """Update the local projects_metadata.csv with new projects from ORACC.

    Fetches the live list, checks against the local CSV, and adds any missing
    projects with empty metadata fields.

    Returns:
        List of newly added project names.
    """
    import pandas as pd
    from datetime import datetime
    from oracc_parser.utils.paths import get_projects_metadata_path

    csv_path = get_projects_metadata_path()
    df = pd.read_csv(csv_path).fillna("")
    
    existing = set(df["Project_Name"])
    live_list = set(get_live_project_list())
    
    new_projects = sorted(live_list - existing)
    
    if not new_projects:
        logger.info("No new projects found.")
        return []

    today = datetime.now().strftime("%d/%m/%Y")
    rows = []
    for proj in new_projects:
        rows.append({
            "Project": "",
            "Link": f"http://oracc.museum.upenn.edu/{proj}",
            "Project_Name": proj,
            "Languages": "",
            "Is_Umbrella_Project": "",
            "Is_Text_Folder_Empty": "",
            "Last_Check": today
        })
    
    if rows:
        df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
        df.sort_values("Project_Name", inplace=True)
        df.to_csv(csv_path, index=False)
        logger.info(f"Added {len(new_projects)} new projects to metadata.")
        
    return new_projects


def get_live_projects_dataframe() -> "pd.DataFrame":
    """Fetch rich project metadata from `projectlist.json` as a DataFrame.

    Tries to fetch from ORACC with retries. If all attempts fail, falls back
    to the local bundled `projects_metadata.csv`.

    Returns:
        DataFrame with columns like ``project``, ``name``, ``abbrev``, ``blurb``.
    """
    import pandas as pd
    import json
    import re
    import time
    from oracc_parser.utils.paths import get_projects_metadata

    url = f"{ORACC_BASE_URL}/projectlist.json"
    max_retries = 3
    timeout = 60

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching live project list (attempt {attempt + 1}/{max_retries})...")

            resp = requests.get(url, verify=False, timeout=timeout)
            
            # Fix known ORACC JSON bug where "projects" key is malformed/doubled
            text = resp.text
            if '"projects": ["' in text and '"projects": [{' in text:
                logger.warning("Detected malformed ORACC JSON, attempting regex fix...")
                text = re.sub(r'"projects":\s*\["\s*"projects":', '"projects":', text)
                
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Standard JSON parse failed. Trying aggressive cleanup.")
                text = text.replace('\t"projects": ["\n', "")
                data = json.loads(text)

            projects = data.get("public", data.get("projects", []))
            df = pd.DataFrame(projects)
            
            if "pathname" in df.columns:
                df.rename(columns={"pathname": "project"}, inplace=True)
                
            logger.info(f"Fetched {len(df)} projects from ORACC live list")
            return df

        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)  # Wait 2 seconds before retry
            else:
                logger.error("All live fetch attempts failed.")

    logger.warning("Falling back to local bundled project metadata.")
    try:
        df = get_projects_metadata()
        if "Project_Name" in df.columns:
            df["project"] = df["Project_Name"]
        return df
    except Exception as e:
        logger.error(f"Failed to load local fallback metadata: {e}")
        return pd.DataFrame()
