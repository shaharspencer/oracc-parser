"""
Pipeline and convenience functions for oracc-parser.

Usage — run via ``main.py`` or import these functions in your script::

    from oracc_parser.pipeline import parse_project, RunConfig
    records = parse_project("saao/saa01", config=RunConfig(limit=5))

For quick access to just metadata, transliterations, etc., use the
granular helpers:

    from oracc_parser.pipeline import get_metadata_table, get_transliterations
"""

from pathlib import Path

import pandas as pd
from tqdm import tqdm

from oracc_parser.cache import (
    clear_project_cache,
    load_cached_tablet,
    save_tablet_to_cache,
)
from oracc_parser.download.extract_jsons import extract_from_zip
from oracc_parser.download.oracc_download import download_projects, download_zip, get_live_projects_dataframe
from oracc_parser.export.to_jsonl import to_csv, to_jsonl
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
    get_live_project_list = staticmethod(get_live_projects_dataframe)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def parse_project(
    project: str,
    config: RunConfig | None = None,
    download: bool = True,
) -> list[TabletRecord]:
    """Download, parse, and return all tablets from an ORACC project.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        config: RunConfig with parsing options. Uses defaults if None.
        download: If True, download the ZIP from ORACC first.

    Returns:
        List of TabletRecord objects.
    """
    if config is None:
        config = RunConfig()

    # 1. Download
    if download:
        zip_path = download_zip(project)
        if not zip_path:
            logger.error(f"Failed to download {project}")
            return []

    # 2. Extract JSONs from ZIP
    project_data = extract_from_zip(project)
    if not project_data.json_files:
        logger.warning(f"No JSON files found for {project}")
        return []

    # 3. Parse each text
    catalogue = project_data.project_catalogue or {}
    members = catalogue.get("members", {})
    records = []

    json_files = project_data.json_files
    if config.limit is not None:
        json_files = json_files[: config.limit]

    cache_hits = 0
    for js in tqdm(json_files, desc=f"Parsing {project}"):
        text_id = js.get("textid", "")

        # --- Cache: instant if config matches, rebuild strings if not ---
        if config.use_cache:
            cached = load_cached_tablet(project, text_id, config, config.cache_dir)
            if cached is not None:
                records.append(cached)
                cache_hits += 1
                continue

        # --- Parse from scratch ---
        metadata_dict = members.get(text_id, {})

        record = TabletRecord()
        record.content = parse_json_text(js, config)
        record.content.english_translation = get_translation(
            project, text_id, cache_dir=config.CACHE_DIR
        )
        record.metadata = populate_metadata(metadata_dict, text_id, project)
        records.append(record)

        # --- Save to cache (with config fingerprint) ---
        if config.use_cache:
            save_tablet_to_cache(record, project, text_id, config, config.cache_dir)

    if cache_hits:
        logger.info(
            f"Loaded {cache_hits}/{len(records)} tablets from cache, "
            f"parsed {len(records) - cache_hits} new"
        )
    else:
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
# Granular convenience functions  — flat pandas DataFrames
# ---------------------------------------------------------------------------


def get_metadata_table(records: list[TabletRecord]) -> pd.DataFrame:
    """Extract a flat metadata table from parsed records.

    Returns a DataFrame with one row per tablet, containing:
    ``id``, ``project``, ``text_id``, ``genre``, ``archive``, ``provenance``,
    ``pleiades_id``, ``period``, ``start_year``, ``end_year``.

    Example::

        records = parse_project("saao/saa01", config=RunConfig(limit=5))
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

    Combines metadata + all string representations into a single table.
    No nesting, no Pydantic objects — just clean columns.

    Returns columns: ``id``, ``project``, ``text_id``, ``genre``, ``archive``,
    ``provenance``, ``period``, ``start_year``, ``end_year``,
    ``transliteration``, ``normalization``, ``lemmatization``,
    ``unicode``, ``translation``, ``total_tokens``, ``tokens_without_broken``.

    Example::

        records = parse_project("saao/saa01")
        df = get_full_flat_table(records)
        df.to_json("dataset.jsonl", orient="records", lines=True)
    """
    rows = []
    for r in records:
        md = r.metadata
        ct = r.content
        t_rep = ct.transliterated_str_representation
        n_rep = ct.normalized_str_representation
        l_rep = ct.lemmatized_str_representation
        u_rep = ct.unicode_str_representation

        rows.append({
            "id": md.identifier,
            "project": md.project,
            "text_id": md.id_text,
            "genre": md.genre or "",
            "archive": md.archive or "",
            "provenance": md.geographical_information.city.city_name,
            "period": (
                md.chronological_information.tablet_period.period_name
                if md.chronological_information.tablet_period
                else ""
            ),
            "start_year": md.chronological_information.start_year,
            "end_year": md.chronological_information.end_year,
            "transliteration": t_rep.text if t_rep else "",
            "normalization": n_rep.text if n_rep else "",
            "lemmatization": l_rep.text if l_rep else "",
            "unicode": u_rep.text if u_rep else "",
            "translation": ct.english_translation or "",
            "total_tokens": t_rep.total_tokens if t_rep else 0,
            "tokens_without_broken": t_rep.tokens_without_broken if t_rep else 0,
        })
    return pd.DataFrame(rows)
