"""
Script: Export all parsed data as a flat JSONL dataset.

This script processes all downloaded ORACC project ZIPs and exports
a single flat JSONL file suitable for releasing as a public dataset.

Usage:
    python scripts/export_dataset.py
    python scripts/export_dataset.py --output my_dataset.jsonl --limit 10
"""

import argparse
import os
from pathlib import Path

from oracc_parser import RunConfig, parse_project, get_full_flat_table
from oracc_parser.utils.paths import get_output_dir


def main():
    parser = argparse.ArgumentParser(
        description="Export all parsed ORACC data as a flat JSONL dataset."
    )
    parser.add_argument(
        "--output", "-o",
        default="oracc_dataset.jsonl",
        help="Output file path (default: oracc_dataset.jsonl)",
    )
    parser.add_argument(
        "--project", "-p",
        help="Parse a specific project (default: all downloaded)",
    )
    parser.add_argument(
        "--limit", "-n",
        type=int,
        help="Limit texts per project",
    )
    parser.add_argument(
        "--drop-missing",
        action="store_true",
        help="Drop missing signs [x]",
    )
    args = parser.parse_args()

    config = RunConfig(
        drop_missing=args.drop_missing,
        limit=args.limit,
    )

    if args.project:
        projects = [args.project]
    else:
        # Find all downloaded ZIPs
        zip_dir = get_output_dir() / "zips"
        if not zip_dir.exists():
            print(f"No downloaded ZIPs found at {zip_dir}")
            print("Run 'oracc-parser download' first.")
            return
        projects = [f.stem for f in zip_dir.glob("*.zip")]

    print(f"Processing {len(projects)} project(s)...")

    import pandas as pd
    all_rows = []

    for project in projects:
        print(f"\n--- {project} ---")
        try:
            records = parse_project(project, config=config, download=False)
            if records:
                df = get_full_flat_table(records)
                all_rows.append(df)
                print(f"  Parsed {len(records)} tablets")
        except Exception as e:
            print(f"  Error: {e}")

    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        combined.to_json(args.output, orient="records", lines=True,
                         force_ascii=False)
        print(f"\n✓ Exported {len(combined)} tablets to {args.output}")
    else:
        print("\nNo data to export.")


if __name__ == "__main__":
    main()
