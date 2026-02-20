"""Tests for oracc_parser.cache — config-independent caching with on-load rebuild."""

from pathlib import Path

import pytest

from oracc_parser.cache import (
    clear_project_cache,
    config_fingerprint,
    load_cached_tablet,
    save_tablet_to_cache,
    _tablet_path,
)
from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import (
    Sign,
    TabletRecord,
    TabletContent,
    TabletMetadata,
    TextStringRepresentation,
    Word,
    WordPOSInfo,
    WordSigns,
)


@pytest.fixture
def cache_dir(tmp_path):
    return str(tmp_path / "test_cache")


@pytest.fixture
def default_config():
    return RunConfig()


@pytest.fixture
def sample_record():
    """Create a TabletRecord with words that allow string regeneration."""
    record = TabletRecord()
    record.metadata = TabletMetadata(
        identifier="test_tablet",
        project="saao/saa01",
        id_text="P334189",
        genre="Letter",
    )

    # Create words with signs so unicode + text reps can be rebuilt
    words = [
        Word(
            frag="a-na",
            ref="P334189.1.1",
            lemma_form="ana",
            norm="ana",
            raw_pos="PRP",
            lang="akk-x-neoass",
            line=1,
            normalized_pos=WordPOSInfo(meaning="to", normalized_pos="PRP"),
            sign_dictionaries=WordSigns(
                reading="a-na",
                break_percentage=0.0,
                signs=[
                    Sign(role="phonetic", meaning="a", breakage="complete",
                         unicode_version="\U00012000"),
                    Sign(role="phonetic", meaning="na", breakage="complete",
                         unicode_version="\U0001223E"),
                ],
            ),
        ),
        Word(
            frag="{m}sargon",
            ref="P334189.1.2",
            lemma_form="sargon",
            norm="sargon",
            raw_pos="PN",
            lang="akk-x-neoass",
            line=1,
            normalized_pos=WordPOSInfo(
                meaning="Sargon", normalized_pos="PN",
                to_mask=False, mask_as=""
            ),
            sign_dictionaries=WordSigns(
                reading="sargon", break_percentage=0.0, signs=[]
            ),
        ),
    ]

    record.content = TabletContent(
        english_translation="To Sargon",
        words=words,
        transliterated_str_representation=TextStringRepresentation(
            text="a-na {m}sargon", total_tokens=2, tokens_without_broken=2,
        ),
    )
    return record


# ---------------------------------------------------------------------------
# Path structure — simple, no fingerprinting
# ---------------------------------------------------------------------------


class TestTabletPath:
    def test_path_structure(self, cache_dir):
        path = _tablet_path("saao/saa01", "P334189", cache_dir)
        expected = Path(cache_dir) / "tablets" / "saao-saa01" / "P334189.json"
        assert path == expected

    def test_one_path_per_tablet(self, cache_dir):
        """Path is the same regardless of config."""
        p1 = _tablet_path("blms", "P1", cache_dir)
        p2 = _tablet_path("blms", "P1", cache_dir)
        assert p1 == p2


# ---------------------------------------------------------------------------
# Save / Load roundtrip
# ---------------------------------------------------------------------------


class TestSaveAndLoad:
    def test_roundtrip_preserves_words(self, cache_dir, default_config, sample_record):
        """Words and metadata survive cache roundtrip."""
        save_tablet_to_cache(sample_record, "saao/saa01", "P334189", default_config, cache_dir)
        loaded = load_cached_tablet("saao/saa01", "P334189", default_config, cache_dir)

        assert loaded is not None
        assert loaded.metadata.identifier == "test_tablet"
        assert loaded.metadata.genre == "Letter"
        assert loaded.content.english_translation == "To Sargon"
        assert len(loaded.content.words) == 2
        assert loaded.content.words[0].frag == "a-na"
        assert loaded.content.words[1].frag == "{m}sargon"

    def test_string_reps_rebuilt_on_load(self, cache_dir, sample_record):
        """String reps are regenerated from words, not loaded from cache blindly."""
        save_tablet_to_cache(sample_record, "saao/saa01", "P1", RunConfig(), cache_dir)

        # Load with mask_pos=["PN"] — should mask the PN word
        config_masked = RunConfig(mask_pos=["PN"])
        loaded = load_cached_tablet("saao/saa01", "P1", config_masked, cache_dir)

        assert loaded is not None
        # The transliteration should now contain [PN] mask
        t_rep = loaded.content.transliterated_str_representation
        assert t_rep is not None
        assert "PN" in t_rep.text

    def test_same_cache_different_configs(self, cache_dir, sample_record):
        """Same cached file serves different configs correctly."""
        save_tablet_to_cache(sample_record, "proj", "P1", RunConfig(), cache_dir)

        # Load with default (no masking)
        loaded_default = load_cached_tablet("proj", "P1", RunConfig(), cache_dir)
        # Load with PN masking
        loaded_masked = load_cached_tablet("proj", "P1", RunConfig(mask_pos=["PN"]), cache_dir)

        assert loaded_default is not None
        assert loaded_masked is not None

        # Both exist, but transliteration text should differ
        text_default = loaded_default.content.transliterated_str_representation.text
        text_masked = loaded_masked.content.transliterated_str_representation.text
        assert text_default != text_masked

    def test_cache_miss(self, cache_dir, default_config):
        result = load_cached_tablet("saao/saa01", "NONEXISTENT", default_config, cache_dir)
        assert result is None

    def test_corrupt_file_returns_none(self, cache_dir, default_config):
        path = _tablet_path("saao/saa01", "CORRUPT", cache_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("NOT VALID JSON {{{{", encoding="utf-8")

        result = load_cached_tablet("saao/saa01", "CORRUPT", default_config, cache_dir)
        assert result is None
        assert not path.exists()


# ---------------------------------------------------------------------------
# Clear cache
# ---------------------------------------------------------------------------


class TestClearCache:
    def test_clear_project(self, cache_dir, default_config, sample_record):
        save_tablet_to_cache(sample_record, "saao/saa01", "P1", default_config, cache_dir)
        save_tablet_to_cache(sample_record, "saao/saa01", "P2", default_config, cache_dir)
        save_tablet_to_cache(sample_record, "blms", "P3", default_config, cache_dir)

        deleted = clear_project_cache("saao/saa01", cache_dir)
        assert deleted == 2
        assert load_cached_tablet("blms", "P3", default_config, cache_dir) is not None
        assert load_cached_tablet("saao/saa01", "P1", default_config, cache_dir) is None

    def test_clear_all(self, cache_dir, default_config, sample_record):
        save_tablet_to_cache(sample_record, "saao/saa01", "P1", default_config, cache_dir)
        save_tablet_to_cache(sample_record, "blms", "P2", default_config, cache_dir)

        deleted = clear_project_cache(project=None, cache_dir=cache_dir)
        assert deleted == 2
        assert load_cached_tablet("saao/saa01", "P1", default_config, cache_dir) is None

    def test_clear_empty(self, cache_dir):
        assert clear_project_cache(project=None, cache_dir=cache_dir) == 0
