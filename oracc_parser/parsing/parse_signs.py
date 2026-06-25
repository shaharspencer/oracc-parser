"""
Parse sign-level information from ORACC GDL (Grapheme Description Language) nodes.

Handles sign value extraction, unicode conversion, break-state classification,
and role assignment (phonetic, logographic, determinative).
"""
from __future__ import annotations

from collections import Counter

from oracc_parser.models.tablet import Sign, WordSigns
from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.unicode import convert_to_unicode

logger = get_logger()


def get_signs(word_dict: list, ref_id: str) -> WordSigns:
    """Parse a GDL word dictionary into a WordSigns object.

    Args:
        word_dict: The ``gdl`` list from an ORACC ``f`` node.
        ref_id: Text reference ID for error reporting.

    Returns:
        WordSigns with parsed sign list and break percentage.
    """
    result = WordSigns()
    parsed = _get_sign_values(word_dict, ref_id)

    try:
        assert (
            len(parsed["unicode"])
            == len(parsed["break"])
            == len(parsed["delims"])
            == len(parsed["role_list"])
            == len(parsed["meanings"])
        )

        result.break_percentage = parsed["break_perc"]
        result.reading = parsed["reading"]

        for i in range(len(parsed["unicode"])):
            sign = Sign(
                role=parsed["role_list"][i],
                unicode_version=parsed["unicode"][i],
                breakage=parsed["break"][i],
                optional_delim=parsed["delims"][i],
                meaning=parsed["meanings"][i],
            )
            result.signs.append(sign)

        if not result.signs:
            result.break_percentage = 1

    except Exception as e:
        logger.error(f"Error in get_signs: {e}")

    return result


def _get_sign_value(signobj: dict, ref_id: str, det: bool = False) -> dict:
    """Extract value, delimiter, unicode, break state, and role from a single sign.

    Args:
        signobj: A single sign dictionary from the GDL node.
        ref_id: Reference ID for error reporting.
        det: Whether this sign is a determinative.

    Returns:
        Dict with keys: value, delim, unicode, break, det, role.
    """
    # Delimiter
    delim = signobj.get("delim", "")
    if delim == "—":
        delim = "-"

    # Reading value — check known keys
    val = ""
    for key in ("v", "s", "form", "p", "c", "q"):
        if key in signobj:
            val = signobj[key]
            break
    else:
        logger.warning(f"No sign value in {ref_id}: {signobj.keys()}")

    # Break state
    br = signobj.get("break", "complete")
    if br not in ("complete", "missing", "damaged"):
        logger.warning(f"Unknown break type in {ref_id}: {br}")

    # Unicode conversion
    if "u" in signobj:
        uni = signobj["u"]
    elif "utf8" in signobj:
        uni = signobj["utf8"]
    else:
        # Fallback to looking up the sign value
        uni = convert_to_unicode(val)[1]
    
    if uni in ("X", "XXX", "o", "") or not val:
        if br == "complete": 
             # If it was marked complete but we have no unicode, 
 
             if val == "x":
                 uni = "x"
                 br = "missing"
             else:
                 # It's a reading without a known unicode mapping
                 # Keep it as is or mark as 'X'?
                 # For now, let's trust the validator or leave it empty if it's really nothing.
                 pass
    
    # Sanity check for non-cuneiform garbage if we expect cuneiform
    # (Range 0x12000 - 0x1254F is Cuneiform)
    # But we also have numbers, punctuation, etc.
    # So we only warn if it looks like ASCII and isn't x/X
    if len(uni) == 1 and ord(uni) < 128 and uni not in "xX":
         # It might be a transliteration that didn't convert
         pass

    # Role assignment
    if det:
        role = "DETERMINATIVE"
    elif signobj.get("role") == "logo":
        role = "LOGOGRAMIC"
    elif signobj.get("role") == "x":
        role = "x"
    else:
        role = "PHONETIC"

    return {"value": val, "delim": delim, "unicode": uni, "break": br, "det": det, "role": role}


def _parse_sign(word_dict: list, ref_id: str, det: bool = False) -> list[dict]:
    """Recursively parse sign objects, handling groups, sequences, and qualifiers.

    Args:
        word_dict: List of sign objects from the GDL node.
        ref_id: Reference ID for error reporting.
        det: Whether the current context is a determinative.

    Returns:
        List of sign dicts (same format as _get_sign_value output).
    """
    signs = []
    for obj in word_dict:
        if any(k in obj for k in ("utf8", "n", "v", "s", "form", "p", "c", "q")):
            signs.append(_get_sign_value(obj, ref_id, det))
        elif "group" in obj:
            signs.extend(_parse_sign(obj["group"], ref_id, det))
        elif "seq" in obj:
            signs.extend(_parse_sign(obj["seq"], ref_id, det=True))
        elif "qualified" in obj:
            signs.extend(_parse_sign(obj["qualified"], ref_id, det))
        elif obj.get("x") == "ellipsis":
            signs.append({"value": "x", "delim": "", "unicode": "x", "break": "missing", "det": det, "role": "x"})
        elif obj.get("x") in ("newline", "dollar"):
            continue
        else:
            logger.warning(f"Unknown sign structure in {ref_id}: {obj.keys()}")
    return signs


def _get_sign_values(word_dict: list, ref_id: str) -> dict:
    """Convert sign-level data into aggregated word-level data.

    Returns dict with unicode list, reading string, break states, and break percentage.
    """
    try:
        signs = _parse_sign(word_dict, ref_id)
        uni_list, state_list, reading = [], [], ""
        delim_list, role_list, meaning_list = [], [], []

        for s in signs:
            uni_list.append(s["unicode"])
            state_list.append(s["break"])
            delim_list.append(s["delim"])
            role_list.append(s["role"])
            meaning_list.append(s["value"])

            # Build human-readable reading string
            v, d, br, is_det = s["value"], s["delim"], s["break"], s["det"]
            token = (
                f"[{v}]{d}" if br == "missing"
                else f"⸢{v}⸣{d}" if br == "damaged"
                else f"{v}{d}"
            )
            if is_det:
                token = "{" + token + "}"
            reading += token

        # Clean up edge cases
        reading = reading.replace("]-[", "-").replace("⸣-⸢", "-")

        # Calculate break percentage
        if state_list:
            cnt = Counter(state_list)
            break_perc = round((cnt["missing"] + 0.5 * cnt["damaged"]) / len(state_list), 2)
        else:
            break_perc = 0

        return {
            "unicode": uni_list,
            "unicode_word": "".join(uni_list),
            "reading": reading,
            "break": state_list,
            "break_perc": break_perc,
            "delims": delim_list,
            "role_list": role_list,
            "meanings": meaning_list,
        }
    except Exception as e:
        logger.error(f"Error in _get_sign_values: {e}")
        return {
            "unicode": [], "unicode_word": "", "reading": "",
            "break": [], "break_perc": 0, "delims": [],
            "role_list": [], "meanings": [],
        }
