"""
Export parsed tablet data to JSONL and CSV formats.
"""

import csv
import json
from pathlib import Path

from oracc_parser.models.tablet import TabletRecord
from oracc_parser.utils.logger import get_logger

logger = get_logger()


def to_jsonl(records: list[TabletRecord], output_path: str | Path) -> Path:
    """Export tablet records to a JSONL file (one JSON object per line).

    Args:
        records: List of parsed TabletRecord objects.
        output_path: File path for the output JSONL.

    Returns:
        Path to the written file.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with open(output, "w", encoding="utf-8") as f:
        for record in records:
            line = _record_to_dict(record)
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    logger.info(f"Exported {len(records)} records to {output}")
    return output


def to_csv(records: list[TabletRecord], output_path: str | Path) -> Path:
    """Export tablet records to a flat CSV file.

    Args:
        records: List of parsed TabletRecord objects.
        output_path: File path for the output CSV.

    Returns:
        Path to the written file.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows = [_record_to_flat_dict(r) for r in records]
    if not rows:
        logger.warning("No records to export.")
        return output

    fieldnames = list(rows[0].keys())
    with open(output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Exported {len(records)} records to {output}")
    return output


def _record_to_dict(record: TabletRecord) -> dict:
    """Convert a TabletRecord to a JSON-serializable dict (nested)."""
    md = record.metadata
    ct = record.content

    result = {
        "id": md.identifier,
        "project": md.project,
        "text_id": md.id_text,
        "genre": md.genre,
        "translation": ct.english_translation,
        "metadata": {
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
            "copyright": md.copyright_information,
        },
    }

    # Add string representations if available
    if ct.transliterated_str_representation:
        result["transliteration"] = ct.transliterated_str_representation.text
    if ct.lemmatized_str_representation:
        result["lemmatization"] = ct.lemmatized_str_representation.text
    if ct.normalized_str_representation:
        result["normalization"] = ct.normalized_str_representation.text
    if ct.unicode_str_representation:
        result["unicode"] = ct.unicode_str_representation.text

    # Word count stats
    if ct.transliterated_str_representation:
        result["total_tokens"] = ct.transliterated_str_representation.total_tokens
        result["tokens_without_broken"] = (
            ct.transliterated_str_representation.tokens_without_broken
        )

    return result


def _record_to_flat_dict(record: TabletRecord) -> dict:
    """Convert a TabletRecord to a flat dict for CSV export."""
    md = record.metadata
    ct = record.content

    return {
        "id": md.identifier,
        "project": md.project,
        "text_id": md.id_text,
        "genre": md.genre or "",
        "provenance": md.geographical_information.city.city_name,
        "period": (
            md.chronological_information.tablet_period.period_name
            if md.chronological_information.tablet_period
            else ""
        ),
        "start_year": md.chronological_information.start_year or "",
        "end_year": md.chronological_information.end_year or "",
        "translation": ct.english_translation,
        "transliteration": (
            ct.transliterated_str_representation.text
            if ct.transliterated_str_representation
            else ""
        ),
        "lemmatization": (
            ct.lemmatized_str_representation.text
            if ct.lemmatized_str_representation
            else ""
        ),
        "normalization": (
            ct.normalized_str_representation.text
            if ct.normalized_str_representation
            else ""
        ),
        "unicode": (
            ct.unicode_str_representation.text
            if ct.unicode_str_representation
            else ""
        ),
        "total_tokens": (
            ct.transliterated_str_representation.total_tokens
            if ct.transliterated_str_representation
            else 0
        ),
        "tokens_without_broken": (
            ct.transliterated_str_representation.tokens_without_broken
            if ct.transliterated_str_representation
            else 0
        ),
    }
