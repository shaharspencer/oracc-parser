"""
Download and extract pre-processed ORACC data from Zenodo.

By default only the word CSVs and project catalogues are downloaded — the
minimum needed to run all notebooks.  Pass ``include_json_zips=True`` to also
fetch the raw ORACC JSON ZIPs (needed only if you want to re-run the full
JSON processing pipeline via ``parse_project()``).

Can be called as:
    oracc-parser fetch-data
    python -m oracc_parser.download.fetch_data
    from oracc_parser.download.fetch_data import fetch_data
"""

import sys
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

from oracc_parser.settings import zenodo_url, data_dir, jsonzip_dir, word_csv_dir, catalogue_dir, cache_dir


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


def get_zenodo_files(record_url: str) -> list[dict]:
    """Fetch the list of files from a Zenodo record via its API."""
    record_id = record_url.rstrip("/").split("/")[-1]
    api_url = f"https://zenodo.org/api/records/{record_id}"
    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    files = resp.json().get("files", [])
    return [
        {
            "filename": f["key"],
            "size": f["size"],
            "url": f["links"]["self"],
            "checksum": f.get("checksum", ""),
        }
        for f in files
    ]


def extract_jsonzip_archive(archive_path: Path, dest_dir: Path) -> None:
    """Extract oracc_jsonzip_all.zip into dest_dir (the jsonzip folder).

    The archive contains entries like ``jsonzip/saao-saa01.zip``.
    Only the inner ``*.zip`` files are extracted — the ``jsonzip/`` prefix
    is stripped so they land directly in ``dest_dir``.
    """
    print(f"\n📂 Extracting project ZIPs from {archive_path.name} ...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as z:
        members = [m for m in z.namelist() if m.endswith(".zip")]
        for member in tqdm(members, desc="Extracting", unit="file"):
            filename = Path(member).name
            target = dest_dir / filename
            if target.exists():
                continue
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())
    print(f"✅ Extracted {len(members)} project ZIPs to {dest_dir}")


def extract_data_archive(archive_path: Path, dest_dir: Path, label: str) -> None:
    """Extract a flat CSV archive (oracc_csvs.zip or catalogues.zip) into dest_dir.

    Handles both archive layouts:
    - Contents directly at the root (``saao-saa01/P123456.csv``)
    - Wrapped in a single top-level folder (``oracc_csvs/saao-saa01/P123456.csv``)
    """
    print(f"\n📂 Extracting {archive_path.name} ...")
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
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    print(f"✅ Extracted {len(files)} files to {dest_dir}")


def extract_project_csvs(
    project: str,
    zip_path: Path | None = None,
    dest_dir: Path | None = None,
) -> Path:
    """Extract one project's word CSVs from ``oracc_csvs.zip`` on demand.

    Skips extraction if the project directory already exists and contains CSV
    files (i.e. the project was already extracted in a previous call).

    Args:
        project:  ORACC project path, e.g. ``"saao/saa01"``.
        zip_path: Path to ``oracc_csvs.zip``. Defaults to ``data_dir() / "oracc_csvs.zip"``.
        dest_dir: Root directory where project folders are extracted.
                  Defaults to ``word_csv_dir()``.

    Returns:
        Path to the extracted project directory.

    Raises:
        FileNotFoundError: If ``oracc_csvs.zip`` cannot be found.
        ValueError: If no CSV files for the project exist in the archive.
    """
    zip_path = zip_path or (data_dir() / "oracc_csvs.zip")
    dest_dir = dest_dir or word_csv_dir()

    project_slug = project.replace("/", "-")
    project_dir = dest_dir / project_slug

    if project_dir.exists() and any(project_dir.glob("*.csv")):
        return project_dir

    if not zip_path.exists():
        raise FileNotFoundError(
            f"oracc_csvs.zip not found at {zip_path}. Run fetch_data() first."
        )

    print(f"Extracting {project} from {zip_path.name}...")
    project_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()

        # Detect and strip a single top-level prefix (same logic as extract_data_archive)
        top_dirs = {n.split("/")[0] for n in names if "/" in n}
        prefix = ""
        if len(top_dirs) == 1:
            candidate = top_dirs.pop() + "/"
            if all(n.startswith(candidate) or n == candidate.rstrip("/") for n in names):
                prefix = candidate

        project_prefix = f"{prefix}{project_slug}/"
        members = [n for n in names if n.startswith(project_prefix) and not n.endswith("/")]

        if not members:
            raise ValueError(f"No CSVs found for '{project}' in {zip_path.name}")

        for member in members:
            rel_path = member[len(project_prefix):]
            target = project_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(member) as src, open(target, "wb") as dst:
                dst.write(src.read())

    print(f"  -> Extracted {len(members)} CSVs for {project}")
    return project_dir


