"""
oracc-parser: Download and parse ORACC cuneiform text projects.
"""
from __future__ import annotations

__version__ = "0.1.3"

# Public re-exports for convenience
from oracc_parser.pipeline import (  # noqa: F401
    export_to_csv,
    export_to_jsonl,
    parse_project,
    records_to_word_dataframes,
    save_project_catalogue,
    load_project_catalogue,
    reference_data,
    get_metadata_table,
    get_transliterations,
    get_normalizations,
    get_lemmatizations,
    get_unicode_texts,
    get_translations,
    get_full_flat_table,
)
from oracc_parser.io.word_csv import (  # noqa: F401
    save_word_csv,
)
from oracc_parser.models.config import RunConfig  # noqa: F401
from oracc_parser.metadata.populate import enrich_catalogue_df  # noqa: F401
from oracc_parser.download.pleiades import PleiadesData  # noqa: F401

