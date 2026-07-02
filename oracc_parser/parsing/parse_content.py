"""
Parse a single ORACC JSON text into a TabletContent object.

Orchestrates CDL tree traversal, word parsing, and text building
(transliteration, lemmatization, normalization, unicode).
"""
from __future__ import annotations

import pandas as pd

from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import (
    TabletContent,
    TextStringRepresentation,
    UnicodeStringRepresentation,
    Word,
)
from oracc_parser.parsing.parse_words import parse_word
from oracc_parser.parsing.text_builder import signs_to_unicode, words_to_text
from oracc_parser.utils.logger import get_logger

logger = get_logger()


def parse_json_text(js: dict, config: RunConfig | None = None) -> TabletContent:
    """Parse an ORACC JSON text dict into a TabletContent object.

    Args:
        js: The full JSON dict for a single ORACC text.
        config: RunConfig controlling sign/masking options.

    Returns:
        TabletContent with words and string representations.
    """
    if config is None:
        config = RunConfig()

    result = TabletContent()

    try:
        # 1. Extract word list from CDL tree
        l_nodes = _get_l_nodes(js)
        result.words = [parse_word(node) for node in l_nodes]

        # 2. Build word-level string representations
        result = _add_word_level_representations(
            result, config.mask_pos, config.max_break_fraction
        )

        # 3. Build sign-level (Unicode) string representation
        result = _add_unicode_representation(
            result,
            drop_missing=config.drop_missing,
            drop_damaged=config.drop_damaged,
            keep_segmentation=config.keep_word_segmentation,
            mask_pos=config.mask_pos,
        )
    except Exception as e:
        text_id = js.get("textid", "unknown")
        logger.error(f"Error parsing text {text_id}: {e}")

    return result


def _get_l_nodes(js: dict) -> list[dict]:
    """Traverse the CDL tree and collect all ``l`` (lemma) nodes.

    These are dicts containing an ``"f"`` key with sign/word information.
    """
    nodes = []

    def _traverse(node):
        if isinstance(node, dict):
            if "f" in node:
                nodes.append(node)
            for child in node.get("cdl", []):
                _traverse(child)

    _traverse(js)
    return nodes


def _add_word_level_representations(
    result: TabletContent, mask_pos: list[str], max_break_fraction: float = 1.0
) -> TabletContent:
    """Add transliterated, lemmatized, and normalized string representations.

    Words whose break percentage exceeds ``max_break_fraction`` are replaced
    with ``'X'`` in all three text outputs.  This operates at the word level
    and is independent of the sign-level ``drop_missing`` / ``drop_damaged``
    flags which only affect the Unicode cuneiform output.
    """
    if not result.words:
        return result

    word_df = _words_to_dataframe(result.words)

    for column, attr in [
        ("frag", "transliterated_str_representation"),
        ("lemma_form", "lemmatized_str_representation"),
        ("norm", "normalized_str_representation"),
    ]:
        text, total, without_broken = words_to_text(
            df=word_df,
            column=column,
            pos_tags_to_mask=mask_pos,
            max_break_fraction=max_break_fraction,
        )
        setattr(
            result,
            attr,
            TextStringRepresentation(
                text=text,
                pos_tags_with_mask=mask_pos,
                max_break_fraction_used=max_break_fraction,
                total_tokens=total,
                tokens_without_broken=without_broken,
            ),
        )
    return result


def _add_unicode_representation(
    result: TabletContent,
    drop_missing: bool,
    drop_damaged: bool,
    keep_segmentation: bool,
    mask_pos: list[str] | None = None,
) -> TabletContent:
    """Add Unicode cuneiform string representation."""
    mask_pos = mask_pos or []
    sign_rows = []
    for word in result.words:
        if not word.sign_dictionaries or not word.sign_dictionaries.signs:
            continue
        word_pos = word.normalized_pos.normalized_pos if word.normalized_pos else ""
        if word_pos in mask_pos:
            continue
        sign_rows.append({
            "unicode": [s.unicode_version for s in word.sign_dictionaries.signs],
            "break": [s.breakage for s in word.sign_dictionaries.signs],
            "line": word.line,
        })

    if not sign_rows:
        return result

    sign_df = pd.DataFrame(sign_rows)
    text, total, included = signs_to_unicode(
        df=sign_df,
        drop_missing=drop_missing,
        drop_damaged=drop_damaged,
        keep_word_segmentation=keep_segmentation,
    )
    result.unicode_str_representation = UnicodeStringRepresentation(
        text=text,
        dropped_missing_signs=drop_missing,
        dropped_damaged_signs=drop_damaged,
        keep_word_segmentation=keep_segmentation,
        pos_tags_with_mask=mask_pos or None,
        total_chars=total,
        included_chars=included,
    )
    return result


def _words_to_dataframe(words: list[Word]) -> pd.DataFrame:
    """Convert a list of Word objects into a DataFrame for text building."""
    rows = []
    for w in words:
        rows.append({
            "ref": w.ref,
            "frag": w.frag or "",
            "norm": w.norm or "",
            "lemma_form": w.lemma_form or "",
            "sense": w.sense or "",
            "pos": w.normalized_pos.normalized_pos if w.normalized_pos else "",
            "break_perc": w.sign_dictionaries.break_percentage if w.sign_dictionaries else 0,
            "line": w.line or 0,
        })
    return pd.DataFrame(rows)
