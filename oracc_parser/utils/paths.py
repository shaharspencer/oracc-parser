"""
Cross-platform path utilities using importlib.resources.

Bundled reference CSVs are accessed via importlib.resources so they work
regardless of where the package is installed. Output/cache directories
are configurable.
"""
from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Bundled reference data (inside oracc_parser/enriched_data/)
# ---------------------------------------------------------------------------

_DATA_PKG = "oracc_parser.enriched_data"


def _data_file(filename: str) -> Path:
    """Return the path to a bundled reference CSV."""
    return resources.files(_DATA_PKG).joinpath(filename)


def get_sign_readings() -> pd.DataFrame:
    """Load the sign-readings lookup table."""
    return pd.read_csv(_data_file("sign_readings.csv"), dtype=str)


def get_pos_tags() -> pd.DataFrame:
    """Load the POS-tag meanings table."""
    return pd.read_csv(_data_file("pos_tags.csv"), dtype=str)


def get_languages() -> pd.DataFrame:
    """Load the languages summary table."""
    return pd.read_csv(_data_file("languages.csv"), dtype=str)


def get_projects_metadata() -> pd.DataFrame:
    """Load ORACC project metadata (project names, languages, etc.)."""
    return pd.read_csv(_data_file("projects_metadata.csv"), dtype=str)

def get_archives() -> pd.DataFrame:
    """Load the raw to normalized archive mapping."""
    return pd.read_csv(_data_file("raw_archive_values.csv"), dtype=str, keep_default_na=False)


def get_catalogue_columns() -> pd.DataFrame:
    """Load the grouped ORACC metadata columns reference table.

    Contains all catalogue column names found across ORACC projects, grouped
    by category (e.g. Publications, Museum Numbers, Provenance, etc.).
    """
    return pd.read_csv(_data_file("grouped_oracc_metadata_columns.csv"), dtype=str, keep_default_na=False)


def get_provenience(pleiades_only: bool = True) -> pd.DataFrame:
    """Load the consolidated provenance table (merged from two original CSVs).

    Args:
        pleiades_only: If True (default), return only rows that have a real
            Pleiades ID (a numeric string like ``"874754"``).  Rows with
            placeholder values such as ``"-"``, ``"?"``, or empty are dropped.
            Pass ``False`` to get the full table (used internally for pipeline
            provenience lookup).

    Returns:
        DataFrame with columns: ``raw_provenience``, ``normalized_city``,
        ``pleiades_id``, ``pleiades_title``, ``lat``, ``lon``.
    """
    df = pd.read_csv(_data_file("provenience.csv"), dtype=str)
    if pleiades_only:
        # Keep only rows whose pleiades_id is a clean numeric string
        df = df[df["pleiades_id"].str.strip().str.match(r"^\d+$", na=False)].copy()
        df = df.reset_index(drop=True)
    return df



def get_period_mapping() -> pd.DataFrame:
    """Load the period-to-year mapping table."""
    return pd.read_csv(_data_file("period_mapping.csv"))



