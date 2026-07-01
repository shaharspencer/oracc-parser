"""
Pipeline and convenience functions for oracc-parser.

Usage — run via ``main.py`` or import these functions in your script::

    from oracc_parser.pipeline import parse_project_from_oracc_from_oracc, RunConfig
    records = parse_project_from_oracc_from_oracc("saao/saa01", config=RunConfig(limit=5))

For quick access to just metadata, transliterations, etc., use the
granular helpers:

    from oracc_parser.pipeline import get_metadata_table, get_transliterations
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from oracc_parser.download.extract_jsons import extract_from_zip
from oracc_parser.download.oracc_download import download_projects, download_zip, get_live_projects_dataframe
from oracc_parser.export.to_jsonl import to_csv, to_jsonl
from oracc_parser.io.word_csv import (
    catalogue_to_dataframe,
    load_catalogue_csv,
    load_word_csvs_from_dir,
    load_word_csvs_from_zenodo,
    record_to_word_dataframe,
    save_catalogue_csv,
    save_word_csv,
    word_dataframe_to_record,
)
from oracc_parser.metadata.populate import populate_metadata
from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import TabletRecord
from oracc_parser.parsing.parse_content import parse_json_text
from oracc_parser.parsing.translation import get_translation
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import (
    get_provenience,
    get_period_mapping,
    get_sign_readings,
    get_pos_tags,
    get_languages,
    get_projects_metadata,
    get_state_mapping,
    get_archives,
    get_catalogue_columns,
)

logger = get_logger()


# ---------------------------------------------------------------------------
# Reference data access
# ---------------------------------------------------------------------------


class reference_data:
    """Access bundled reference datasets as pandas DataFrames.

    Example::

        from oracc_parser.pipeline import reference_data
        df = reference_data.get_provenance()
    """

    get_provenance = staticmethod(get_provenience)
    get_period_mapping = staticmethod(get_period_mapping)
    get_sign_list = staticmethod(get_sign_readings)
    get_pos_tags = staticmethod(get_pos_tags)
    get_languages = staticmethod(get_languages)
    get_projects_metadata = staticmethod(get_projects_metadata)
    get_state_supergroup_mapping = staticmethod(get_state_mapping)
    get_archive_mapping = staticmethod(get_archives)
    get_catalogue_columns = staticmethod(get_catalogue_columns)
    get_live_project_list = staticmethod(get_live_projects_dataframe)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def parse_project_from_oracc_from_oracc(
    project: str,
    config: RunConfig | None = None,
    download: bool = True,
) -> list[TabletRecord]:
    """Download, parse, and return all tablets from an ORACC project.

    On first call, downloads the ORACC ZIP, parses each tablet from JSON,
    and saves per-word CSVs to disk for fast future reloads.  On subsequent
    calls the word CSVs are used directly, skipping the JSON parsing step.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        config: RunConfig with parsing options. Uses defaults if None.
        download: If True, download the ZIP from ORACC if not already present.

    Returns:
        List of TabletRecord objects.
    """
    if config is None:
        config = RunConfig()

    from oracc_parser.settings import WORD_CSV_DIR
    project_slug = project.replace("/", "-")
    csv_dir = WORD_CSV_DIR / project_slug

    # Fast path: word CSVs already on disk — skip JSON parsing entirely
    if csv_dir.exists() and any(csv_dir.glob("*.csv")):
        word_dfs = load_word_csvs_from_dir(csv_dir, project=project)
        if config.limit is not None:
            word_dfs = dict(list(word_dfs.items())[: config.limit])
        return parse_project_from_oracc_from_word_csvs(project, word_dfs, config=config)

    # Slow path: parse from JSON, then save word CSVs for future use
    if download:
        zip_path = download_zip(project)
        if not zip_path:
            logger.error(f"Failed to download {project}")
            return []

    project_data = extract_from_zip(project)
    if not project_data.json_files:
        logger.warning(f"No JSON files found for {project}")
        return []

    catalogue = project_data.project_catalogue or {}
    members = catalogue.get("members", {})

    json_files = project_data.json_files
    if config.limit is not None:
        json_files = json_files[: config.limit]

    records = []
    for js in tqdm(json_files, desc=f"Parsing {project}"):
        text_id = js.get("textid", "")
        metadata_dict = members.get(text_id, {})

        record = TabletRecord()
        record.content = parse_json_text(js, config)
        if config.fetch_translations:
            record.content.english_translation = get_translation(project, text_id)
        record.metadata = populate_metadata(metadata_dict, text_id, project)
        records.append(record)

        # Save word CSV so future calls skip JSON parsing
        save_word_csv(record_to_word_dataframe(record))

    logger.info(f"Parsed {len(records)} tablets from {project}")
    return records


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------


def export_to_jsonl(records: list[TabletRecord], output_path: str) -> Path:
    """Export tablet records to a JSONL file."""
    return to_jsonl(records, output_path)


def export_to_csv(records: list[TabletRecord], output_path: str) -> Path:
    """Export tablet records to a CSV file."""
    return to_csv(records, output_path)


# ---------------------------------------------------------------------------
# Word-CSV entry point
# ---------------------------------------------------------------------------


def records_to_word_dataframes(
    records: list[TabletRecord],
) -> dict[str, pd.DataFrame]:
    """Convert parsed TabletRecords to per-word DataFrames.

    Each DataFrame contains one row per word and is keyed by ``text_id``.
    Use this to prepare data for upload (save each DataFrame with
    ``save_word_csv``) or for in-memory inspection.

    Args:
        records: List of parsed TabletRecord objects.

    Returns:
        Dict mapping text_id to per-word DataFrame.
    """
    result = {}
    for record in records:
        text_id = record.metadata.id_text
        if text_id:
            result[text_id] = record_to_word_dataframe(record)
    return result


def save_project_catalogue(project: str, path: Path | None = None) -> Path:
    """Extract the raw ORACC catalogue for a project and save it as a CSV.

    Reads ``catalogue.json`` from the project's ZIP and writes one row per
    text with all raw catalogue fields preserved.  The resulting file is
    saved to ``enriched_data/catalogues/{project_slug}.csv`` by
    default and can be loaded back with :func:`load_project_catalogue`.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        path: Override the output path. Optional.

    Returns:
        Path to the written CSV.

    Example::

        from oracc_parser import save_project_catalogue
        csv_path = save_project_catalogue("saao/saa01")
    """
    project_data = extract_from_zip(project)
    catalogue = project_data.project_catalogue or {}
    members = catalogue.get("members", {})
    if not members:
        logger.warning(f"No catalogue members found for {project} — skipping catalogue save")
        raise ValueError(f"No catalogue members found for {project}")
    df = catalogue_to_dataframe(project, members)
    return save_catalogue_csv(df, path)


def load_project_catalogue(path: str | Path) -> pd.DataFrame:
    """Load a saved project catalogue CSV from disk.

    Args:
        path: Path to the catalogue CSV saved by :func:`save_project_catalogue`.

    Returns:
        DataFrame with one row per text and raw catalogue fields as columns.

    Example::

        from oracc_parser import load_project_catalogue
        df = load_project_catalogue("enriched_data/catalogues/saao-saa01.csv")
    """
    return load_catalogue_csv(path)


def parse_project_from_oracc_from_word_csvs(
    project: str,
    word_dfs: dict[str, pd.DataFrame],
    config: RunConfig | None = None,
) -> list[TabletRecord]:
    """Parse tablets from pre-loaded per-word DataFrames.

    This is an alternative entry point to :func:`parse_project_from_oracc` for users
    who have downloaded the word-level CSVs from Zenodo instead of the raw
    ORACC JSON ZIPs.  All ``RunConfig`` options work identically: string
    representations are rebuilt from the word data according to ``config``.

    To load ``word_dfs``, use one of:

    - :func:`~oracc_parser.io.word_csv.load_word_csvs_from_zenodo` —
      stream directly from a Zenodo record without saving to disk.
    - :func:`~oracc_parser.io.word_csv.load_word_csvs_from_dir` —
      load from a local directory of CSV files.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        word_dfs: Dict mapping text_id to per-word DataFrame, as returned
            by the loader functions above.
        config: RunConfig with parsing options. Uses defaults if None.

    Returns:
        List of TabletRecord objects (same type as :func:`parse_project_from_oracc`).

    Example::

        from oracc_parser import parse_project_from_oracc_from_word_csvs, RunConfig
        from oracc_parser.io.word_csv import load_word_csvs_from_zenodo

        word_dfs = load_word_csvs_from_zenodo(
            zenodo_url="https://zenodo.org/records/12345",
            project="saao/saa01",
        )
        records = parse_project_from_oracc_from_word_csvs(
            "saao/saa01", word_dfs, config=RunConfig(drop_missing=True)
        )
    """
    if config is None:
        config = RunConfig()

    # Load catalogue once so each tablet gets its provenance/period/genre
    from oracc_parser.settings import CATALOGUE_DIR
    cat_path = CATALOGUE_DIR / f"{project.replace('/', '-')}.csv"
    catalogue_lookup: dict[str, dict] = {}
    if cat_path.exists():
        cat_df = load_catalogue_csv(cat_path)
        if "text_id" in cat_df.columns:
            catalogue_lookup = {
                row["text_id"]: row.to_dict()
                for _, row in cat_df.iterrows()
            }
    else:
        logger.warning(f"No catalogue found at {cat_path}; metadata will be empty")

    records = []
    for text_id, df in tqdm(word_dfs.items(), desc=f"Processing {project}"):
        catalogue_row = catalogue_lookup.get(text_id)
        record = word_dataframe_to_record(df, config, catalogue_row=catalogue_row)
        if config.fetch_translations:
            record.content.english_translation = get_translation(project, text_id)
        records.append(record)

    logger.info(f"Processed {len(records)} tablets for {project} from word CSVs")
    return records


# ---------------------------------------------------------------------------
# Granular convenience functions  — flat pandas DataFrames
# ---------------------------------------------------------------------------


def get_metadata_table(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract a flat metadata table from parsed records.

    Returns a DataFrame with one row per tablet, containing:
    ``id``, ``project``, ``text_id``, ``genre``, ``archive``, ``provenance``,
    ``pleiades_id``, ``period``, ``start_year``, ``end_year``,
    ``accession_museum_publication_numbers``, ``secondary_literature``.

    Example::

        records = parse_project_from_oracc("saao/saa01", config=RunConfig(limit=5))
        metadata_df = get_metadata_table(records)
        print(metadata_df.head())
    """
    rows = []
    for r in records:
        md = r.metadata
        rows.append({
            "id": md.identifier,
            "project": md.project,
            "text_id": md.id_text,
            "genre": md.genre or "",
            "archive": md.archive or "",
            "provenance": md.geographical_information.city.city_name,
            "pleiades_id": md.geographical_information.city.city_plaides_id,
            "state_supergroup": md.geographical_information.state_supergroup,
            "period": (
                md.chronological_information.tablet_period.period_name
                if md.chronological_information.tablet_period
                else ""
            ),
            "start_year": md.chronological_information.start_year,
            "end_year": md.chronological_information.end_year,
            "accession_museum_publication_numbers": md.accession_museum_publication_numbers,
            "secondary_literature": md.secondary_literature,
            "credits": md.credits,
            "cite_as": md.cite_as,
        })
    return pd.DataFrame(rows)


