"""
Download pre-processed data from Zenodo.

This is a thin shim for local use. The actual logic lives in
oracc_parser.download.fetch_data so it is available after `pip install`.

Usage:
    python scripts/download_zenodo_data.py
    python scripts/download_zenodo_data.py --output ./data
    python scripts/download_zenodo_data.py --url https://zenodo.org/records/XXXXX
"""

import argparse
from pathlib import Path

from oracc_parser.download.fetch_data import fetch_data


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
    fetch_data(
        url=args.url,
        dest=Path(args.output) if args.output else None,
    )


if __name__ == "__main__":
    main()
