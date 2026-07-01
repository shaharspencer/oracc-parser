"""
Serialize/deserialize TabletRecord <-> per-word CSV format.

Each CSV holds all words for a single tablet, one row per word.
Only the data that cannot be re-derived from reference tables is stored.
Metadata (provenance, period, etc.) and normalized POS/language fields are
intentionally omitted — they are re-populated at reconstruction time from
the project catalogue and bundled reference CSVs.

CSV schema
----------
Identity:
    text_id, project

Word fields:
    word_index, frag, ref, inst, form, lemma_form, sense,
    norm, raw_pos, lang, line

Signs (derived from Word.sign_dictionaries):
    signs_reading    — reading string for the whole word
    signs_break_pct  — fraction of broken signs (used for word-level filtering)
    break_info       — breakage state per sign, joined with "; "
                       e.g. "complete; missing; complete"
"""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

from oracc_parser.models.tablet import (
    Sign,
    TabletContent,
    TabletMetadata,
    TabletRecord,
    Word,
    WordSigns,
)
from oracc_parser.utils.logger import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Record -> DataFrame
# ---------------------------------------------------------------------------


def record_to_word_dataframe(record: TabletRecord) -> pd.DataFrame:
    """Serialize a TabletRecord into a per-word DataFrame.

    Args:
        record: A fully parsed TabletRecord.

    Returns:
        DataFrame with one row per word. Empty DataFrame if no words.
    """
    md = record.metadata

    rows = []
    for i, word in enumerate(record.content.words):
        sd = word.sign_dictionaries

        if sd and sd.signs:
            unicode = "; ".join(s.unicode_version for s in sd.signs)
            break_info = "; ".join(s.breakage for s in sd.signs)
        else:
            unicode = ""
            break_info = ""

        row = {
            "text_id": md.id_text or "",
            "project": md.project or "",
            "word_index": i,
            "frag": word.frag or "",
            "ref": word.ref or "",
            "inst": word.inst or "",
            "form": word.form or "",
            "lemma_form": word.lemma_form or "",
            "sense": word.sense or "",
            "norm": word.norm or "",
            "raw_pos": word.raw_pos or "",
            "lang": word.lang or "",
            "line": word.line if word.line is not None else 0,
            "signs_reading": sd.reading if sd else "",
            "signs_break_pct": sd.break_percentage if sd else -1.0,
            "unicode": unicode,
            "break_info": break_info,
        }
        rows.append(row)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# DataFrame -> Record
# ---------------------------------------------------------------------------


def word_dataframe_to_record(
    df: pd.DataFrame,
    config,
    catalogue_row: dict | None = None,
) -> TabletRecord:
    """Reconstruct a TabletRecord from a per-word DataFrame, applying config.

    Normalized POS and language fields are re-derived from ``raw_pos`` and
    ``lang`` via the same reference-table lookups used during a normal parse.
    String representations are rebuilt according to ``config``, so all config
    options work identically to the normal parse path.

    Args:
        df:            DataFrame produced by ``record_to_word_dataframe``.
        config:        RunConfig controlling sign/masking options.
        catalogue_row: Raw catalogue dict for this text (from the project
                       catalogue CSV).  When provided, provenance, period,
                       genre, and other metadata fields are fully populated.
                       When ``None``, metadata will be mostly empty.

    Returns:
        TabletRecord with full content and rebuilt string representations.
    """
    from oracc_parser.parsing.parse_content import (
        _add_unicode_representation,
        _add_word_level_representations,
    )
    from oracc_parser.parsing.parse_words import (
        _load_lookups,
        _normalize_language,
        _normalize_pos,
    )
    from oracc_parser.metadata.populate import populate_metadata

    record = TabletRecord()

    if df.empty:
        return record

    first = df.iloc[0]
    text_id = _str_or_none(first.get("text_id")) or ""
    project = _str_or_none(first.get("project")) or ""

    record.metadata = populate_metadata(catalogue_row or {}, text_id, project)

    # Ensure POS and language lookup tables are loaded
    _load_lookups()

    # --- Words ---
    words = []
    for _, row in df.iterrows():
        raw_pos = _str_or_none(row.get("raw_pos"))
        lang = _str_or_none(row.get("lang"))

        # Re-derive normalized fields from reference tables
        np_info = _normalize_pos(raw_pos)
        nl_info = _normalize_language(lang)

        # Reconstruct per-sign data from unicode + break_info
        unicode_str = _str_or_none(row.get("unicode")) or ""
        break_info_str = _str_or_none(row.get("break_info")) or ""

        unicode_chars = unicode_str.split("; ") if unicode_str else []
        break_states = break_info_str.split("; ") if break_info_str else []

        # Pad or trim so lengths match
        n = max(len(unicode_chars), len(break_states))
        unicode_chars += [""] * (n - len(unicode_chars))
        break_states += ["complete"] * (n - len(break_states))

        signs = [
            Sign(unicode_version=u, breakage=b)
            for u, b in zip(unicode_chars, break_states)
        ]

        word = Word(
            frag=_str_or_none(row.get("frag")),
            ref=_str_or_none(row.get("ref")),
            inst=_str_or_none(row.get("inst")),
            form=_str_or_none(row.get("form")),
            lemma_form=_str_or_none(row.get("lemma_form")),
            sense=_str_or_none(row.get("sense")),
            norm=_str_or_none(row.get("norm")),
            raw_pos=raw_pos,
            lang=lang,
            line=_int_or_none(row.get("line")),
            normalized_pos=np_info,
            normalized_language=nl_info,
            sign_dictionaries=WordSigns(
                reading=_str_or_none(row.get("signs_reading")) or "",
                break_percentage=_float_or_default(row.get("signs_break_pct"), -1.0),
                signs=signs,
            ),
        )
        words.append(word)

    record.content = TabletContent(words=words)
    record.content = _add_word_level_representations(
        record.content, config.mask_pos, config.max_break_fraction
    )
    record.content = _add_unicode_representation(
        record.content,
        drop_missing=config.drop_missing,
        drop_damaged=config.drop_damaged,
        keep_segmentation=config.keep_word_segmentation,
    )

    return record


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def save_word_csv(df: pd.DataFrame, path: str | Path | None = None) -> Path:
    """Write a per-word DataFrame to a CSV file.

    If ``path`` is omitted, saves to ``enriched_data/oracc_csvs/{text_id}.csv``
    using the ``text_id`` from the first row of the DataFrame.

    Args:
        df: DataFrame produced by ``record_to_word_dataframe``.
        path: Output file path. Optional.

    Returns:
        Path to the written file.
    """
    if path is None:
        from oracc_parser.settings import WORD_CSV_DIR
        first = df.iloc[0] if not df.empty else {}
        text_id = str(first.get("text_id", "unknown"))
        project_slug = str(first.get("project", "unknown")).replace("/", "-")
        path = WORD_CSV_DIR / project_slug / f"{text_id}.csv"

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    logger.info(f"Saved word CSV to {out} ({len(df)} rows)")
    return out


