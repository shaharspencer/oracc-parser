"""
Download and extract pre-processed ORACC data from Zenodo.

Project word CSVs are downloaded lazily — only when first accessed — from
per-umbrella zip files on Zenodo (e.g. ``saao.zip`` covers all saao/* projects).
Catalogues and HTML translations are downloaded eagerly on the first call to
``fetch_data()``.  Pass ``include_json_zips=True`` to also fetch the raw ORACC
JSON ZIPs (needed only if you want to re-run the full JSON processing pipeline
via ``parse_project()``).

The newest published version of the dataset is used unless a version is pinned
(``settings.ZENODO_RECORD_URL``, the ``ORACC_ZENODO_RECORD_URL`` environment
variable, or ``url=`` / ``--url``), so new dataset versions need no package release.

Can be called as:
    oracc-parser fetch-data
    python -m oracc_parser.download.fetch_data
    from oracc_parser.download.fetch_data import fetch_data
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from oracc_parser import settings
from oracc_parser.settings import (
    catalogue_dir,
    data_dir,
    jsonzip_dir,
    translations_dir,
    word_csv_dir,
    zenodo_is_pinned,
    zenodo_url,
)
from oracc_parser.utils.paths import project_slug

ZENODO_API = "https://zenodo.org/api"

# Which Zenodo file (record id + checksum) each extracted archive came from.
# Lets fetch_data() refresh data when a newer dataset version changes a file.
STATE_FILE = ".zenodo_files.json"

# Record JSON by the id it was requested with, so one session sticks to one
# dataset version and asks Zenodo only once.
_record_cache: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Zenodo record lookup
# ---------------------------------------------------------------------------


def record_id_from_url(record_url: str) -> str:
    """Return the record id in a Zenodo record URL, API URL, DOI or bare id.

    >>> record_id_from_url("https://zenodo.org/records/24336925")
    '24336925'
    >>> record_id_from_url("https://doi.org/10.5281/zenodo.18643121")
    '18643121'
    """
    m = re.search(r"(\d+)/*$", str(record_url).strip())
    if not m:
        raise ValueError(f"Not a Zenodo record URL or id: {record_url!r}")
    return m.group(1)


def get_zenodo_record(record_url: str | None = None) -> dict:
    """Fetch a Zenodo record's JSON (cached for the session).

    ``record_url`` defaults to ``settings.zenodo_url()``. A concept record (the
    default) resolves to the newest published version of the dataset; a
    version's own record URL returns that version.
    """
    rid = record_id_from_url(record_url or zenodo_url())
    if rid not in _record_cache:
        resp = requests.get(f"{ZENODO_API}/records/{rid}", timeout=30)
        resp.raise_for_status()
        _record_cache[rid] = resp.json()
    return _record_cache[rid]


def resolve_record(record_url: str | None = None) -> tuple[str, dict | None]:
    """Return ``(record id, record JSON)`` for the dataset version to use.

    If the newest version cannot be looked up (Zenodo unreachable) and no
    version was chosen explicitly, falls back to
    ``settings.ZENODO_FALLBACK_RECORD_ID`` with a warning; the JSON is then
    ``None``. A version chosen explicitly (``record_url`` or a pinned
    ``ZENODO_RECORD_URL``) never falls back: the error is raised.
    """
    try:
        record = get_zenodo_record(record_url)
        return str(record["id"]), record
    except requests.RequestException as e:
        if record_url or zenodo_is_pinned():
            raise
        fallback = settings.ZENODO_FALLBACK_RECORD_ID
        print(
            f"WARNING: could not look up the newest dataset version on Zenodo ({e}). "
            f"Using record {fallback}.",
            file=sys.stderr,
        )
        return fallback, None


def resolve_record_id(record_url: str | None = None) -> str:
    """Record id of the dataset version to use (the newest, unless pinned)."""
    return resolve_record(record_url)[0]


def _file_checksum(record: dict | None, filename: str) -> str:
    if not record:
        return ""
    return next((f.get("checksum", "") for f in record.get("files", []) if f["key"] == filename), "")


# ---------------------------------------------------------------------------
# Local download state
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    return data_dir() / STATE_FILE


def _load_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _record_state(filename: str, record_id: str, checksum: str) -> None:
    state = _load_state()
    state[filename] = {"record_id": record_id, "checksum": checksum}
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def _md5_matches(path: Path, checksum: str) -> bool:
    """True if ``path`` matches a Zenodo ``md5:<hex>`` checksum (or none is known)."""
    if not checksum.startswith("md5:"):
        return True
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest() == checksum[4:]


# ---------------------------------------------------------------------------
# Download and extraction
# ---------------------------------------------------------------------------


def download_file(url: str, dest: Path, desc: str = "") -> Path:
    """Download a file with a progress bar."""
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    total = int(resp.headers.get("content-length", 0))

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        with tqdm(total=total, unit="B", unit_scale=True, desc=desc) as bar:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                bar.update(len(chunk))
    return dest


def get_zenodo_files(record_url: str | None = None) -> list[dict]:
    """List the files of a Zenodo record (default: the newest dataset version)."""
    files = get_zenodo_record(record_url).get("files", [])
    return [
        {
            "filename": f["key"],
            "size": f["size"],
            "url": f["links"]["self"],
            "checksum": f.get("checksum", ""),
        }
        for f in files
    ]


def extract_jsonzip_archive(archive_path: Path, dest_dir: Path, overwrite: bool = False) -> None:
    """Extract oracc_jsonzip_all.zip into dest_dir (the jsonzip folder).

    The archive contains entries like ``jsonzip/saao-saa01.zip``.
    Only the inner ``*.zip`` files are extracted — the ``jsonzip/`` prefix
    is stripped so they land directly in ``dest_dir``. Existing files are kept
    unless ``overwrite`` is set.
    """
    print(f"\nExtracting project ZIPs from {archive_path.name} ...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as z:
        members = [m for m in z.namelist() if m.endswith(".zip")]
        for member in tqdm(members, desc="Extracting", unit="file"):
            filename = Path(member).name
            target = dest_dir / filename
            if target.exists() and not overwrite:
                continue
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
    print(f"[OK] Extracted {len(members)} project ZIPs to {dest_dir}")


def extract_data_archive(archive_path: Path, dest_dir: Path, label: str, overwrite: bool = False) -> None:
    """Extract a flat CSV archive (catalogues.zip) into dest_dir.

    Handles both archive layouts:
    - Contents directly at the root (``saao-saa01/P123456.csv``)
    - Wrapped in a single top-level folder (``oracc_csvs/saao-saa01/P123456.csv``)

    Existing files are kept unless ``overwrite`` is set.
    """
    print(f"\nExtracting {archive_path.name} ...")
    dest_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(archive_path, "r") as z:
        names = z.namelist()

        # Detect a single common top-level directory prefix and strip it
        top_dirs = {n.split("/")[0] for n in names if "/" in n}
        prefix = ""
        if len(top_dirs) == 1:
            candidate = top_dirs.pop() + "/"
            if all(n.startswith(candidate) or n == candidate.rstrip("/") for n in names):
                prefix = candidate

        files = [n for n in names if not n.endswith("/")]
        for member in tqdm(files, desc=f"Extracting {label}", unit="file"):
            rel_path = member[len(prefix):] if prefix else member
            if not rel_path:
                continue
            target = dest_dir / rel_path
            if target.exists() and not overwrite:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    print(f"[OK] Extracted {len(files)} files to {dest_dir}")


def extract_project_csvs(
    project: str,
    dest_dir: Path | None = None,
) -> Path:
    """Download and extract word CSVs for a project from Zenodo on demand.

    Downloads the umbrella zip for the project's corpus group (e.g. ``saao.zip``
    for any ``saao/*`` project), extracts all sub-projects it contains, then
    deletes the temporary zip.  Subsequent calls for any project in the same
    umbrella group are instant because the files are already on disk.

    Args:
        project:  ORACC project path, e.g. ``"saao/saa01"``.
        dest_dir: Root directory where project folders are written.
                  Defaults to ``word_csv_dir()``.

    Returns:
        Path to the extracted project directory.

    Raises:
        FileNotFoundError: If the umbrella zip cannot be downloaded from Zenodo.
        ValueError: If no CSV files for the project exist in the downloaded archive.
    """
    dest_dir = dest_dir or word_csv_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    slug = project_slug(project)
    project_dir = dest_dir / slug

    if project_dir.exists() and any(project_dir.glob("*.csv")):
        return project_dir

    umbrella = slug.split("-")[0]
    record_id, record = resolve_record()
    file_url = f"https://zenodo.org/records/{record_id}/files/{umbrella}.zip"
    tmp_zip = dest_dir / f"_tmp_{umbrella}.zip"

    print(f"Downloading {umbrella}.zip from Zenodo (record {record_id})...")
    try:
        download_file(file_url, tmp_zip, desc=f"{umbrella}.zip")
    except Exception as e:
        if tmp_zip.exists():
            tmp_zip.unlink()
        raise FileNotFoundError(
            f"Could not download {umbrella}.zip from Zenodo: {e}"
        ) from e

    with zipfile.ZipFile(tmp_zip, "r") as z:
        files = [n for n in z.namelist() if not n.endswith("/")]
        for member in files:
            target = dest_dir / member
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    tmp_zip.unlink()
    _record_state(f"{umbrella}.zip", record_id, _file_checksum(record, f"{umbrella}.zip"))

    if not project_dir.exists() or not any(project_dir.glob("*.csv")):
        raise ValueError(f"No CSVs found for '{project}' in {umbrella}.zip")

    print(f"  -> Extracted {umbrella} projects to {dest_dir}")
    return project_dir


def fetch_data(
    url: str | None = None,
    dest: Path | None = None,
    include_translations: bool = False,
    include_json_zips: bool = False,
) -> None:
    """Download pre-processed ORACC data from Zenodo and extract it.

    By default downloads only ``catalogues.zip`` — the minimum needed for all
    standard notebook workflows.  Word CSVs are downloaded lazily per-project
    on first access via ``extract_project_csvs()``.

    Set ``include_translations=True`` to also fetch
    ``oracc_html_translations.zip`` (130 MB — needed if you want English
    translations in parsed output without live web requests).

    Set ``include_json_zips=True`` to also fetch ``oracc_jsonzip_all.zip`` (raw
    ORACC JSON, needed only for ``parse_project()``).

    All transport ZIPs are deleted after extraction.

    By default the newest version of the dataset is used. Data extracted from
    an older version is downloaded again (and overwritten) when the newer
    version changed that file; unchanged files are skipped.

    Args:
        url:                   Record URL of a specific dataset version, e.g.
                               ``https://zenodo.org/records/24336925``. Defaults
                               to ``settings.zenodo_url()``: the pinned
                               ``ZENODO_RECORD_URL`` if set, else the newest version.
        dest:                  Directory for temporary download files. Defaults to ``data_dir()``.
        include_translations:  Also download and extract the HTML translation cache.
        include_json_zips:     Also download and extract the raw ORACC JSON ZIPs.
    """
    dest = dest or data_dir()

    wanted = {"catalogues.zip"}
    if include_translations:
        wanted.add("oracc_html_translations.zip")
    if include_json_zips:
        wanted.add("oracc_jsonzip_all.zip")

    print(f"Fetching file list from {url or zenodo_url()}...")
    try:
        record = get_zenodo_record(url)
    except Exception as e:
        print(f"ERROR: Could not fetch Zenodo record: {e}")
        sys.exit(1)
    record_id = str(record["id"])
    which = "requested" if (url or zenodo_is_pinned()) else "newest"
    print(f"Using dataset version: record {record_id} ({which}).")

    all_files = get_zenodo_files(url)
    if not all_files:
        print("No files found in this Zenodo record.")
        sys.exit(1)

    def _already_extracted(filename: str) -> bool:
        if filename == "oracc_html_translations.zip":
            return (translations_dir() / ".translations_complete").exists()
        if filename == "catalogues.zip":
            return catalogue_dir().exists() and any(catalogue_dir().glob("*.csv"))
        if filename == "oracc_jsonzip_all.zip":
            return jsonzip_dir().exists() and any(jsonzip_dir().glob("*.zip"))
        return False

    state = _load_state()

    def _up_to_date(f: dict) -> bool:
        recorded = state.get(f["filename"], {}).get("checksum")
        return _already_extracted(f["filename"]) and recorded == f["checksum"]

    files = [f for f in all_files if f["filename"] in wanted]

    print(f"Dataset files ({len(files)}):")
    for f in files:
        print(f"  {f['filename']} ({f['size'] / (1024 * 1024):.1f} MB)")

    extractors = {
        "oracc_jsonzip_all.zip": lambda p, ow: extract_jsonzip_archive(p, jsonzip_dir(), overwrite=ow),
        "oracc_html_translations.zip": lambda p, ow: extract_data_archive(
            p, translations_dir(), "HTML translations", overwrite=ow),
        "catalogues.zip": lambda p, ow: extract_data_archive(p, catalogue_dir(), "catalogues", overwrite=ow),
    }

    dest.mkdir(parents=True, exist_ok=True)
    for f in files:
        name = f["filename"]
        if _up_to_date(f):
            print(f"  [OK] {name} already extracted from this version, skipping")
            continue
        dest_path = dest / name
        if dest_path.exists() and _md5_matches(dest_path, f["checksum"]):
            print(f"  [OK] {name} already downloaded, extracting...")
        else:
            download_file(f["url"], dest_path, desc=name)
            if not _md5_matches(dest_path, f["checksum"]):
                dest_path.unlink()
                print(f"ERROR: {name} download is incomplete or corrupt (checksum mismatch). Please retry.")
                sys.exit(1)
        # Data from another version (or of unknown version) is replaced.
        extractors[name](dest_path, _already_extracted(name))
        if name == "oracc_html_translations.zip":
            (translations_dir() / ".translations_complete").touch()
        dest_path.unlink()
        _record_state(name, record_id, f["checksum"])

    _report_stale_word_csvs(all_files)
    print(f"\n[OK] Done. Data is ready in {dest}")


def _report_stale_word_csvs(record_files: list[dict]) -> None:
    """Tell the user which word-CSV folders on disk are older than this version.

    Word CSVs are never replaced automatically (they may be in use, and a
    project's folder is only fetched once); deleting a folder makes the next
    ``parse_project()`` download the current files.
    """
    current = {f["filename"]: f["checksum"] for f in record_files}
    stale = sorted(
        name[:-4]
        for name, info in _load_state().items()
        if name not in {"catalogues.zip", "oracc_html_translations.zip", "oracc_jsonzip_all.zip"}
        and name in current and info.get("checksum") != current[name]
    )
    if not stale:
        return
    root = word_csv_dir()
    print("\nNOTE: a newer dataset version changed the word CSVs of: " + ", ".join(stale) + ".")
    print(f"To use the new files, delete these projects' folders in {root} "
          f"(e.g. {stale[0]}, {stale[0]}-*); they are downloaded again on the next parse_project().")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", "-u", default=None,
                        help="Record URL of a specific dataset version (default: the newest version)")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument(
        "--include-json-zips",
        action="store_true",
        default=False,
        help="Also download raw ORACC JSON ZIPs (needed for parse_project())",
    )
    args = parser.parse_args()
    fetch_data(
        url=args.url,
        dest=Path(args.output) if args.output else None,
        include_json_zips=args.include_json_zips,
    )
