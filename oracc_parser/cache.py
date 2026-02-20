"""
JSON caching for parsed TabletRecord objects.

Parsed tablets are expensive to produce (long runtimes due to CDL tree
traversal, sign parsing, and translation downloads).  This module caches
the full result including a **config fingerprint**.

On reload:
- If the current config matches the cached fingerprint → **instant return**
  (everything is reused, including string representations)
- If the config differs → the cached **words** are reused and string
  representations are rebuilt (cheap, no re-parsing needed)
- If not cached at all → full parse from scratch

Cache layout::

    {cache_dir}/tablets/{project}/{text_id}.json

Each file is a JSON wrapper::

    {"config_fingerprint": "a1b2c3d4", "record": { ... TabletRecord ... }}
"""

import hashlib
import json
from pathlib import Path

from oracc_parser.utils.logger import get_logger

logger = get_logger()


# ---------------------------------------------------------------------------
# Config fingerprinting
# ---------------------------------------------------------------------------

# These RunConfig fields affect the parsed output.
# Everything else (use_cache, cache_dir, limit, languages) does NOT.
_OUTPUT_AFFECTING_FIELDS = (
    "drop_missing",
    "drop_damaged",
    "keep_word_segmentation",
    "mask_pos",
)


def config_fingerprint(config) -> str:
    """Compute a short, stable hash of the output-affecting config options.

    Args:
        config: A ``RunConfig`` instance.

    Returns:
        8-char hex string (e.g. ``"a1b2c3d4"``).
    """
    key = {}
    for field in _OUTPUT_AFFECTING_FIELDS:
        val = getattr(config, field)
        if isinstance(val, list):
            val = sorted(val)
        key[field] = val

    raw = json.dumps(key, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _resolve_cache_dir(cache_dir: str | None = None) -> Path:
    """Return the base cache directory."""
    if cache_dir:
        return Path(cache_dir)
    from oracc_parser.settings import cache_dir as settings_cache_dir
    return settings_cache_dir()


def _tablet_path(
    project: str,
    text_id: str,
    cache_dir: str | None = None,
) -> Path:
    """Return the JSON file path for a cached tablet."""
    base = _resolve_cache_dir(cache_dir) / "tablets"
    project_dir = project.replace("/", "-")
    return base / project_dir / f"{text_id}.json"


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------


def load_cached_tablet(
    project: str,
    text_id: str,
    config,
    cache_dir: str | None = None,
) -> "TabletRecord | None":
    """Load a cached tablet, rebuilding string reps only if config changed.

    Two fast paths:

    1. **Config match** — the cached fingerprint matches the current config.
       The full record (including string representations) is returned as-is.
       This is the fastest path.

    2. **Config mismatch** — the words and metadata are reused, but string
       representations are rebuilt with the current config.  This avoids
       the expensive CDL parsing + translation download.

    Args:
        project: ORACC project path, e.g. ``"saao/saa01"``.
        text_id: Text identifier, e.g. ``"P334189"``.
        config: ``RunConfig`` instance.
        cache_dir: Custom cache directory (overrides settings).

    Returns:
        The TabletRecord (possibly with rebuilt strings), or ``None``.
    """
    from oracc_parser.models.tablet import TabletRecord
    from oracc_parser.parsing.parse_content import (
        _add_word_level_representations,
        _add_unicode_representation,
    )

    path = _tablet_path(project, text_id, cache_dir)
    if not path.exists():
        return None

    try:
        raw = path.read_text(encoding="utf-8")
        wrapper = json.loads(raw)

        # Handle both new wrapper format and legacy bare-record format
        if "record" in wrapper and "config_fingerprint" in wrapper:
            cached_fp = wrapper["config_fingerprint"]
            record = TabletRecord.model_validate(wrapper["record"])
        else:
            # Legacy format (bare TabletRecord JSON) — always rebuild
            cached_fp = None
            record = TabletRecord.model_validate(wrapper)

        current_fp = config_fingerprint(config)

        if cached_fp == current_fp:
            # Fast path: config matches → everything is valid
            return record

        # Config changed → rebuild string representations from cached words
        record.content = _add_word_level_representations(
            record.content, config.mask_pos
        )
        record.content = _add_unicode_representation(
            record.content,
            drop_missing=config.drop_missing,
            drop_damaged=config.drop_damaged,
            keep_segmentation=config.keep_word_segmentation,
        )
        return record

    except Exception as e:
        logger.warning(f"Corrupt cache file {path}, will re-parse: {e}")
        path.unlink(missing_ok=True)
        return None


def save_tablet_to_cache(
    record: "TabletRecord",
    project: str,
    text_id: str,
    config,
    cache_dir: str | None = None,
) -> None:
    """Persist a TabletRecord to the JSON cache with a config fingerprint.

    The saved file includes the config fingerprint so that on reload
    we can skip string rebuilding when the config hasn't changed.

    Args:
        record: The parsed tablet to cache.
        project: ORACC project path.
        text_id: Text identifier.
        config: ``RunConfig`` instance (its fingerprint is stored).
        cache_dir: Custom cache directory.
    """
    path = _tablet_path(project, text_id, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    wrapper = {
        "config_fingerprint": config_fingerprint(config),
        "record": record.model_dump(mode="python"),
    }

    try:
        path.write_text(
            json.dumps(wrapper, indent=1, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning(f"Failed to write cache file {path}: {e}")


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------


def clear_project_cache(
    project: str | None = None,
    cache_dir: str | None = None,
) -> int:
    """Delete cached JSON files for a project (or all projects).

    Args:
        project: ORACC project path.  ``None`` = clear everything.
        cache_dir: Custom cache directory.

    Returns:
        Number of tablet JSON files deleted.
    """
    base = _resolve_cache_dir(cache_dir) / "tablets"
    if not base.exists():
        return 0

    if project:
        target = base / project.replace("/", "-")
    else:
        target = base

    if not target.exists():
        return 0

    count = 0
    for f in target.rglob("*.json"):
        f.unlink()
        count += 1

    # Clean up empty directories (bottom-up)
    for d in sorted(target.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if project and target.exists() and not any(target.iterdir()):
        target.rmdir()

    logger.info(f"Cleared {count} cached tablet(s)")
    return count