def fetch_data(
    url: str | None = None,
    dest: Path | None = None,
    include_json_zips: bool = False,
) -> None:
    """Download pre-processed ORACC data from Zenodo and extract it.

    By default downloads only ``oracc_csvs.zip`` and ``catalogues.zip`` —
    the files needed for all standard notebook workflows.  Set
    ``include_json_zips=True`` to also fetch ``oracc_jsonzip_all.zip`` (raw
    ORACC JSON, needed only for ``parse_project()``).

    All transport ZIPs are deleted after extraction.

    Args:
        url:               Zenodo record URL. Defaults to ``ZENODO_RECORD_URL``.
        dest:              Directory for temporary download files. Defaults to ``data_dir()``.
        include_json_zips: Also download and extract the raw ORACC JSON ZIPs.
    """
    url = url or zenodo_url()
    dest = dest or data_dir()

    if "XXXXXXX" in url:
        print("ERROR: Zenodo URL not configured yet!")
        print("Set ORACC_ZENODO_RECORD_URL in your .env or pass --url explicitly.")
        sys.exit(1)

    # Files to fetch by default; json zips are opt-in
    wanted = {"oracc_csvs.zip", "catalogues.zip", "oracc_html_translations.zip"}
    if include_json_zips:
        wanted.add("oracc_jsonzip_all.zip")

    print(f"Fetching file list from {url}...")
    try:
        all_files = get_zenodo_files(url)
    except Exception as e:
        print(f"ERROR: Could not fetch Zenodo record: {e}")
        sys.exit(1)

    if not all_files:
        print("No files found in this Zenodo record.")
        sys.exit(1)

    # For each file, check whether its extracted output already exists on disk
    # so we don't re-download and re-extract on subsequent calls.
    def _already_extracted(filename: str) -> bool:
        if filename == "oracc_html_translations.zip":
            return any((cache_dir() / "html").rglob("*.html"))
        if filename == "catalogues.zip":
            return catalogue_dir().exists() and any(catalogue_dir().glob("*.csv"))
        if filename == "oracc_jsonzip_all.zip":
            return jsonzip_dir().exists() and any(jsonzip_dir().glob("*.zip"))
        if filename == "oracc_csvs.zip":
            return (dest / "oracc_csvs.zip").exists()
        return False

    files = [f for f in all_files if f["filename"] in wanted]
    skipped = [f["filename"] for f in all_files if f["filename"] not in wanted]

    print(f"Downloading {len(files)} file(s):")
    for f in files:
        print(f"  {f['filename']} ({f['size'] / (1024 * 1024):.1f} MB)")
    if skipped:
        print(f"Skipping: {', '.join(skipped)}")

    dest.mkdir(parents=True, exist_ok=True)
    print(f"\nDownloading to {dest}...")
    for f in files:
        dest_path = dest / f["filename"]
        if _already_extracted(f["filename"]):
            print(f"  ✓ {f['filename']} already extracted, skipping")
            continue
        if dest_path.exists():
            print(f"  ✓ {f['filename']} already downloaded, extracting...")
        else:
            download_file(f["url"], dest_path, desc=f["filename"])

    # Extract and delete each transport ZIP
    combined_zip = dest / "oracc_jsonzip_all.zip"
    if combined_zip.exists():
        extract_jsonzip_archive(combined_zip, jsonzip_dir())
        combined_zip.unlink()
        print(f"🗑️  Deleted {combined_zip.name}")

    # HTML translations — extract into the translation cache, then delete
    translations_zip = dest / "oracc_html_translations.zip"
    if translations_zip.exists():
        extract_data_archive(translations_zip, cache_dir() / "html", "HTML translations")
        translations_zip.unlink()
        print(f"🗑️  Deleted {translations_zip.name}")

    # oracc_csvs.zip is kept on disk for lazy per-project extraction
    if (dest / "oracc_csvs.zip").exists():
        print(f"  ✓ oracc_csvs.zip ready (projects will be extracted on demand)")

    # Catalogues are small — extract all at once and delete the transport zip
    catalogues_zip = dest / "catalogues.zip"
    if catalogues_zip.exists():
        extract_data_archive(catalogues_zip, catalogue_dir(), "catalogues")
        catalogues_zip.unlink()
        print(f"🗑️  Deleted {catalogues_zip.name}")

    print(f"\n✓ Done. Data is in {dest}")
    print("You can now use oracc-parser with this data.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", "-u", default=None)
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
