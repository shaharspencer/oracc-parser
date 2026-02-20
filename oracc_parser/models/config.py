"""
Configuration for parsing runs.

Controls how broken/damaged signs are handled, which POS tags to mask,
caching behavior, and sample-mode limits.
"""

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

    # --- Sign handling ---
    drop_missing: bool = Field(
        default=False,
        description="Drop entirely missing cuneiform signs ([x]) from unicode text.",
    )
    drop_damaged: bool = Field(
        default=False,
        description="Drop damaged cuneiform signs (⸢x⸣) from unicode text.",
    )
    keep_word_segmentation: bool = Field(
        default=True,
        description="Preserve word boundaries in cuneiform unicode output.",
    )

    # --- POS masking ---
    mask_pos: list[str] = Field(
        default_factory=list,
        description=(
            "List of POS tags whose lemma forms should be replaced with a mask token. "
            "Common choices: 'PN' (Personal Name), 'DN' (Divine Name), "
            "'GN' (Geographical Name), 'RN' (Royal Name)."
        ),
    )

    # --- Caching ---
    use_cache: bool = Field(
        default=True,
        description="Use cached parsed results if available.",
    )
    cache_dir: str | None = Field(
        default=None,
        description=(
            "Directory for cached parsed results. "
            "Defaults to './oracc_cache/' in the current working directory."
        ),
    )

    # --- Sample / limit mode ---
    limit: int | None = Field(
        default=None,
        description="Process only the first N texts. None = process all.",
    )

    # --- Language filter ---
    languages: list[str] = Field(
        default_factory=lambda: ["Akkadian"],
        description=(
            "Languages to include when downloading projects. "
            "Default: ['Akkadian']. Use ['all'] to download everything."
        ),
    )
