"""Tests for models (RunConfig, tablet data models)."""

import pytest
from pydantic import ValidationError

from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import (
    City,
    Sign,
    TabletContent,
    TabletMetadata,
    TabletRecord,
    Word,
    WordSigns,
)
from oracc_parser.constants import CITY_UNKNOWN


class TestRunConfig:
    """RunConfig should validate and provide sensible defaults."""

    def test_defaults(self):
        config = RunConfig()
        assert config.drop_missing is False
        assert config.drop_damaged is False
        assert config.keep_word_segmentation is True
        assert config.mask_pos == []
        assert config.limit is None
        assert config.languages == ["Akkadian"]

    def test_custom_values(self):
        config = RunConfig(
            drop_missing=True,
            drop_damaged=True,
            mask_pos=["PN", "DN"],
            limit=10,
            languages=["Akkadian", "Sumerian"],
        )
        assert config.drop_missing is True
        assert config.mask_pos == ["PN", "DN"]
        assert config.limit == 10
        assert len(config.languages) == 2

    def test_serialization_roundtrip(self):
        config = RunConfig(limit=5, mask_pos=["GN"])
        json_str = config.model_dump_json()
        restored = RunConfig.model_validate_json(json_str)
        assert restored.limit == 5
        assert restored.mask_pos == ["GN"]


class TestDataModels:
    """Tablet data models should have sensible defaults and structure."""

    def test_city_default(self):
        city = City()
        assert city.city_name == CITY_UNKNOWN
        assert city.city_plaides_id == ""

    def test_sign_creation(self):
        sign = Sign(role="phonetic", meaning="lu", breakage="complete", unicode_version="𒇻")
        assert sign.role == "phonetic"
        assert sign.unicode_version == "𒇻"

    def test_word_with_signs(self, sample_word):
        assert sample_word.frag == "lugal"
        assert sample_word.lemma_form == "šarru"
        assert len(sample_word.sign_dictionaries.signs) == 2
        assert sample_word.sign_dictionaries.break_percentage == 0.0

    def test_tablet_record_structure(self, sample_record):
        assert sample_record.metadata.identifier == "test_P000001"
        assert sample_record.metadata.geographical_information.city.city_name == "Nineveh"
        assert sample_record.content.transliterated_str_representation.text == "lugal"

    def test_word_signs_empty_default(self):
        ws = WordSigns()
        assert ws.signs == []
        assert ws.break_percentage == -1  # -1 means "not computed yet"

    def test_tablet_content_empty(self):
        content = TabletContent()
        assert content.words == []
        assert content.english_translation == ""
