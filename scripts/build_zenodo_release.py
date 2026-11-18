"""
Build the files for a new Zenodo dataset version.

Starts from a local copy of the previous release (every file of the Zenodo
record, e.g. downloaded into ``oracc_data/_zenodo_24336925``), re-fetches the
given projects from the ORACC servers, and writes updated archives:

* ``<umbrella>.zip``             word CSVs (one folder per sub-project)
* ``catalogues.zip``             one catalogue CSV per project
* ``oracc_jsonzip_all.zip``      raw ORACC JSON ZIPs (``jsonzip/<slug>.zip``)
* ``oracc_html_translations.zip`` cached ORACC HTML pages (``<project>/<id>.html``)

Archives that need no change are not rewritten. Empty word CSVs (texts whose
ORACC JSON has no words) are dropped unless ``--keep-empty`` is passed. A
completeness check against ``projects_metadata.csv`` runs at the end, and
``MANIFEST.json`` lists every file of the new version with its md5, marking which
ones changed.

Usage:
    python scripts/build_zenodo_release.py \\
        --base oracc_data/_zenodo_24336925 \\
        --out  oracc_data/_release \\
        --project atae/saab0509

Nothing is uploaded. See ``scripts/upload_to_zenodo.py --new-version`` for that.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from oracc_parser.download.extract_jsons import extract_from_zip
from oracc_parser.download.oracc_download import download_zip
from oracc_parser.download.release_check import check_completeness
from oracc_parser.io.word_csv import catalogue_to_dataframe, record_to_word_dataframe
from oracc_parser.metadata.populate import populate_metadata
from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import TabletRecord
from oracc_parser.parsing.parse_content import parse_json_text
from oracc_parser.parsing.translation import ORACC_HTML_URL, _download_html, _is_valid_html
from oracc_parser.utils.paths import normalize_project, project_slug

# The published word and catalogue CSVs use CRLF; keep new files consistent.
CSV_EOL = "\r\n"

# Files on the Zenodo record that are not word-CSV umbrella archives.
NON_UMBRELLA = {
    "catalogues.zip",
    "oracc_jsonzip_all.zip",
    "oracc_html_translations.zip",
    "plaides_scraped_data.zip",
}


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_empty_csv(data: bytes) -> bool:
    """True for a word CSV with no data rows (blank, or header only)."""
    lines = [ln for ln in data.decode("utf-8", errors="replace").splitlines() if ln.strip()]
    return len(lines) <= 1


# ---------------------------------------------------------------------------
# 1. Fetch and convert projects from ORACC
# ---------------------------------------------------------------------------


def build_project(project: str, stage: Path, translations: bool) -> dict:
    """Download one project from ORACC and write its dataset files into ``stage``."""
    slug = project_slug(project)
    jsonzip_dir = stage / "jsonzip"
    jsonzip_dir.mkdir(parents=True, exist_ok=True)

    zip_path = download_zip(project, output_dir=jsonzip_dir)
    if not zip_path:
        raise RuntimeError(f"could not download {project} from ORACC")
    data = extract_from_zip(project, zip_dir=jsonzip_dir)
    members = (data.project_catalogue or {}).get("members", {})
    if not members:
        raise RuntimeError(f"{project}: catalogue.json has no members")

    cat_path = stage / "catalogues" / f"{slug}.csv"
    cat_path.parent.mkdir(parents=True, exist_ok=True)
    catalogue_to_dataframe(project, members).to_csv(
        cat_path, index=False, encoding="utf-8", lineterminator=CSV_EOL
    )

    word_dir = stage / "oracc_csvs" / slug
    word_dir.mkdir(parents=True, exist_ok=True)
    config = RunConfig(fetch_translations=False)
    written, empty = [], []
    for js in tqdm(data.json_files, desc=f"Converting {project}"):
        text_id = js.get("textid", "")
        record = TabletRecord()
        record.content = parse_json_text(js, config)
        record.metadata = populate_metadata(members.get(text_id, {}), text_id, project)
        df = record_to_word_dataframe(record)
        if df.empty:
            empty.append(text_id)
            continue
        df.to_csv(word_dir / f"{text_id}.csv", index=False, encoding="utf-8", lineterminator=CSV_EOL)
        written.append(text_id)

    fetched_html = 0
    if translations:
        html_dir = stage / "translations" / project
        html_dir.mkdir(parents=True, exist_ok=True)
        for text_id in tqdm(written, desc=f"Translations {project}"):
            target = html_dir / f"{text_id}.html"
            if target.exists():
                fetched_html += 1
                continue
            html = _download_html(f"{ORACC_HTML_URL}/{project}/{text_id}/html")
            if html and _is_valid_html(html):
                target.write_text(html, encoding="utf-8")
                fetched_html += 1

    info = {
        "project": project,
        "catalogue_rows": len(members),
        "corpus_json": len(data.json_files),
        "word_csvs": len(written),
        "no_words": empty,
        "translation_pages": fetched_html,
    }
    print(json.dumps(info))
    return info


# ---------------------------------------------------------------------------
# 2. Rewrite archives
# ---------------------------------------------------------------------------


def rewrite_zip(
    src: Path | None,
    dest: Path,
    replace_prefixes: list[str],
    new_files: dict[str, Path],
    drop_empty: bool,
) -> list[str]:
    """Copy ``src`` into ``dest`` minus ``replace_prefixes`` (and empty CSVs), plus ``new_files``.

    Returns the list of dropped empty CSV member names.
    """
    dropped = []
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as out:
        if src is not None and src.exists():
            with zipfile.ZipFile(src) as z:
                for info in z.infolist():
                    name = info.filename
                    if any(name.startswith(p) for p in replace_prefixes):
                        continue
                    data = z.read(info)
                    if drop_empty and name.endswith(".csv") and is_empty_csv(data):
                        dropped.append(name)
                        continue
                    out.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        for arcname, path in sorted(new_files.items()):
            out.write(path, arcname)
    return dropped


def umbrella_has_empty_csvs(src: Path) -> bool:
    # Only small members can be header-only, so skip reading the rest.
    with zipfile.ZipFile(src) as z:
        return any(
            i.filename.endswith(".csv") and i.file_size < 512 and is_empty_csv(z.read(i))
            for i in z.infolist()
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, type=Path, help="Folder with every file of the previous Zenodo version")
    ap.add_argument("--out", required=True, type=Path, help="Output folder (staging/ and upload/ are created inside)")
    ap.add_argument("--project", action="append", default=[], help="Project to (re)fetch from ORACC; repeatable")
    ap.add_argument("--keep-empty", action="store_true", help="Keep word CSVs with no rows")
    ap.add_argument("--no-translations", action="store_true", help="Do not fetch HTML translation pages")
    ap.add_argument("--allow-missing", action="append", default=[], help="Project excluded on purpose (completeness check)")
    args = ap.parse_args()

    logging.getLogger("oracc_parser").setLevel(logging.WARNING)
    base, out = args.base, args.out
    stage, upload = out / "staging", out / "upload"
    upload.mkdir(parents=True, exist_ok=True)
    projects = [normalize_project(p) for p in args.project]
    drop_empty = not args.keep_empty

    # 1. Fetch projects
    built = [build_project(p, stage, translations=not args.no_translations) for p in projects]

    # 2. Decide which archives change
    by_umbrella: dict[str, list[str]] = defaultdict(list)
    for p in projects:
        by_umbrella[project_slug(p).split("-")[0]].append(p)

    changed: dict[str, dict] = {}
    umbrellas = sorted(f.name for f in base.glob("*.zip") if f.name not in NON_UMBRELLA)
    for name in sorted(set(umbrellas) | {f"{u}.zip" for u in by_umbrella}):
        umbrella = name[:-4]
        rebuilt = by_umbrella.get(umbrella, [])
        src = base / name
        if not rebuilt and not (drop_empty and src.exists() and umbrella_has_empty_csvs(src)):
            continue
        new_files = {}
        for p in rebuilt:
            slug = project_slug(p)
            for f in sorted((stage / "oracc_csvs" / slug).glob("*.csv")):
                new_files[f"{slug}/{f.name}"] = f
        dropped = rewrite_zip(
            src if src.exists() else None, upload / name,
            [f"{project_slug(p)}/" for p in rebuilt], new_files, drop_empty,
        )
        changed[name] = {"added_projects": rebuilt, "dropped_empty_csvs": dropped}

    if projects:
        new_cats = {f"{project_slug(p)}.csv": stage / "catalogues" / f"{project_slug(p)}.csv" for p in projects}
        rewrite_zip(base / "catalogues.zip", upload / "catalogues.zip", list(new_cats), new_cats, False)
        changed["catalogues.zip"] = {"added_projects": projects}

        new_js = {f"jsonzip/{project_slug(p)}.zip": stage / "jsonzip" / f"{project_slug(p)}.zip" for p in projects}
        rewrite_zip(base / "oracc_jsonzip_all.zip", upload / "oracc_jsonzip_all.zip", list(new_js), new_js, False)
        changed["oracc_jsonzip_all.zip"] = {"added_projects": projects}

        if not args.no_translations:
            new_html = {}
            for p in projects:
                for f in sorted((stage / "translations" / p).glob("*.html")):
                    new_html[f"{p}/{f.name}"] = f
            if new_html:
                rewrite_zip(
                    base / "oracc_html_translations.zip", upload / "oracc_html_translations.zip",
                    [f"{p}/" for p in projects], new_html, False,
                )
                changed["oracc_html_translations.zip"] = {"added_projects": projects}

    # 3. Completeness check on the resulting file set
    def final(name: str) -> Path:
        return upload / name if (upload / name).exists() else base / name

    with zipfile.ZipFile(final("catalogues.zip")) as z:
        cat_slugs = {Path(n).stem for n in z.namelist() if n.endswith(".csv")}
    with zipfile.ZipFile(final("oracc_jsonzip_all.zip")) as z:
        js_slugs = {Path(n).stem for n in z.namelist() if n.endswith(".zip")}
    word_slugs = set()
    for name in sorted(set(umbrellas) | {f"{u}.zip" for u in by_umbrella}):
        with zipfile.ZipFile(final(name)) as z:
            word_slugs |= {n.split("/")[0] for n in z.namelist() if n.endswith(".csv")}

    report = check_completeness(cat_slugs, word_slugs, js_slugs, allow_missing=set(args.allow_missing))
    print("\nCompleteness check:\n" + report.summary())

    # 4. Manifest
    manifest = {"base": str(base), "projects_rebuilt": built, "changed": changed, "files": []}
    for f in sorted(base.iterdir()):
        if f.is_file():
            p = final(f.name)
            manifest["files"].append({"filename": f.name, "changed": f.name in changed,
                                      "size": p.stat().st_size, "md5": md5(p)})
    for name in sorted(set(changed) - {f.name for f in base.iterdir()}):
        p = upload / name
        manifest["files"].append({"filename": name, "changed": True, "new": True,
                                  "size": p.stat().st_size, "md5": md5(p)})
    manifest["completeness"] = {
        "ok": report.ok,
        "missing_catalogue": report.missing_catalogue,
        "missing_word_csvs": report.missing_word_csvs,
        "missing_jsonzip": report.missing_jsonzip,
        "allowed_missing": report.allowed_missing,
    }
    (upload / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nChanged files written to {upload}:")
    for name, info in changed.items():
        print(f"  {name}: {info}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
