"""
Convert parsed Word/Sign data into final string representations.

Two levels of text building
----------------------------
1. **Word-level** — ``words_to_text()``
   Produces transliteration, normalization, and lemmatization strings.
   Break filtering here is *word-granularity*: each word has a
   ``break_perc`` that represents the fraction of its signs that are
   missing or damaged.  Words whose ``break_perc`` exceeds
   ``max_break_fraction`` are replaced wholesale with ``'X'``.
   Controlled via ``RunConfig.max_break_fraction``.

2. **Sign-level** — ``signs_to_unicode()``
   Produces the Unicode cuneiform string.
   Break filtering here is *sign-granularity*: individual signs are
   replaced with ``X`` (or kept) based on their breakage state
   (``"missing"`` / ``"damaged"``).  Controlled via
   ``RunConfig.drop_missing`` and ``RunConfig.drop_damaged``.

.. note::
   Because the two levels use different granularities, **the text versions
   and the Unicode version are not necessarily aligned**.  A word kept
   intact in the transliteration (because its average break fraction is
   below the threshold) may still have individual signs replaced with
   ``X`` in the Unicode output, and vice-versa.
"""

from typing import Any

import pandas as pd

from oracc_parser.utils.logger import get_logger

logger = get_logger()

NUM_COLUMN = "NUM"


# ---------------------------------------------------------------------------
# Word-level text building
# ---------------------------------------------------------------------------


def words_to_text(
    df: pd.DataFrame,
    column: str,
    pos_tags_to_mask: list[str],
    max_break_fraction: float = 1.0,
) -> tuple[str, int, int]:
    """Convert a DataFrame of words into a single text string.

    Args:
        df: DataFrame with columns: ``norm``, ``lemma_form``, ``sense``,
            ``pos``, ``break_perc``, ``line``, and the target ``column``.
        column: Column to extract words from (e.g. ``"frag"``, ``"norm"``).
        pos_tags_to_mask: POS tags whose tokens should be replaced by tag name.
        max_break_fraction: Only include words with ``break_perc <= this``.

    Returns:
        ``(text, total_tokens, tokens_without_broken)``
    """
    working = df.copy()
    if column not in {"norm", "lemma_form", "sense", "pos"}:
        working = working.drop_duplicates(subset="ref")
    working[column] = working[column].replace("", "UNK")

    # Mask chosen POS tags
    if "pos" in working.columns and pos_tags_to_mask:
        mask = working["pos"].isin(pos_tags_to_mask)
        working.loc[mask, column] = working.loc[mask, "pos"]

    # Mask NUM tokens
    num_mask = working[column] == NUM_COLUMN
    working.loc[num_mask, column] = NUM_COLUMN

    # Filter by break percentage
    if working["break_perc"].dtype == object:
        working = working[working["break_perc"] != ""]
    working["break_perc"] = pd.to_numeric(working["break_perc"], errors="coerce")
    working = working.dropna(subset=["break_perc"])
    break_mask = working["break_perc"] <= max_break_fraction
    working.loc[~break_mask, column] = "X"

    # Build multi-line text
    text_lines = []
    for _, line_df in working.groupby("line"):
        words = [w for w in line_df[column].tolist() if w]
        if words:
            text_lines.append(" ".join(words).strip())
    text = "\n".join(text_lines)

    total = len(working)
    broken = int(working[column].isin({"UNK", "X", "x"}).sum())
    return text, total, total - broken


# ---------------------------------------------------------------------------
# Sign-level (Unicode cuneiform) text building
# ---------------------------------------------------------------------------


def signs_to_unicode(
    df: pd.DataFrame,
    drop_missing: bool = True,
    drop_damaged: bool = False,
    keep_word_segmentation: bool = False,
) -> tuple[str, int, int]:
    """Convert a DataFrame of sign data into a Unicode cuneiform string.

    Args:
        df: DataFrame with ``unicode`` (list[str]), ``break`` (list[str]),
            and ``line`` (int) columns.
        drop_missing: Replace signs marked ``"missing"`` with ``X``.
        drop_damaged: Replace signs marked ``"damaged"`` with ``X``.
        keep_word_segmentation: Preserve word boundaries with spaces.

    Returns:
        ``(text, total_chars, included_chars)``
    """
    def _apply(state: str, ch: Any) -> str:
        """Return the character to emit for this sign.

        Complete signs pass through unchanged.  Missing/damaged signs are
        replaced with ``X`` when the corresponding flag is set; otherwise
        they pass through (damaged) or are kept as-is (missing).
        """
        if state == "complete":
            return ch
        if state == "missing":
            return "X" if drop_missing else ch
        if state == "damaged":
            if drop_damaged:
                return "X"
            return "" if ch == "x" else ch
        return ch

    total_chars = 0
    included_chars = 0
    lines: list[str] = []

    for _, line_df in df.groupby("line"):
        unicode_seq = line_df["unicode"].tolist()
        break_states = line_df["break"].tolist()

        for word_chars in unicode_seq:
            total_chars += len(word_chars)

        if keep_word_segmentation:
            word_strs = []
            for word_chars, states in zip(unicode_seq, break_states):
                rendered = "".join(_apply(st, ch) for ch, st in zip(word_chars, states))
                complete = sum(1 for ch, st in zip(word_chars, states) if st == "complete")
                included_chars += complete
                if rendered:
                    word_strs.append(rendered)
            filtered_line = " ".join(word_strs)
        else:
            filtered_line = "".join(
                _apply(st, ch)
                for word_chars, states in zip(unicode_seq, break_states)
                for ch, st in zip(word_chars, states)
            )
            included_chars += sum(
                1
                for word_chars, states in zip(unicode_seq, break_states)
                for ch, st in zip(word_chars, states)
                if st == "complete"
            )

        if filtered_line:
            lines.append(filtered_line)

    return "\n".join(lines), total_chars, included_chars