def update_pos_tags_counts(
    word_csv_dir: Path | None = None,
    column_name: str = "corpus_count",
) -> pd.DataFrame:
    """Scan all word CSVs and update the bundled pos_tags.csv with corpus-wide counts.

    Rules applied:
    - Tags already in pos_tags.csv get a count column added (or overwritten if the
      column already exists).
    - Tags found in the corpus but absent from pos_tags.csv are appended as new rows
      with all metadata columns left blank for manual review.
    - Tags already in pos_tags.csv that no longer appear in the corpus receive a
      count of 0.

    The file is modified in place — existing columns and rows are never removed.

    Args:
        word_csv_dir: Root directory whose sub-directories each contain per-text
                      word CSV files.  Defaults to ``WORD_CSV_DIR`` from settings.
        column_name:  Name of the count column to add or update.  Change this to
                      record counts for a specific corpus snapshot or date, e.g.
                      ``"count_2026_06"``.  Defaults to ``"corpus_count"``.

    Returns:
        The updated DataFrame (also written to disk).
    """
    from collections import Counter
    from tqdm import tqdm

    if word_csv_dir is None:
        from oracc_parser.settings import WORD_CSV_DIR
        word_csv_dir = WORD_CSV_DIR

    word_csv_dir = Path(word_csv_dir)

    # --- Count raw_pos across every word CSV in every project directory ---
    counts: Counter = Counter()
    project_dirs = [d for d in sorted(word_csv_dir.iterdir()) if d.is_dir()]
    for project_dir in tqdm(project_dirs, desc="Counting POS tags", unit="project"):
        for csv_file in project_dir.glob("*.csv"):
            try:
                df = pd.read_csv(
                    csv_file,
                    usecols=["raw_pos"],
                    dtype=str,
                    keep_default_na=False,
                )
                counts.update(df["raw_pos"].tolist())
            except Exception:
                pass  # skip malformed files

    # --- Load existing pos_tags.csv ---
    pos_path = Path(_data_file("pos_tags.csv"))
    existing = pd.read_csv(pos_path, dtype=str, keep_default_na=False)
    tag_col = "POS-tag"

    # --- Build updated count column ---
    existing[column_name] = existing[tag_col].map(lambda t: str(counts.get(t, 0)))

    # --- Append any brand-new tags as blank rows ---
    known_tags = set(existing[tag_col].tolist())
    new_rows = [
        {tag_col: tag, column_name: str(count)}
        for tag, count in sorted(counts.items())
        if tag not in known_tags
    ]
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        existing = pd.concat([existing, new_df], ignore_index=True)

    existing.to_csv(pos_path, index=False, encoding="utf-8")
    return existing


def get_state_mapping() -> pd.DataFrame:
    """Load the project → state_supergroup mapping table.

    Columns: ``project``, ``match_type`` (``"prefix"`` or ``"exact"``),
    ``state_supergroup``.
    """
    return pd.read_csv(_data_file("state_supergroup_mapping.csv"), dtype=str, keep_default_na=False)


def update_state_mapping(catalogue_dir: Path | None = None) -> pd.DataFrame:
    """Scan all catalogue slugs and add any unmapped projects to the state mapping CSV.

    For each project slug found in ``catalogue_dir``:
    - If it is already covered by an exact row or a prefix row, it is left alone.
    - If it is not covered, a new exact row is appended with ``state_supergroup``
      left blank for manual completion.

    Modifies the bundled ``state_supergroup_mapping.csv`` in place.

    Args:
        catalogue_dir: Directory containing per-project catalogue CSV files.
                       Defaults to ``CATALOGUE_DIR`` from settings.

    Returns:
        The updated DataFrame (also written to disk).
    """
    if catalogue_dir is None:
        from oracc_parser.settings import CATALOGUE_DIR
        catalogue_dir = CATALOGUE_DIR

    catalogue_dir = Path(catalogue_dir)
    slugs = sorted(f.stem for f in catalogue_dir.glob("*.csv"))

    mapping_path = Path(_data_file("state_supergroup_mapping.csv"))
    df = pd.read_csv(mapping_path, dtype=str, keep_default_na=False)

    prefixes = df.loc[df["match_type"] == "prefix", "project"].tolist()
    exact_projects = set(df.loc[df["match_type"] == "exact", "project"].tolist())

    def _is_covered(slug: str) -> bool:
        if slug in exact_projects:
            return True
        return any(slug.startswith(p) for p in prefixes)

    new_rows = [
        {"project": slug, "match_type": "exact", "state_supergroup": ""}
        for slug in slugs
        if not _is_covered(slug)
    ]

    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)

    df.to_csv(mapping_path, index=False, encoding="utf-8")
    print(f"state_supergroup_mapping.csv: {len(df)} rows total, {len(new_rows)} new project(s) added")
    return df


