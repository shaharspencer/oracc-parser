"""
Configuration for parsing runs.

Controls how broken/damaged signs are handled, which POS tags to mask,
caching behavior, and sample-mode limits.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RunConfig(BaseModel):
    """Configuration object for an oracc-parser run.

    Example::

        config = RunConfig(
            drop_missing=True,
            drop_damaged=False,
            mask_pos=["PN", "DN"],
            limit=10,
        )
    """

    # --- Sign handling (Unicode cuneiform representation only) ---
    drop_missing: bool = Field(
        default=False,
        description=(
            "Drop entirely missing cuneiform signs ([x]) from the Unicode cuneiform output. "
            "Operates sign-by-sign. Does NOT affect transliteration, normalization, or lemmatization."
        ),
    )
    drop_damaged: bool = Field(
        default=False,
        description=(
            "Drop damaged cuneiform signs (⸢x⸣) from the Unicode cuneiform output. "
            "Operates sign-by-sign. Does NOT affect transliteration, normalization, or lemmatization."
        ),
    )
    keep_word_segmentation: bool = Field(
        default=True,
        description="Preserve word boundaries in cuneiform unicode output.",
    )

    # --- Word-level break filtering (transliteration / normalization / lemmatization) ---
    max_break_fraction: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Maximum fraction of a word's signs that may be broken/missing before the entire "
            "word is replaced with 'X' in the transliteration, normalization, and lemmatization "
            "outputs. A value of 0.0 excludes any word with even one broken sign; 1.0 (default) "
            "keeps all words regardless of damage. "
            "This operates at the word level and does NOT affect the Unicode cuneiform output "
            "(use drop_missing / drop_damaged for that)."
        ),
    )

    # --- POS masking ---
    mask_pos: list[str] = Field(
        default_factory=list,
        description=(
            "List of POS tags whose lemma forms should be replaced with a mask token. "
            "Valid tags include: 'PN' (Personal Name), 'DN' (Divine Name), "
            "'GN' (Geographical Name), 'MN' (Month Name), "
            "'SN' (State/City Name), 'N' (Noun), 'V' (Verb), 'AJ' (Adjective), "
            "and others."
        ),
    )

    # --- Translation ---
    fetch_translations: bool = Field(
        default=False,
        description=(
            "Fetch English translations from the ORACC website. "
            "Set to True to include translations in parsed output — requires either "
            "the Zenodo translation cache or live network access to ORACC. "
            "Translations are not included in word CSVs."
        ),
    )

    # --- Caching ---
    use_cache: bool = Field(
        default=True,
        description="Use cached parsed results if available.",
    )
    cache_dir: Optional[str] = Field(
        default=None,
        description=(
            "Directory for cached parsed results. "
            "Defaults to './oracc_cache/' in the current working directory."
        ),
    )

    # --- Sample / limit mode ---
    limit: Optional[int] = Field(
        default=None,
        description="Process only the first N texts. None = process all.",
    )

    # --- Language filter ---
    languages: list[str] = Field(
        default_factory=lambda: ["Akkadian"],
        description=(
            "Languages to include when downloading projects. "
            "Default: ['Akkadian']. Use ['all'] to download everything. "
            "Valid languages include: 'Akkadian', 'Sumerian', 'Hittite', "
            "'Elamite', 'Urartian', 'Old Persian', 'Ugaritic', 'Hurrian', "
            "'Amorite', 'Aramaic', 'Eblaite', 'Greek', 'Egyptian'."
        ),
    )