def get_transliterations(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract transliteration strings as a flat DataFrame.

    Returns columns: ``id``, ``project``, ``transliteration``,
    ``total_tokens``, ``tokens_without_broken``.
    """
    rows = []
    for r in records:
        rep = r.content.transliterated_str_representation
        rows.append({
            "id": r.metadata.identifier,
            "project": r.metadata.project,
            "transliteration": rep.text if rep else "",
            "total_tokens": rep.total_tokens if rep else 0,
            "tokens_without_broken": rep.tokens_without_broken if rep else 0,
        })
    return pd.DataFrame(rows)


def get_normalizations(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract normalization strings as a flat DataFrame.

    Returns columns: ``id``, ``project``, ``normalization``,
    ``total_tokens``, ``tokens_without_broken``.
    """
    rows = []
    for r in records:
        rep = r.content.normalized_str_representation
        rows.append({
            "id": r.metadata.identifier,
            "project": r.metadata.project,
            "normalization": rep.text if rep else "",
            "total_tokens": rep.total_tokens if rep else 0,
            "tokens_without_broken": rep.tokens_without_broken if rep else 0,
        })
    return pd.DataFrame(rows)


def get_lemmatizations(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract lemmatization strings as a flat DataFrame.

    Returns columns: ``id``, ``project``, ``lemmatization``,
    ``total_tokens``, ``tokens_without_broken``.
    """
    rows = []
    for r in records:
        rep = r.content.lemmatized_str_representation
        rows.append({
            "id": r.metadata.identifier,
            "project": r.metadata.project,
            "lemmatization": rep.text if rep else "",
            "total_tokens": rep.total_tokens if rep else 0,
            "tokens_without_broken": rep.tokens_without_broken if rep else 0,
        })
    return pd.DataFrame(rows)


def get_unicode_texts(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract Unicode cuneiform strings as a flat DataFrame.

    Returns columns: ``id``, ``project``, ``unicode``,
    ``total_chars``, ``included_chars``.
    """
    rows = []
    for r in records:
        rep = r.content.unicode_str_representation
        rows.append({
            "id": r.metadata.identifier,
            "project": r.metadata.project,
            "unicode": rep.text if rep else "",
            "total_chars": rep.total_chars if rep else 0,
            "included_chars": rep.included_chars if rep else 0,
        })
    return pd.DataFrame(rows)


def get_translations(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract English translations as a flat DataFrame.

    Returns columns: ``id``, ``project``, ``translation``.
    """
    rows = []
    for r in records:
        rows.append({
            "id": r.metadata.identifier,
            "project": r.metadata.project,
            "translation": r.content.english_translation or "",
        })
    return pd.DataFrame(rows)


def get_full_flat_table(records: list[TabletRecord]) -> pd.DataFrame:
    """Get everything in one flat DataFrame — ideal for releasing as a dataset.

    Combines all metadata columns (same as ``get_metadata_table``) with the
    text string representations. No nesting, no Pydantic objects.

    Returns all columns from ``get_metadata_table`` plus:
    ``transliteration``, ``normalization``, ``lemmatization``,
    ``unicode``, ``translation``, ``total_tokens``, ``tokens_without_broken``.

    Example::

        records = parse_project_from_oracc("saao/saa01")
        df = get_full_flat_table(records)
        df.to_json("dataset.jsonl", orient="records", lines=True)
    """
    meta_df = get_metadata_table(records)

    text_rows = []
    for r in records:
        md = r.metadata
        ct = r.content
        t_rep = ct.transliterated_str_representation
        n_rep = ct.normalized_str_representation
        l_rep = ct.lemmatized_str_representation
        u_rep = ct.unicode_str_representation
        text_rows.append({
            "id": md.identifier,
            "transliteration": t_rep.text if t_rep else "",
            "normalization": n_rep.text if n_rep else "",
            "lemmatization": l_rep.text if l_rep else "",
            "unicode": u_rep.text if u_rep else "",
            "translation": ct.english_translation or "",
            "total_tokens": t_rep.total_tokens if t_rep else 0,
            "tokens_without_broken": t_rep.tokens_without_broken if t_rep else 0,
        })
    text_df = pd.DataFrame(text_rows)
    return meta_df.merge(text_df, on="id")
