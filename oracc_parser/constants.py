"""
Standardized sentinel values and warning messages used across oracc-parser.

All "unknown" / "not found" / "unmapped" states are centralized here
so the user sees consistent, informative messages rather than ad-hoc strings.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Sentinel values — used as field defaults when real data is unavailable
# ---------------------------------------------------------------------------

# Geography
CITY_UNKNOWN = "unknown"
"""Provenance city could not be determined from ORACC catalogue."""

STATE_UNMAPPED = "unmapped"
"""Project has not been mapped to a state/empire grouping in our reference data."""

# Chronology
PERIOD_UNKNOWN = "unknown"
"""Historical period could not be determined."""

YEAR_UNKNOWN = None
"""Year could not be resolved from the period mapping (represented as None)."""

# POS / Language
POS_NOT_PROVIDED = "NOT_PROVIDED"
"""Part-of-speech tag was absent from the ORACC data for this word."""

LANGUAGE_UNKNOWN = "unknown"
"""Language code could not be mapped to a known language."""

# Content
TRANSLATION_UNAVAILABLE = ""
"""English translation was not available on the ORACC web interface."""

SIGN_UNICODE_FALLBACK = "U"
"""Sign reading could not be converted to a Unicode cuneiform character."""

SIGN_BROKEN = "X"
"""Sign is entirely missing / broken beyond recognition."""


# ---------------------------------------------------------------------------
# Warning messages — logged when edge cases are encountered
# ---------------------------------------------------------------------------

def warn_unmapped_city(project: str, raw_prov: str) -> str:
    """Warning when a provenance value can't be matched to our reference table."""
    return (
        f"[{project}] Provenance '{raw_prov}' not found in reference data. "
        f"City set to '{CITY_UNKNOWN}'. "
        f"Consider adding this city to data/provenience.csv."
    )


def warn_unmapped_state(project: str) -> str:
    """Warning when a project hasn't been mapped to a state grouping."""
    return (
        f"[{project}] Project not mapped to a state/empire grouping. "
        f"State set to '{STATE_UNMAPPED}'. "
        f"This project may need manual classification."
    )


def warn_unmapped_period(project: str, period: str) -> str:
    """Warning when a period name isn't in the period-to-year mapping."""
    return (
        f"[{project}] Period '{period}' not found in period_mapping.csv. "
        f"Year range could not be resolved."
    )


def warn_unmapped_pos(raw_pos: str) -> str:
    """Warning when a POS tag isn't in the reference table."""
    return (
        f"POS tag '{raw_pos}' not found in pos_tags.csv. "
        f"Normalized POS set to '{POS_NOT_PROVIDED}'."
    )


def warn_unmapped_language(lang_code: str) -> str:
    """Warning when a language code can't be normalized."""
    return (
        f"Language code '{lang_code}' not found in languages.csv. "
        f"Language set to '{LANGUAGE_UNKNOWN}'."
    )


def warn_no_catalogue_entry(project: str, text_id: str) -> str:
    """Warning when a text has no entry in the project catalogue."""
    return (
        f"[{project}/{text_id}] No catalogue entry found. "
        f"Metadata will use default/unknown values."
    )


def warn_unicode_fallback(reading: str, cleaned: str) -> str:
    """Warning when a sign reading can't be mapped to Unicode."""
    return (
        f"Sign reading '{reading}' (cleaned: '{cleaned}') has no Unicode mapping. "
        f"Stored as '{SIGN_UNICODE_FALLBACK}'."
    )
