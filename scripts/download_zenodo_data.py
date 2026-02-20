"""
Download pre-processed data from Zenodo.

This script downloads the heavy data files (ORACC JSON ZIPs, HTML translations,
Pleiades data) from Zenodo instead of re-downloading from the original servers.

Usage:
    python scripts/download_zenodo_data.py
    python scripts/download_zenodo_data.py --output ./data
    python scripts/download_zenodo_data.py --url https://zenodo.org/records/XXXXX

This is the RECOMMENDED way to get the data. It:
  - Avoids unnecessary load on ORACC and Pleiades servers
  - Is faster than downloading + parsing from scratch
  - Ensures reproducible results with the exact same data
"""

import argparse
import os
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from oracc_parser.settings import zenodo_url, data_dir


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
    # Convert record URL to API URL
    # https://zenodo.org/records/123456 -> https://zenodo.org/api/records/123456
    record_id = record_url.rstrip("/").split("/")[-1]
    api_url = f"https://zenodo.org/api/records/{record_id}"

    resp = requests.get(api_url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    files = data.get("files", [])
    return [
        {
            "filename": f["key"],
            "size": f["size"],
            "url": f["links"]["self"],
            "checksum": f.get("checksum", ""),
        }
        for f in files
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Download pre-processed ORACC data from Zenodo."
    )
    parser.add_argument(
        "--url", "-u",
        default=None,
        help="Zenodo record URL (default: from .env or settings)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory for downloaded files (default: from .env or ./data)",
    )
    args = parser.parse_args()

    url = args.url or zenodo_url()
    dest = Path(args.output) if args.output else data_dir()

    if "XXXXXXX" in url:
        print("ERROR: Zenodo URL not configured yet!")
        print()
        print("To configure:")
        print("  1. Copy .env.example to .env")
        print("  2. Set ORACC_ZENODO_RECORD_URL to your Zenodo record URL")
        print("  Or pass --url directly:")
        print("  python scripts/download_zenodo_data.py --url https://zenodo.org/records/XXXXX")
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

    print(f"\n✓ All files downloaded to {dest}")
    print("\nYou can now run oracc-parser with this data:")
    print(f"  python main.py --project saao/saa01")


if __name__ == "__main__":
    main()