def update_languages_counts(
    word_csv_dir: Path | None = None,
    column_name: str = "corpus_count",
) -> pd.DataFrame:
    """Scan all word CSVs and update languages.csv with corpus-wide language stats.

    For each language code found in the ``lang`` column across all word CSVs:
    - ``count`` is updated with the total number of word tokens for that language.
    - ``projects`` is updated with a comma-separated list of project slugs that
      contain at least one word in that language.
    - ``projects_count`` is updated with the number of such projects.
    - Language codes already in languages.csv have their stats columns overwritten.
    - Language codes not yet in languages.csv are appended as new rows with all
      metadata columns (``language_name``, ``dialect``, etc.) left blank for
      manual completion.

    Args:
        word_csv_dir: Root directory whose sub-directories each contain per-text
                      word CSV files.  Defaults to ``WORD_CSV_DIR`` from settings.
        column_name:  Unused — kept for API symmetry with ``update_pos_tags_counts``.
                      The columns updated are always ``count``, ``projects``, and
                      ``projects_count``.

    Returns:
        The updated DataFrame (also written to disk).
    """
    from collections import Counter, defaultdict
    from tqdm import tqdm

    if word_csv_dir is None:
        from oracc_parser.settings import WORD_CSV_DIR
        word_csv_dir = WORD_CSV_DIR

    word_csv_dir = Path(word_csv_dir)

    counts: Counter = Counter()
    projects_by_lang: defaultdict[str, set] = defaultdict(set)

    project_dirs = [d for d in sorted(word_csv_dir.iterdir()) if d.is_dir()]
    for project_dir in tqdm(project_dirs, desc="Counting languages", unit="project"):
        project_slug = project_dir.name
        for csv_file in project_dir.glob("*.csv"):
            try:
                df = pd.read_csv(
                    csv_file,
                    usecols=["lang"],
                    dtype=str,
                    keep_default_na=False,
                )
                lang_values = [v for v in df["lang"].tolist() if v.strip()]
                counts.update(lang_values)
                for lang in set(lang_values):
                    projects_by_lang[lang].add(project_slug)
            except Exception:
                pass

    lang_path = Path(_data_file("languages.csv"))
    existing = pd.read_csv(lang_path, dtype=str, keep_default_na=False)
    lang_col = "lang"

    existing["count"] = existing[lang_col].map(lambda t: str(counts.get(t, 0)))
    existing["projects"] = existing[lang_col].map(
        lambda t: ", ".join(sorted(projects_by_lang.get(t, set())))
    )
    existing["projects_count"] = existing[lang_col].map(
        lambda t: str(len(projects_by_lang.get(t, set())))
    )

    known_langs = set(existing[lang_col].tolist())
    new_rows = [
        {
            lang_col: lang,
            "language_name": "",
            "dialect": "",
            "Is_cuneiform": "",
            "Notes": "",
            "count": str(count),
            "projects": ", ".join(sorted(projects_by_lang[lang])),
            "projects_count": str(len(projects_by_lang[lang])),
        }
        for lang, count in sorted(counts.items())
        if lang not in known_langs
    ]
    if new_rows:
        new_df = pd.DataFrame(new_rows)
        existing = pd.concat([existing, new_df], ignore_index=True)

    existing.to_csv(lang_path, index=False, encoding="utf-8")
    rows_with_count = (existing["count"].astype(int, errors="ignore") > 0).sum()
    print(f"languages.csv: {len(existing)} rows total, {len(new_rows)} new language(s) added, {rows_with_count} with count > 0")
    return existing


