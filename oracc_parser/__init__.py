"""
oracc-parser: Download and parse ORACC cuneiform text projects.
"""

__version__ = "0.1.0"

# Public re-exports for convenience
from oracc_parser.pipeline import (  # noqa: F401
    export_to_csv,
    export_to_jsonl,
    parse_project,
    reference_data,
    get_metadata_table,
    get_transliterations,
    get_normalizations,
    get_lemmatizations,
    get_unicode_texts,
    get_translations,
    get_full_flat_table,
)
from oracc_parser.models.config import RunConfig  # noqa: F401
from oracc_parser.download.pleiades import PleiadesData  # noqa: F401

