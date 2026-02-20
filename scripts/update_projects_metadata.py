#!/usr/bin/env python3
"""
Update the local projects_metadata.csv with the latest project list from ORACC.

Usage:
    python scripts/update_projects_metadata.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from oracc_parser.download.oracc_download import update_project_metadata
from oracc_parser.utils.logger import get_logger

logger = get_logger()

def main():
    print("Fetching live project list from ORACC...")
    new_projects = update_project_metadata()
    
    if new_projects:
        print(f"\n✅ Added {len(new_projects)} new projects:")
        for p in new_projects:
            print(f"   - {p}")
        print("\nYou can now download these projects using:")
        print("   oracc-parser download --project <project_name>")
    else:
        print("\n✨ Metadata is already up to date. No new projects found.")

if __name__ == "__main__":
    main()