def update_catalogue_columns(catalogue_dir: Path | None = None) -> pd.DataFrame:
    """Scan all catalogue CSVs and add any new column names to grouped_oracc_metadata_columns.csv.

    For each column header found across all catalogue CSVs:
    - If it is already in the ``Column`` field of the CSV, it is left alone.
    - If it is new, a row is appended with all other fields left blank for
      manual completion.

    Modifies ``grouped_oracc_metadata_columns.csv`` in place.

    Args:
        catalogue_dir: Directory containing per-project catalogue CSV files.
                       Defaults to ``CATALOGUE_DIR`` from settings.

    Returns:
        The updated DataFrame (also written to disk).
    """
    if catalogue_dir is None:
        from oracc_parser.settings import CATALOGUE_DIR
        catalogue_dir = CATALOGUE_DIR

    catalogue_dir = Path(catalogue_dir)

    all_columns: set[str] = set()
    for csv_file in sorted(catalogue_dir.glob("*.csv")):
        try:
            header = pd.read_csv(csv_file, nrows=0, dtype=str).columns.tolist()
            all_columns.update(header)
        except Exception:
            pass

    col_path = Path(_data_file("grouped_oracc_metadata_columns.csv"))
    existing = pd.read_csv(col_path, dtype=str, keep_default_na=False)
    known = set(existing["Column"].tolist())

    new_rows = [
        {"Group": "", "Column": col, "Description": "", "Subgroups": "",
         "Remove": "", "Why_remove": "", "Reviewed": "", "Comments": ""}
        for col in sorted(all_columns)
        if col not in known
    ]
    if new_rows:
        existing = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

    existing.to_csv(col_path, index=False, encoding="utf-8")
    print(f"grouped_oracc_metadata_columns.csv: {len(existing)} rows total, {len(new_rows)} new column(s) added")
    return existing


def update_period_mapping(catalogue_dir: Path | None = None) -> pd.DataFrame:
    """Scan all catalogue CSVs and add any unmapped period values to period_mapping.csv.

    For each unique raw value found in the ``period`` column across all catalogues:
    - If it is already in ``period_mapping.csv`` (case-insensitive), it is left alone.
    - If it is new, a row is appended with blank ``start_year`` and ``end_year``
      for manual completion.

    Modifies ``period_mapping.csv`` in place.

    Args:
        catalogue_dir: Directory containing per-project catalogue CSV files.
                       Defaults to ``CATALOGUE_DIR`` from settings.

    Returns:
        The updated DataFrame (also written to disk).
    """
    if catalogue_dir is None:
        from oracc_parser.settings import CATALOGUE_DIR
        catalogue_dir = CATALOGUE_DIR

    catalogue_dir = Path(catalogue_dir)

    raw_values: set[str] = set()
    for csv_file in sorted(catalogue_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file, usecols=["period"], dtype=str, keep_default_na=False)
            raw_values.update(v.strip() for v in df["period"].tolist() if v.strip())
        except Exception:
            pass

    period_path = Path(_data_file("period_mapping.csv"))
    existing = pd.read_csv(period_path, dtype=str, keep_default_na=False)
    known_lower = set(existing["period_name"].str.lower().tolist())

    new_rows = [
        {"period_name": raw, "start_year": "", "end_year": ""}
        for raw in sorted(raw_values)
        if raw.lower() not in known_lower
    ]
    if new_rows:
        existing = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

    existing.to_csv(period_path, index=False, encoding="utf-8")
    print(f"period_mapping.csv: {len(existing)} rows total, {len(new_rows)} new value(s) added")
    return existing


