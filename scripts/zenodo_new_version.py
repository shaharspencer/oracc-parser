"""
Create a new version of the oracc-parser Zenodo dataset from a release build.

Reads ``MANIFEST.json`` written by ``scripts/build_zenodo_release.py`` and, on
Zenodo, creates a new version of ``--record`` (the latest published version).
Zenodo copies every file of the previous version into the new draft; this
script replaces only the files the manifest marks as changed, updates the
publication date (and optionally the version label and a change note), then
checks every file's md5 against the manifest.

Three levels, from safest:

    # 1. Dry run (default): print the plan, touch nothing on Zenodo.
    python scripts/zenodo_new_version.py --upload-dir oracc_data/_release/upload

    # 2. Create and fill the draft, but leave it unpublished for review on zenodo.org.
    python scripts/zenodo_new_version.py --upload-dir oracc_data/_release/upload --create-draft

    # 3. Same, then publish (permanent: a published version cannot be deleted).
    python scripts/zenodo_new_version.py --upload-dir oracc_data/_release/upload --create-draft --publish

Requires ``ZENODO_ACCESS_TOKEN`` (scopes: deposit:write, deposit:actions) in the
environment for levels 2 and 3. After publishing, point
``oracc_parser/settings.py::ZENODO_RECORD_URL`` at the new record.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

API = "https://zenodo.org/api"
DEFAULT_RECORD = "24336925"


def _session(token: str) -> requests.Session:
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def _check(r: requests.Response) -> dict:
    if not r.ok:
        raise SystemExit(f"Zenodo API error {r.status_code} for {r.request.method} {r.url}:\n{r.text[:2000]}")
    return r.json() if r.content else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upload-dir", required=True, type=Path, help="Folder with MANIFEST.json and the changed files")
    ap.add_argument("--record", default=DEFAULT_RECORD, help="Latest published record id to version from")
    ap.add_argument("--version-label", default=None, help='Optional version string, e.g. "2026-11"')
    ap.add_argument("--notes-file", type=Path, default=None,
                    help="HTML/text appended to the description as a 'Changes in this version' note")
    ap.add_argument("--create-draft", action="store_true", help="Create and fill the new-version draft")
    ap.add_argument("--publish", action="store_true", help="Publish the draft (requires --create-draft)")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="Proceed even if the manifest's completeness check failed")
    args = ap.parse_args()
    if args.publish and not args.create_draft:
        raise SystemExit("--publish requires --create-draft")

    manifest = json.loads((args.upload_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    changed = [f for f in manifest["files"] if f["changed"]]
    expected = {f["filename"]: f for f in manifest["files"]}

    print(f"Previous version: https://zenodo.org/records/{args.record}")
    print(f"Files in new version: {len(expected)}  (replaced/added: {len(changed)})")
    for f in changed:
        print(f"  {'add' if f.get('new') else 'replace'} {f['filename']:32s} {f['size'] / 1e6:9.1f} MB  md5 {f['md5']}")
    comp = manifest.get("completeness", {})
    if not comp.get("ok", False):
        print(f"\nCompleteness check FAILED in manifest: {comp}")
        if not args.allow_incomplete:
            print("Re-run the build with --allow-missing for intentional exclusions, or pass --allow-incomplete.")
            return 1

    if not args.create_draft:
        print("\nDry run only. Pass --create-draft to create the new-version draft on Zenodo.")
        return 0

    token = os.environ.get("ZENODO_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("ZENODO_ACCESS_TOKEN is not set.")
    s = _session(token)

    # 1. New version draft (Zenodo copies all files of the previous version).
    dep = _check(s.post(f"{API}/deposit/depositions/{args.record}/actions/newversion"))
    draft_url = dep["links"]["latest_draft"]
    draft = _check(s.get(draft_url))
    print(f"\nDraft created: {draft['links']['html']}")

    # 2. Replace changed files.
    existing = {f["filename"]: f for f in _check(s.get(f"{draft_url}/files"))}
    bucket = draft["links"]["bucket"]
    for f in changed:
        name = f["filename"]
        if name in existing:
            _check(s.delete(f"{draft_url}/files/{existing[name]['id']}"))
        path = args.upload_dir / name
        print(f"  uploading {name} ...", flush=True)
        with open(path, "rb") as fh:
            _check(s.put(f"{bucket}/{name}", data=fh, timeout=None))

    # 3. Metadata: keep the previous version's, bump the date, optional label/note.
    md = draft["metadata"]
    md["publication_date"] = dt.date.today().isoformat()
    if args.version_label:
        md["version"] = args.version_label
    if args.notes_file:
        note = args.notes_file.read_text(encoding="utf-8").strip()
        md["description"] = md.get("description", "") + f"<h3>Changes in this version</h3>{note}"
    md.pop("doi", None)  # Zenodo reserves a fresh DOI for the new version
    _check(s.put(draft_url, json={"metadata": md}))

    # 4. Verify the draft's file set against the manifest.
    files = {f["filename"]: f for f in _check(s.get(f"{draft_url}/files"))}
    problems = []
    for name, f in expected.items():
        got = files.get(name)
        if got is None:
            problems.append(f"missing {name}")
        elif got.get("checksum", "").removeprefix("md5:") != f["md5"]:
            problems.append(f"md5 mismatch {name}: {got.get('checksum')} != {f['md5']}")
    for name in set(files) - set(expected):
        problems.append(f"unexpected file {name}")
    if problems:
        print("\nDraft verification FAILED (draft left unpublished):\n  " + "\n  ".join(problems))
        return 1
    print(f"\nDraft verified: {len(files)} files, all md5s match the manifest.")

    if not args.publish:
        print("Draft left unpublished. Review it on Zenodo, then publish there or re-run with --publish.")
        return 0

    pub = _check(s.post(f"{draft_url}/actions/publish"))
    print(f"\nPublished: {pub['links']['record_html']}  DOI {pub.get('doi')}")
    print(f'Update oracc_parser/settings.py:  ZENODO_RECORD_URL: str = "https://zenodo.org/records/{pub["id"]}"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
