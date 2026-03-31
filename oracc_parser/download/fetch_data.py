"""
Download and extract pre-processed ORACC data from Zenodo.

This module downloads the heavy data files (ORACC JSON ZIPs, HTML translations,
Pleiades data) from Zenodo instead of re-downloading from the original servers.

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

from oracc_parser.settings import zenodo_url, data_dir, jsonzip_dir


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


def fetch_data(url: str | None = None, dest: Path | None = None) -> None:
    """Download all Zenodo data files and extract the project ZIP archive.

    Args:
        url:  Zenodo record URL. Defaults to the configured ``ORACC_ZENODO_RECORD_URL``.
        dest: Directory to download raw Zenodo files into. Defaults to ``data_dir()``.
    """
    url = url or zenodo_url()
    dest = dest or data_dir()

    if "XXXXXXX" in url:
        print("ERROR: Zenodo URL not configured yet!")
        print("Set ORACC_ZENODO_RECORD_URL in your .env or pass --url explicitly.")
        sys.exit(1)

    print(f"Fetching file list from {url}...")
    try:
        files = get_zenodo_files(url)
    except Exception as e:
        print(f"ERROR: Could not fetch Zenodo record: {e}")
        sys.exit(1)

    if not files:
        print("No files found in this Zenodo record.")
        sys.exit(1)

    print(f"Found {len(files)} file(s):")
    for f in files:
        size_mb = f["size"] / (1024 * 1024)
        print(f"  {f['filename']} ({size_mb:.1f} MB)")

    print(f"\nDownloading to {dest}...")
    for f in files:
        dest_path = dest / f["filename"]
        if dest_path.exists():
            print(f"  ✓ {f['filename']} already exists, skipping")
            continue
        download_file(f["url"], dest_path, desc=f["filename"])

    # Extract individual project ZIPs from the combined archive
    combined_zip = dest / "oracc_jsonzip_all.zip"
    if combined_zip.exists():
        extract_jsonzip_archive(combined_zip, jsonzip_dir())

    print(f"\n✓ All files downloaded to {dest}")
    print("\nYou can now use oracc-parser with this data.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--url", "-u", default=None)
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()
    fetch_data(
        url=args.url,
        dest=Path(args.output) if args.output else None,
    )
