"""
Upload oracc-parser data files to Zenodo.

Creates a new Zenodo deposit, uploads data files, adds metadata,
and publishes. Requires ZENODO_ACCESS_TOKEN in the environment or .env.

Usage:
    python scripts/upload_to_zenodo.py
"""

import os
import sys
import json
import zipfile
from pathlib import Path

import requests
from tqdm import tqdm

# Load token
TOKEN = os.getenv("ZENODO_ACCESS_TOKEN")

if not TOKEN:
    print("ERROR: ZENODO_ACCESS_TOKEN not found in environment or .env")
    sys.exit(1)

BASE_URL = "https://zenodo.org/api"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def create_deposit():
    """Create a new empty Zenodo deposit."""
    r = requests.post(
        f"{BASE_URL}/deposit/depositions",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={},
    )
    r.raise_for_status()
    dep = r.json()
    print(f"✓ Created deposit {dep['id']}")
    print(f"  URL: {dep['links']['html']}")
    return dep


def upload_file(deposit_id, bucket_url, filepath: Path, display_name: str = None):
    """Upload a single file to a Zenodo deposit."""
    name = display_name or filepath.name
    size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"  Uploading {name} ({size_mb:.1f} MB)...")

    with open(filepath, "rb") as fp:
        r = requests.put(
            f"{bucket_url}/{name}",
            headers=HEADERS,
            data=fp,
        )
    r.raise_for_status()
    print(f"  ✓ {name} uploaded")
    return r.json()


def set_metadata(deposit_id):
    """Set Zenodo metadata on the deposit."""
    metadata = {
        "metadata": {
            "title": "oracc-parser: Pre-downloaded ORACC Data for Cuneiform NLP",
            "upload_type": "dataset",
            "description": (
                "<p>Pre-downloaded and cached data for the "
                "<a href='https://github.com/shaharspencer/oracc-parser'>oracc-parser</a> Python package.</p>"
                "<p>Contains:</p>"
                "<ul>"
                "<li><b>oracc_jsonzip_all.zip</b> — 139 ORACC project JSON data bundles</li>"
                "<li><b>oracc_html_translations.zip</b> — 22,999 cached English translation HTML pages</li>"
                "<li><b>plaides_scraped_data.zip</b> — Cached Pleiades geographical data for city provenance</li>"
                "</ul>"
                "<p>Download these files to enable oracc-parser to work entirely offline, "
                "without hitting ORACC or Pleiades servers.</p>"
                "<p>Usage: <code>python scripts/download_zenodo_data.py</code></p>"
            ),
            "creators": [{"name": "Spencer, Shahar", "affiliation": "Hebrew University of Jerusalem"}],
            "keywords": [
                "ORACC", "cuneiform", "Akkadian", "NLP",
                "digital humanities", "Assyriology", "ancient Near East",
            ],
            "license": "MIT",
            "access_right": "open",
            "related_identifiers": [
                {
                    "identifier": "https://github.com/shaharspencer/oracc-parser",
                    "relation": "isSupplementTo",
                    "scheme": "url",
                }
            ],
            "notes": (
                "This dataset is intended to be used with the oracc-parser Python package. "
                "See https://github.com/shaharspencer/oracc-parser for documentation."
            ),
        }
    }
    r = requests.put(
        f"{BASE_URL}/deposit/depositions/{deposit_id}",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=metadata,
    )
    r.raise_for_status()
    print(f"✓ Metadata set")
    return r.json()


def publish(deposit_id):
    """Publish the deposit (makes it permanent!)."""
    r = requests.post(
        f"{BASE_URL}/deposit/depositions/{deposit_id}/actions/publish",
        headers=HEADERS,
    )
    r.raise_for_status()
    result = r.json()
    doi = result.get("doi", "N/A")
    record_url = result["links"]["record_html"]
    print(f"\n✓ Published!")
    print(f"  DOI: {doi}")
    print(f"  URL: {record_url}")
    return result