def update_archive_mapping(catalogue_dir: Path | None = None) -> pd.DataFrame:
    """Scan all catalogue CSVs and add any unmapped raw archive values to raw_archive_values.csv.

    For each unique raw value found in the ``archive`` column across all catalogues:
    - If it is already in ``raw_archive_values.csv``, it is left alone.
    - If it is new, a row is appended with blank ``Count``, ``Projects``, and
      ``Normalized Archive Value`` for manual completion.

    Modifies ``raw_archive_values.csv`` in place.

    Args:
        catalogue_dir: Directory containing per-project catalogue CSV files.
                       Defaults to ``CATALOGUE_DIR`` from settings.

    Returns:
        The updated DataFrame (also written to disk).
    """
    if catalogue_dir is None:
        from oracc_parser.settings import CATALOGUE_DIR
        catalogue_dir = CATALOGUE_DIR

    catalogue_dir = Path(catalogue_dir)

    raw_values: set[str] = set()
    for csv_file in sorted(catalogue_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file, usecols=["archive"], dtype=str, keep_default_na=False)
            raw_values.update(v.strip() for v in df["archive"].tolist() if v.strip())
        except Exception:
            pass

    archive_path = Path(_data_file("raw_archive_values.csv"))
    existing = pd.read_csv(archive_path, dtype=str, keep_default_na=False)
    known = set(existing["Raw Archive Value"].tolist())

    new_rows = [
        {"Raw Archive Value": raw, "Count": "", "Projects": "", "Normalized Archive Value": ""}
        for raw in sorted(raw_values)
        if raw not in known
    ]
    if new_rows:
        existing = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

    existing.to_csv(archive_path, index=False, encoding="utf-8")

    from oracc_parser.metadata.archive import _archive_mapping_cache
    import oracc_parser.metadata.archive as _archive_mod
    _archive_mod._archive_mapping_cache = None  # invalidate cache after update

    print(f"raw_archive_values.csv: {len(existing)} rows total, {len(new_rows)} new value(s) added")
    return existing


def update_provenience_mapping(catalogue_dir: Path | None = None) -> pd.DataFrame:
    """Scan all catalogue CSVs and add any unmapped raw provenience values to provenience.csv.

    For each unique raw value found in the ``provenience`` column across all catalogues:
    - If it is already in ``provenience.csv``, it is left alone.
    - If it is new, a row is appended with blank ``normalized_city``, ``pleiades_id``,
      ``pleiades_title``, ``lat``, ``lon`` for manual completion.

    Modifies ``provenience.csv`` in place.

    Args:
        catalogue_dir: Directory containing per-project catalogue CSV files.
                       Defaults to ``CATALOGUE_DIR`` from settings.

    Returns:
        The updated DataFrame (also written to disk).
    """
    if catalogue_dir is None:
        from oracc_parser.settings import CATALOGUE_DIR
        catalogue_dir = CATALOGUE_DIR

    catalogue_dir = Path(catalogue_dir)

    raw_values: set[str] = set()
    for csv_file in sorted(catalogue_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_file, usecols=["provenience"], dtype=str, keep_default_na=False)
            raw_values.update(v.strip() for v in df["provenience"].tolist() if v.strip())
        except Exception:
            pass

    prov_path = Path(_data_file("provenience.csv"))
    existing = pd.read_csv(prov_path, dtype=str, keep_default_na=False)
    known = set(existing["raw_provenience"].tolist())

    new_rows = [
        {"raw_provenience": raw, "normalized_city": "", "pleiades_id": "",
         "pleiades_title": "", "lat": "", "lon": ""}
        for raw in sorted(raw_values)
        if raw not in known
    ]
    if new_rows:
        existing = pd.concat([existing, pd.DataFrame(new_rows)], ignore_index=True)

    existing.to_csv(prov_path, index=False, encoding="utf-8")
    print(f"provenience.csv: {len(existing)} rows total, {len(new_rows)} new value(s) added")
    return existing


def get_zip_dir(base: str | None = None) -> Path:
    """Return the directory for downloaded ORACC project ZIPs.

    Args:
        base: Custom directory. Defaults to configured ``ORACC_JSONZIP_DIR``
            (set via ``.env`` or environment variable).
    """
    if base:
        p = Path(base)
    else:
        from oracc_parser.settings import JSONZIP_DIR
        p = JSONZIP_DIR

    p.mkdir(parents=True, exist_ok=True)
    return p
