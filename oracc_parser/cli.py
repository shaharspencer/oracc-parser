"""
Command-line interface for oracc-parser.

Usage:
    oracc-parser download --project saao/saa01
    oracc-parser download --lang akkadian
    oracc-parser parse --project saao/saa01 --format jsonl --output data.jsonl
    oracc-parser parse --project saao/saa01 --limit 5 --format csv --output data.csv
"""
from __future__ import annotations

import argparse
import sys

from oracc_parser.pipeline import export_to_csv, export_to_jsonl, parse_project
from oracc_parser.models.config import RunConfig
from oracc_parser.utils.logger import get_logger

logger = get_logger()


def main(argv: list[str] | None = None):
    """Entry point for the oracc-parser CLI."""
    parser = argparse.ArgumentParser(
        prog="oracc-parser",
        description="Download and parse ORACC cuneiform text projects.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --------------- download ---------------
    dl = subparsers.add_parser("download", help="Download a single ORACC project ZIP from the ORACC servers")
    dl.add_argument("--project", "-p", required=True, help="Project path, e.g. saao/saa01")

    # --------------- parse ---------------
    ps = subparsers.add_parser("parse", help="Parse a project and export results")
    ps.add_argument("--project", "-p", required=True, help="Project path")
    ps.add_argument(
        "--format",
        "-f",
        choices=["jsonl", "csv"],
        default="jsonl",
        help="Output format (default: jsonl)",
    )
    ps.add_argument(
        "--output", "-o", default="output.jsonl", help="Output file path"
    )
    ps.add_argument("--limit", "-n", type=int, help="Parse only first N texts")
    ps.add_argument(
        "--drop-missing",
        action="store_true",
        help="Drop entirely missing signs [x]",
    )
    ps.add_argument(
        "--drop-damaged",
        action="store_true",
        help="Drop damaged signs ⸢x⸣",
    )
    ps.add_argument(
        "--mask-pos",
        nargs="*",
        default=[],
        help="POS tags to mask (e.g. PN DN GN)",
    )
    ps.add_argument(
        "--from-oracc",
        action="store_true",
        help="Download from ORACC live servers instead of Zenodo (for projects not in the dataset)",
    )

    # --------------- fetch-data ---------------
    fd = subparsers.add_parser("fetch-data", help="Download pre-processed data from Zenodo")
    fd.add_argument("--url", "-u", default=None, help="Zenodo record URL")
    fd.add_argument("--output", "-o", default=None, help="Destination directory")

    # --------------- info ---------------
    subparsers.add_parser("info", help="Show bundled reference data summary")

    args = parser.parse_args(argv)

    if args.command == "download":
        _cmd_download(args)
    elif args.command == "fetch-data":
        _cmd_fetch_data(args)
    elif args.command == "parse":
        _cmd_parse(args)
    elif args.command == "info":
        _cmd_info()
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_fetch_data(args):
    """Handle the fetch-data command."""
    from pathlib import Path
    from oracc_parser.download.fetch_data import fetch_data

    fetch_data(
        url=args.url,
        dest=Path(args.output) if args.output else None,
    )


def _cmd_download(args):
    """Handle the download command."""
    from oracc_parser.download.oracc_download import download_zip

    path = download_zip(args.project)
    if path:
        print(f"Downloaded: {path}")
    else:
        print("Download failed.", file=sys.stderr)
        sys.exit(1)


def _cmd_parse(args):
    """Handle the parse command."""
    config = RunConfig(
        drop_missing=args.drop_missing,
        drop_damaged=args.drop_damaged,
        mask_pos=args.mask_pos,
        limit=args.limit,
    )

    records = parse_project(
        args.project, config=config, download_from_oracc_server=args.from_oracc
    )

    if not records:
        print("No records parsed.", file=sys.stderr)
        sys.exit(1)

    if args.format == "jsonl":
        path = export_to_jsonl(records, args.output)
    else:
        path = export_to_csv(records, args.output)

    print(f"Exported {len(records)} records to {path}")


def _cmd_info():
    """Show summary of bundled reference data."""
    from oracc_parser.pipeline import reference_data

    datasets = {
        "Provenance": reference_data.get_provenance,
        "Period mapping": reference_data.get_period_mapping,
        "Sign list": reference_data.get_sign_list,
        "POS tags": reference_data.get_pos_tags,
        "Languages": reference_data.get_languages,
        "Projects metadata": reference_data.get_projects_metadata,
    }

    for name, loader in datasets.items():
        try:
            df = loader()
            print(f"  {name}: {len(df)} rows, columns: {list(df.columns)}")
        except Exception as e:
            print(f"  {name}: Error loading - {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
