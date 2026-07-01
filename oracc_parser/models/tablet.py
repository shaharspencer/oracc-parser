"""
Pydantic data models for ORACC tablet records.

This module contains all the structured data models used throughout
oracc-parser, from individual signs up to complete tablet records.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from oracc_parser.constants import (
    CITY_UNKNOWN,
    POS_NOT_PROVIDED,
    STATE_UNMAPPED,
)


# ---------------------------------------------------------------------------
# Value normalization models
# ---------------------------------------------------------------------------


class WordPOSInfo(BaseModel):
    """Normalized part-of-speech information for a word."""

    meaning: str = ""
    normalized_pos: str = ""
    to_mask: bool = False
    mask_as: str = ""


class Language(BaseModel):
    """Language tag for a word, with cuneiform flag."""

    is_cuneiform: bool = True
    normalized_language: Optional[Literal[
        "Sumerian",
        "Proto-cuneiform",
        "Akkadian",
        "Ugaritic",
        "Urartian",
        "Persian",
        "Hittite",
        "Aramaic",
        "Elamite",
        "Hurrian",
        "Canaanite",
        "Numbers",
        "Unclear",
        "Proto-Elamite",
        "Greek",
        "Egyptian",
        "Assyrian Hieroglyphs",
    ]] = None
    dialect: str = ""


# ---------------------------------------------------------------------------
# Geographical models
# ---------------------------------------------------------------------------


class StateSupergroup(str, Enum):
    """Known state/empire groupings for provenance classification."""

    NEO_ASSYRIAN = "Neo-Assyrian Empire"
    ACHAEMENID = "Achemenid"
    HELLENISTIC = "Hellenistic"
    BABYLONIA_TRANSITION = "Babylonia Transition Period 2nd to 1st mill"
    SUHU = "Suhu"
    FIRST_SEALAND = "First Sealand Dynasty"
    BABYLONIA = "Babylonia"
    NEO_BABYLONIAN = "Neo Babylonian Empire"
    MIDDLE_ASSYRIAN = "Middle-Assyrian State"
    UNMAPPED = "WE HAVE NOT YET MAPPED THIS PROJECT"


class City(BaseModel):
    """Geographical city with optional Pleiades ID."""

    city_name: str = CITY_UNKNOWN
    city_plaides_id: str = ""


class GeographicalAttributeType(Enum):
    STATE = 1
    CITY = 2
    ARCHIVE_NEIGHBORHOOD_OR_SQUARE = 3
    INDICATION_OF_UNKNOWN = 4


class TabletGeographicalInformation(BaseModel):
    """Where the tablet was found."""

    state_supergroup: str = ""
    city: City = Field(default_factory=City)
    sender_city: Optional[str] = ""


# ---------------------------------------------------------------------------
# Chronological models
# ---------------------------------------------------------------------------


class TabletPeriod(BaseModel):
    """Named historical period with approximate year range."""

    period_name: Optional[str] = ""
    period_start_year: Optional[int] = None
    period_end_year: Optional[int] = None


class TabletChronologicalInformation(BaseModel):
    """Chronological dating for a tablet."""

    tablet_period: TabletPeriod = Field(default_factory=TabletPeriod)
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    years_source: Optional[str] = ""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TabletMetadata(BaseModel):
    """All metadata for a single tablet."""

    identifier: str = ""
    project: Optional[str] = None
    id_text: Optional[str] = None
    metadata_raw_dict: Optional[dict] = None
    geographical_information: TabletGeographicalInformation = Field(
        default_factory=TabletGeographicalInformation
    )
    chronological_information: TabletChronologicalInformation = Field(
        default_factory=TabletChronologicalInformation
    )
    archive: Optional[str] = ""
    copyright_information: str = ""
    genre: Optional[str] = ""
    accession_museum_publication_numbers: str = ""
    secondary_literature: str = ""
    credits: str = ""
    cite_as: str = ""


# ---------------------------------------------------------------------------
# Sign / Word / Content models
# ---------------------------------------------------------------------------


class Sign(BaseModel):
    """A single cuneiform sign within a word."""

    role: str = ""  # logographic, phonetic, or determinative
    meaning: str = ""
    breakage: str = ""  # missing, damaged, complete
    optional_delim: Optional[str] = None
    unicode_version: str = ""


class WordSigns(BaseModel):
    """Collection of signs that make up a word, with break statistics."""

    reading: str = ""
    break_percentage: float = -1
    signs: list[Sign] = Field(default_factory=list)


class Word(BaseModel):
    """A single word parsed from an ORACC JSON text.

    Created by traversing the CDL tree and extracting ``l`` (lemma) nodes.
    """

    frag: Optional[str] = None  # transliteration, e.g. "{[na₄]}⸢KIŠIB⸣"
    ref: Optional[str] = None  # reference, e.g. "P527140.2.1"
    inst: Optional[str] = None  # instance, e.g. "kunuk[seal]N"
    form: Optional[str] = None  # form without broken signs
    lemma_form: Optional[str] = None  # lemma, e.g. "kunukku"
    sense: Optional[str] = None  # sense, e.g. "seal"
    norm: Optional[str] = None  # normalization, e.g. "kunuk"
    raw_pos: Optional[str] = None  # raw POS tag, e.g. "N"
    lang: Optional[str] = None  # language code, e.g. "akk-x-neoass"
    sign_dictionaries: Optional[WordSigns] = None
    line: Optional[int] = None
    normalized_pos: Optional[WordPOSInfo] = None
    normalized_language: Optional[Language] = None


# ---------------------------------------------------------------------------
# String representation models
# ---------------------------------------------------------------------------


class UnicodeStringRepresentation(BaseModel):
    """Unicode (cuneiform) text with sign-level statistics."""

    text: str = ""
    dropped_missing_signs: Optional[bool] = None
    dropped_damaged_signs: Optional[bool] = None
    keep_word_segmentation: Optional[bool] = None
    total_chars: int = 0
    included_chars: int = 0


class TextStringRepresentation(BaseModel):
    """Word-level text representation with masking/break statistics."""

    text: Optional[str] = None
    pos_tags_with_mask: Optional[list[str]] = None
    max_break_fraction_used: float = 0
    total_tokens: int = 0
    tokens_without_broken: int = 0


# ---------------------------------------------------------------------------
# Top-level composite models
# ---------------------------------------------------------------------------


class TabletContent(BaseModel):
    """All parsed content for a single tablet."""

    english_translation: str = ""
    words: list[Word] = Field(default_factory=list)
    unicode_str_representation: Optional[UnicodeStringRepresentation] = None
    transliterated_str_representation: Optional[TextStringRepresentation] = None
    lemmatized_str_representation: Optional[TextStringRepresentation] = None
    normalized_str_representation: Optional[TextStringRepresentation] = None


class TabletRecord(BaseModel):
    """Complete record for a single cuneiform tablet (metadata + content)."""

    metadata: TabletMetadata = Field(default_factory=TabletMetadata)
    content: TabletContent = Field(default_factory=TabletContent)