def bundle_jsonzips(output_path: Path):
    """Bundle all ORACC project ZIPs into one ZIP."""
    jsonzip_dir = DATA_DIR / "jsonzip"
    if not jsonzip_dir.exists():
        print(f"  ⚠ {jsonzip_dir} not found, skipping")
        return None

    zips = sorted(jsonzip_dir.glob("*.zip"))
    print(f"  Bundling {len(zips)} ORACC project ZIPs...")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_STORED) as zf:
        for z in tqdm(zips, desc="  Packing"):
            zf.write(z, f"jsonzip/{z.name}")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.0f} MB)")
    return output_path


def bundle_html_pages(output_path: Path):
    """Bundle cached HTML translation pages into one ZIP."""
    html_dir = DATA_DIR / "oracc_html_pages"
    if not html_dir.exists():
        print(f"  ⚠ {html_dir} not found, skipping")
        return None

    files = list(html_dir.rglob("*"))
    files = [f for f in files if f.is_file()]
    print(f"  Bundling {len(files)} HTML translation pages...")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in tqdm(files, desc="  Packing"):
            arcname = f.relative_to(DATA_DIR)
            zf.write(f, str(arcname))

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Created {output_path.name} ({size_mb:.0f} MB)")
    return output_path


def main():
    print("=" * 60)
    print("  oracc-parser → Zenodo Upload")
    print("=" * 60)
    print()

    # 1. Prepare bundles
    print("1. Preparing data bundles...")
    tmp_dir = DATA_DIR / "_zenodo_upload"
    tmp_dir.mkdir(exist_ok=True)

    files_to_upload = []

    # Pleiades data (already a zip)
    pleiades_zip = DATA_DIR / "plaides_scraped_data.zip"
    if pleiades_zip.exists():
        files_to_upload.append(pleiades_zip)
        print(f"  ✓ Pleiades ZIP ready ({pleiades_zip.stat().st_size/1024/1024:.1f} MB)")

    # Bundle ORACC JSONZIPs
    jsonzip_bundle = tmp_dir / "oracc_jsonzip_all.zip"
    if not jsonzip_bundle.exists():
        result = bundle_jsonzips(jsonzip_bundle)
        if result:
            files_to_upload.append(result)
    else:
        files_to_upload.append(jsonzip_bundle)
        print(f"  ✓ ORACC ZIP bundle already exists ({jsonzip_bundle.stat().st_size/1024/1024:.0f} MB)")

    # Bundle HTML translations
    html_bundle = tmp_dir / "oracc_html_translations.zip"
    if not html_bundle.exists():
        result = bundle_html_pages(html_bundle)
        if result:
            files_to_upload.append(result)
    else:
        files_to_upload.append(html_bundle)
        print(f"  ✓ HTML bundle already exists ({html_bundle.stat().st_size/1024/1024:.0f} MB)")

    print(f"\n  Total files to upload: {len(files_to_upload)}")
    total_mb = sum(f.stat().st_size for f in files_to_upload) / (1024 * 1024)
    print(f"  Total size: {total_mb:.0f} MB")

    # 2. Create deposit
    print("\n2. Creating Zenodo deposit...")
    deposit = create_deposit()
    deposit_id = deposit["id"]
    bucket_url = deposit["links"]["bucket"]

    # 3. Upload files
    print("\n3. Uploading files...")
    for f in files_to_upload:
        upload_file(deposit_id, bucket_url, f)

    # 4. Set metadata
    print("\n4. Setting metadata...")
    set_metadata(deposit_id)

    # 5. Publish
    print("\n5. Publishing...")
    result = publish(deposit_id)

    # 6. Save info
    info = {
        "deposit_id": deposit_id,
        "doi": result.get("doi"),
        "record_url": result["links"]["record_html"],
        "record_id": result["id"],
        "files": [f.name for f in files_to_upload],
    }
    info_path = tmp_dir / "zenodo_upload_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)
    print(f"\n  Upload info saved to {info_path}")

    print("\n" + "=" * 60)
    print(f"  Done! Your data is live at:")
    print(f"  {result['links']['record_html']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
