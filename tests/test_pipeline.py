"""Tests for reference data loading and convenience functions."""

import pandas as pd
import pytest

from oracc_parser.pipeline import (
    get_full_flat_table,
    get_lemmatizations,
    get_metadata_table,
    get_normalizations,
    get_transliterations,
    get_translations,
    get_unicode_texts,
    reference_data,
)


class TestReferenceData:
    """Reference data should load without errors and have expected shape."""

    def test_provenance_loads(self):
        df = reference_data.get_provenance()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "raw_provenience" in df.columns or len(df.columns) > 0

    def test_period_mapping_loads(self):
        df = reference_data.get_period_mapping()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_sign_list_loads(self):
        df = reference_data.get_sign_list()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 1000  # We know there are ~8900 signs

    def test_pos_tags_loads(self):
        df = reference_data.get_pos_tags()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_languages_loads(self):
        df = reference_data.get_languages()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_projects_metadata_loads(self):
        df = reference_data.get_projects_metadata()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 100  # We know there are ~221 projects


class TestConvenienceFunctions:
    """Granular convenience functions should return flat DataFrames."""

    def test_metadata_table(self, sample_record):
        df = get_metadata_table([sample_record])
        assert len(df) == 1
        assert "id" in df.columns
        assert "provenance" in df.columns
        assert df.iloc[0]["provenance"] == "Nineveh"

    def test_transliterations(self, sample_record):
        df = get_transliterations([sample_record])
        assert len(df) == 1
        assert "transliteration" in df.columns
        assert df.iloc[0]["transliteration"] == "lugal"

    def test_normalizations(self, sample_record):
        df = get_normalizations([sample_record])
        assert len(df) == 1
        assert "normalization" in df.columns
        assert df.iloc[0]["normalization"] == "šarru"

    def test_lemmatizations(self, sample_record):
        df = get_lemmatizations([sample_record])
        assert len(df) == 1
        assert "lemmatization" in df.columns

    def test_unicode_texts(self, sample_record):
        df = get_unicode_texts([sample_record])
        assert len(df) == 1
        assert "unicode" in df.columns
        assert "𒇻" in df.iloc[0]["unicode"]

    def test_translations(self, sample_record):
        df = get_translations([sample_record])
        assert len(df) == 1
        assert "translation" in df.columns

    def test_full_flat_table(self, sample_record):
        df = get_full_flat_table([sample_record])
        assert len(df) == 1
        expected_cols = {
            "id", "project", "text_id", "genre",
            "provenance", "period",
            "transliteration", "normalization", "lemmatization",
            "unicode", "translation",
            "total_tokens", "tokens_without_broken",
        }
        assert expected_cols.issubset(set(df.columns))

    def test_full_flat_table_no_nesting(self, sample_record):
        """The flat table should contain only scalar values, no nested objects."""
        df = get_full_flat_table([sample_record])
        for col in df.columns:
            val = df.iloc[0][col]
            assert not isinstance(val, (dict, list)), (
                f"Column '{col}' contains nested {type(val).__name__}"
            )

    def test_empty_records_returns_empty_df(self):
        df = get_metadata_table([])
        assert len(df) == 0
        df2 = get_full_flat_table([])
        assert len(df2) == 0
