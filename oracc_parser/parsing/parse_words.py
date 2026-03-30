"""
Parse word-level information from ORACC JSON ``l`` (lemma) nodes.

Extracts transliteration, normalization, lemma, POS, language, and
sign-level details for each word.
"""

from oracc_parser.models.tablet import Word, WordPOSInfo, WordSigns, Language
from oracc_parser.parsing.parse_signs import get_signs
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_pos_tags, get_languages

logger = get_logger()

# ---------------------------------------------------------------------------
# Load lookup tables once at import time
# ---------------------------------------------------------------------------

_pos_dict: dict[str, WordPOSInfo] = {}
_language_dict: dict[str, Language] = {}


def _load_lookups():
    """Load POS and language lookup dicts from reference CSVs."""
    global _pos_dict, _language_dict

    if not _pos_dict:
        df = get_pos_tags()
        for _, row in df.iterrows():
            try:
                _pos_dict[str(row.iloc[0])] = WordPOSInfo(
                    meaning=str(row.iloc[1]) if len(row) > 1 else "",
                    normalized_pos=str(row.iloc[2]) if len(row) > 2 else "",
                    to_mask=str(row.iloc[3]).lower() == "true" if len(row) > 3 else False,
                    mask_as=str(row.iloc[4]) if len(row) > 4 else "",
                )
            except Exception:
                pass

    if not _language_dict:
        import typing
        # Get valid literal values from the Pydantic model
        # Pydantic v2: annotation is the type
        # We need to unwrap Optional if present, but here it defaults to None so it is Optional
        field_info = Language.model_fields["normalized_language"]
        # extract valid args from Literal inside the annotation
        # annotation might be Optional[Literal[...]] or just Literal[...]
        # A robust way is to try constructing the object and catching validation error, 
        # or just trust the CSV and let pydantic validate in the constructor
        
        df = get_languages()
        for _, row in df.iterrows():
            try:
                lang_code = str(row["lang"])
                is_cuneiform = str(row.get("Is_cuneiform", "")).lower() == "yes"
                lang_name = str(row.get("language_name", ""))
                
                dialect = str(row.get("dialect", ""))
                if dialect == "nan":  # pandas empty string fallback
                    dialect = ""
                
                # Check if this name is valid
                # We can just try to instantiate. If it fails, we catch it.
                # But we want to store None if invalid, not crash.
                
                try:
                    lang_obj = Language(
                        is_cuneiform=is_cuneiform,
                        normalized_language=lang_name,
                        dialect=dialect
                    )
                except Exception:
                    # Fallback to None if the language name isn't in the allowed Literal
                    lang_obj = Language(
                        is_cuneiform=is_cuneiform,
                        normalized_language=None,
                        dialect=dialect
                    )
                
                _language_dict[lang_code] = lang_obj

            except Exception as e:
                logger.error(f"Error loading language {row.get('lang')}: {e}")
                pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_word(node_dict: dict) -> Word:
    """Parse a single ORACC ``l`` node into a Word object.

    Args:
        node_dict: Dictionary from the CDL tree containing ``f``, ``frag``,
                   ``ref``, ``inst`` keys.

    Returns:
        Populated Word object.
    """
    _load_lookups()

    result = Word()
    result.frag = _get_frag(node_dict)
    result.ref = node_dict.get("ref", "")
    result.inst = node_dict.get("inst", "")
    result.form = _safe_get(node_dict, "f", "form")
    result.lemma_form = _safe_get(node_dict, "f", "cf")
    result.sense = _safe_get(node_dict, "f", "sense")
    result.norm = _safe_get(node_dict, "f", "norm") or _safe_get(node_dict, "f", "norm0")
    result.raw_pos = _safe_get(node_dict, "f", "pos")
    result.lang = _safe_get(node_dict, "f", "lang")

    # Normalize POS
    result.normalized_pos = _normalize_pos(result.raw_pos)

    # Normalize language
    result.normalized_language = _normalize_language(result.lang)

    # Extract line number from ref (e.g. "P527140.2.1" -> line 2)
    try:
        result.line = int(result.ref.split(".")[1])
    except (IndexError, ValueError):
        result.line = 0

    # Parse signs (only for cuneiform languages)
    f_dict = node_dict.get("f", {})
    gdl = f_dict.get("gdl")
    if not gdl:
        logger.debug(f"No signs for {result.ref}")
        result.sign_dictionaries = WordSigns(break_percentage=1)
    elif gdl and result.normalized_language and result.normalized_language.is_cuneiform:
        result.sign_dictionaries = get_signs(word_dict=gdl, ref_id=result.ref)

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_frag(node_dict: dict) -> str:
    """Extract the transliteration fragment."""
    try:
        return node_dict["frag"]
    except KeyError:
        return "0" if node_dict.get("f", {}).get("form") == "0" else ""


def _safe_get(node_dict: dict, *keys) -> str:
    """Safely navigate nested dict keys, returning empty string on failure."""
    current = node_dict
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return ""
    return current if current is not None else ""


def _normalize_pos(raw_pos: str | None) -> WordPOSInfo | None:
    """Look up normalized POS info from the reference table."""
    if raw_pos and raw_pos in _pos_dict:
        return _pos_dict[raw_pos]
    elif raw_pos is not None:
        logger.debug(f"POS '{raw_pos}' not in lookup table")
    return WordPOSInfo(meaning="NOT_PROVIDED", normalized_pos="NOT_PROVIDED", to_mask=False, mask_as="")


def _normalize_language(lang_code: str | None) -> Language | None:
    """Look up normalized language from the reference table."""
    if not lang_code:
        return None
    return _language_dict.get(lang_code)
