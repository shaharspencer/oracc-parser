"""
Genre resolution, spelling normalization and coarse classification.

* :func:`resolve_genre` picks the raw genre for a catalogue entry: the first
  non-empty of ``genre`` -> ``genres`` -> ``subgenre``, then the editorial
  rules in ``metadata_rules.csv``. It also reports which field was used.
* :func:`normalize_genre` collapses whitespace and unifies case to a canonical
  spelling (``genre_normalization.csv``, built from the catalogues by
  ``scripts/build_genre_normalization.py``).
* :func:`classify_genre` maps (source field, raw value) to one of 11 coarse
  classes (plus ``Uncertain``) via ``genre_classes.csv``. That mapping was
  contributed as a reference (it reflects one study's class boundaries) and only
  covers values seen in that corpus; uncovered values get ``""``.
"""
from __future__ import annotations

from oracc_parser.metadata.rules import apply_rules, clean_value
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_genre_classes, get_genre_normalization

logger = get_logger()

#: Catalogue fields consulted for the raw genre, in priority order.
GENRE_FIELDS = ("genre", "genres", "subgenre")

_canonical: dict[str, str] | None = None
_classes_by_source: dict[tuple[str, str], str] | None = None
_classes_by_value: dict[str, str] | None = None
_class_names: set[str] | None = None


def collapse_ws(s: str) -> str:
    """Collapse runs of whitespace to a single space and strip."""
    return " ".join(str(s).split())


def fold_genre(s: str) -> str:
    """Case-fold and whitespace-collapse a genre string (lookup key)."""
    return collapse_ws(s).casefold()


def _load_tables() -> None:
    global _canonical, _classes_by_source, _classes_by_value, _class_names
    if _canonical is None:
        _canonical = {}
        try:
            for row in get_genre_normalization().to_dict("records"):
                _canonical[fold_genre(row["variant"])] = row["canonical"]
                _canonical[fold_genre(row["canonical"])] = row["canonical"]
        except Exception as e:
            logger.error(f"error loading genre_normalization.csv: {e}")
    if _classes_by_source is None:
        _classes_by_source, by_value = {}, {}
        try:
            for row in get_genre_classes().to_dict("records"):
                key = fold_genre(row["raw_value"])
                _classes_by_source[(row["source"], key)] = row["genre_class"]
                by_value.setdefault(key, set()).add(row["genre_class"])
        except Exception as e:
            logger.error(f"error loading genre_classes.csv: {e}")
        # Value-only fallback, used only when unambiguous across source fields.
        _classes_by_value = {k: next(iter(v)) for k, v in by_value.items() if len(v) == 1}
        _class_names = set(_classes_by_source.values())


def resolve_genre(metadata_dict: dict, project: str) -> tuple[str, str]:
    """Return ``(raw_genre, source)`` for a catalogue entry.

    ``source`` is the catalogue field the value came from (``"genre"``,
    ``"genres"``, ``"subgenre"``), ``"rule:<field>"`` when an editorial rule
    supplied it, or ``""`` when nothing was found.
    """
    for field in GENRE_FIELDS:
        value = clean_value(metadata_dict.get(field))
        if value:
            return value, field
    return apply_rules("genre", metadata_dict, project)


def normalize_genre(raw: str) -> str:
    """Return the canonical spelling of ``raw`` (whitespace collapsed, case unified)."""
    raw = clean_value(raw)
    if not raw:
        return ""
    _load_tables()
    return _canonical.get(fold_genre(raw), collapse_ws(raw))


def classify_genre(raw: str, source: str) -> str:
    """Return the coarse genre class for a raw value from ``source``, or ``""``."""
    raw = clean_value(raw)
    if not raw:
        return ""
    _load_tables()
    key = fold_genre(raw)
    if source.startswith("rule:"):
        # Editorial rules assign class names directly.
        if raw in _class_names:
            return raw
        return _classes_by_value.get(key, "")
    return _classes_by_source.get((source, key)) or _classes_by_value.get(key, "")
