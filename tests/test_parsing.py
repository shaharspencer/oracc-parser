"""Tests for the parsing modules (signs, words, content)."""

import pytest

from oracc_parser.parsing.parse_content import _get_l_nodes, parse_json_text
from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import TabletContent


class TestCDLTraversal:
    """CDL tree traversal should find all lemma nodes."""

    def test_get_l_nodes_finds_word(self, sample_oracc_json):
        nodes = _get_l_nodes(sample_oracc_json)
        assert len(nodes) == 1
        assert "f" in nodes[0]
        assert nodes[0]["f"]["form"] == "lugal"

    def test_get_l_nodes_empty_json(self):
        nodes = _get_l_nodes({})
        assert nodes == []

    def test_get_l_nodes_no_cdl(self):
        nodes = _get_l_nodes({"textid": "P999999", "type": "text"})
        assert nodes == []


class TestParseContent:
    """parse_json_text should produce a TabletContent with words."""

    def test_basic_parse(self, sample_oracc_json):
        result = parse_json_text(sample_oracc_json)
        assert isinstance(result, TabletContent)
        assert len(result.words) == 1
        assert result.words[0].form == "lugal"

    def test_parse_with_config(self, sample_oracc_json):
        config = RunConfig(drop_missing=True, mask_pos=["PN"])
        result = parse_json_text(sample_oracc_json, config)
        assert isinstance(result, TabletContent)
        assert len(result.words) >= 1

    def test_empty_json_returns_empty_content(self):
        result = parse_json_text({})
        assert isinstance(result, TabletContent)
        assert result.words == []

    def test_transliteration_representation(self, sample_oracc_json):
        result = parse_json_text(sample_oracc_json)
        if result.transliterated_str_representation:
            assert isinstance(result.transliterated_str_representation.text, str)
            assert result.transliterated_str_representation.total_tokens >= 1
