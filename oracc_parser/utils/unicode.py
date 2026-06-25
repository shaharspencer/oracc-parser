"""
Convert transliteration sign readings to Unicode cuneiform characters.

Uses the bundled sign_readings.csv lookup table. Handles accented vowels,
numeric subscripts, and various ORACC notation conventions.
"""
from __future__ import annotations

import re

from oracc_parser.utils.logger import get_logger
from oracc_parser.utils.paths import get_sign_readings

logger = get_logger()

# ---------------------------------------------------------------------------
# Load lookup table once at import time
# ---------------------------------------------------------------------------

_sign_df = get_sign_readings()
# Build dict: reading -> unicode character
_unicode_dict: dict[str, str] = {}
for _, row in _sign_df.iterrows():
    key = str(row.iloc[0]).strip() if not row.empty else ""
    val = str(row.iloc[1]).strip() if len(row) > 1 else ""
    if key and val:
        _unicode_dict[key] = val

# ---------------------------------------------------------------------------
# Pre-compiled patterns
# ---------------------------------------------------------------------------

ACCENT2 = {"á": "a", "é": "e", "í": "i", "ú": "u"}
ACCENT3 = {"à": "a", "è": "e", "ì": "i", "ù": "u"}
NUM2SUB = {"2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"}

ACCENT2_RE = re.compile("|".join(map(re.escape, ACCENT2)))
ACCENT3_RE = re.compile("|".join(map(re.escape, ACCENT3)))
TRAILING_NUM_RE = re.compile(r"([2-9])$")
PAREN_RE = re.compile(r"\((.*?)\)")


def convert_to_unicode(reading: str) -> tuple[str, str]:
    """Convert a transliteration reading to its Unicode cuneiform equivalent.

    Args:
        reading: A sign reading string (e.g. "šar", "LUGAL", "1").

    Returns:
        A tuple of (cleaned_reading, unicode_char). If no mapping is found,
        the reading is echoed back as-is.
    """
    # --- A) Exact numeric lookup ---
    if reading.isdigit():
        uni = _unicode_dict.get(reading)
        if not uni:
            stripped = str(int(reading))
            uni = _unicode_dict.get(stripped)
        if uni:
            return (reading, uni)

    # --- B) Fraction lookup (e.g. "1/3") ---
    if "/" in reading:
        frac = reading.replace("/", "")
        if frac.isdigit():
            uni = _unicode_dict.get(reading)
            if uni:
                return (reading, uni)

    # --- C) Normalize case & special "ḫ" → "h" ---
    clean = reading.lower().replace("ḫ", "h")

    # --- D) Handle accented vowels → base + subscript ---
    if ACCENT2_RE.search(clean):
        clean = ACCENT2_RE.sub(lambda m: ACCENT2[m.group(0)], clean) + "₂"
    elif ACCENT3_RE.search(clean):
        clean = ACCENT3_RE.sub(lambda m: ACCENT3[m.group(0)], clean) + "₃"

    # --- E) Convert trailing digit to Unicode subscript ---
    m = TRAILING_NUM_RE.search(clean)
    if m:
        sub = NUM2SUB.get(m.group(1))
        if sub:
            clean = clean[:-1] + sub

    # --- F) Direct lookup ---
    uni = _unicode_dict.get(clean)
    if uni:
        if "(" in clean or ")" in clean:
            printable = PAREN_RE.sub("", clean)
            return (printable, uni)
        return (clean, uni)

    # --- G) Fallbacks ---
    if clean in ("xxx", "x"):
        return (clean, "broken")

    if "(" in clean or ")" in clean:
        no_paren = clean.replace("(", "").replace(")", "")
        uni2 = _unicode_dict.get(no_paren)
        if uni2:
            return (no_paren, uni2)
        return (no_paren, no_paren)

    if clean == "n":
        return ("n", "n")

    logger.warning(f"Unicode not found for reading: |{reading}| (cleaned: {clean})")
    return (clean, clean)
