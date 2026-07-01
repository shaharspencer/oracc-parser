"""
main.py — Entry point for running oracc-parser locally.

Usage:
    python main.py                          # Parse with defaults
    python main.py --project saao/saa01     # Parse a specific project
    python main.py --limit 5                # Only parse 5 texts
    python main.py --export-flat dataset.jsonl  # Export flat JSONL dataset
"""

from oracc_parser import (
    parse_project_from_oracc,
    RunConfig,
    get_metadata_table,
    get_full_flat_table,
    export_to_jsonl,
)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run oracc-parser pipeline locally."
    )
    parser.add_argument("--project", "-p", default="saao/saa01",
                        help="ORACC project to parse (default: saao/saa01)")
    parser.add_argument("--limit", "-n", type=int, default=None,
                        help="Only parse first N texts")
    parser.add_argument("--export-flat", type=str, default=None,
                        help="Export flat JSONL dataset to this path")
    parser.add_argument("--drop-missing", action="store_true",
                        help="Drop entirely missing signs [x]")
    parser.add_argument("--drop-damaged", action="store_true",
                        help="Drop damaged signs")
    parser.add_argument("--mask-pos", nargs="*", default=[],
                        help="POS tags to mask (e.g. PN DN GN)")
    args = parser.parse_args()

    config = RunConfig(
        drop_missing=args.drop_missing,
        drop_damaged=args.drop_damaged,
        mask_pos=args.mask_pos,
        limit=args.limit,
    )

    print(f"Parsing {args.project}...")
    records = parse_project_from_oracc(args.project, config=config)

    if not records:
        print("No records parsed.")
        return

    # Show metadata summary
    meta_df = get_metadata_table(records)
    print(f"\n=== Parsed {len(records)} tablets ===")
    print(meta_df.to_string(index=False, max_rows=10))

    # Export flat dataset if requested
    if args.export_flat:
        flat_df = get_full_flat_table(records)
        flat_df.to_json(args.export_flat, orient="records", lines=True,
                        force_ascii=False)
        print(f"\nFlat dataset exported to {args.export_flat}")
    else:
        # Default: export to JSONL
        output = export_to_jsonl(records, "output.jsonl")
        print(f"\nExported to {output}")


if __name__ == "__main__":
    main()