def load_word_csv(path: str | Path) -> pd.DataFrame:
    """Load a per-word CSV from disk.

    Args:
        path: Path to the CSV file.

    Returns:
        DataFrame with one row per word.
    """
    return pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)


def load_word_csvs_from_dir(
    directory: str | Path,
    project: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Load all per-word CSVs from a local directory.

    If the directory does not exist (or is empty) and ``project`` is given,
    the project's CSVs are downloaded from Zenodo on demand and cached on disk.
    Subsequent calls for the same project are instant.

    Args:
        directory: Directory containing ``{text_id}.csv`` files.
        project:   ORACC project path (e.g. ``"saao/saa01"``). Required for
                   automatic download from Zenodo when the directory is missing.

    Returns:
        Dict mapping text_id to DataFrame.
    """
    base = Path(directory)

    if not base.exists() or not any(base.glob("*.csv")):
        if project is None:
            raise FileNotFoundError(
                f"Directory {base} not found. Pass project= to enable automatic "
                "download from Zenodo."
            )
        from oracc_parser.download.fetch_data import extract_project_csvs
        base = extract_project_csvs(project, dest_dir=base.parent)

    result = {}
    for f in sorted(base.glob("*.csv")):
        text_id = f.stem
        result[text_id] = load_word_csv(f)
    logger.info(f"Loaded {len(result)} word CSV(s) from {base}")
    return result


def catalogue_to_dataframe(project: str, members: dict) -> pd.DataFrame:
    """Flatten the raw ORACC catalogue members dict into a DataFrame.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        members: The ``members`` dict from catalogue.json (text_id -> field dict).

    Returns:
        DataFrame with one row per text. Columns: ``text_id``, ``project``,
        followed by every raw catalogue field found across all texts.
    """
    rows = []
    for text_id, fields in members.items():
        row: dict = {}
        if isinstance(fields, dict):
            row.update(fields)
        # Set after update so the full project path is not overwritten by the
        # short internal project name stored in each member's fields.
        row["text_id"] = text_id
        row["project"] = project
        rows.append(row)
    return pd.DataFrame(rows)


def save_catalogue_csv(df: pd.DataFrame, path: str | Path | None = None) -> Path:
    """Write a project catalogue DataFrame to a CSV file.

    If ``path`` is omitted, saves to
    ``enriched_data/catalogues/{project_slug}.csv``.

    Args:
        df: DataFrame produced by :func:`catalogue_to_dataframe`.
        path: Output file path. Optional.

    Returns:
        Path to the written file.
    """
    if path is None:
        if df.empty:
            raise ValueError(
                "Cannot auto-name catalogue CSV: DataFrame is empty. "
                "Pass an explicit path or ensure the project has catalogue data."
            )
        from oracc_parser.settings import CATALOGUE_DIR
        project = str(df["project"].iloc[0])
        project_slug = project.replace("/", "-")
        path = CATALOGUE_DIR / f"{project_slug}.csv"

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    logger.info(f"Saved catalogue CSV to {out} ({len(df)} rows)")
    return out


def load_catalogue_csv(path: str | Path) -> pd.DataFrame:
    """Load a project catalogue CSV from disk.

    Args:
        path: Path to the catalogue CSV file.

    Returns:
        DataFrame with one row per text and raw catalogue fields as columns.
        Returns an empty DataFrame if the file is empty or unreadable.
    """
    try:
        return pd.read_csv(path, encoding="utf-8", dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame()



# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _str_or_none(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _int_or_none(val) -> int | None:
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def _float_or_default(val, default: float) -> float:
    if val is None:
        return default
    if isinstance(val, float) and pd.isna(val):
        return default
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return default
