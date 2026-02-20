"""
Shared test fixtures for oracc-parser test suite.

To run all tests:
    cd oracc-parser
    pytest tests/ -v

To run with coverage:
    pytest tests/ --cov=oracc_parser --cov-report=term-missing
"""

import json
import pytest

from oracc_parser.models.config import RunConfig
from oracc_parser.models.tablet import (
    City,
    Sign,
    TabletContent,
    TabletMetadata,
    TabletRecord,
    TextStringRepresentation,
    UnicodeStringRepresentation,
    Word,
    WordPOSInfo,
    WordSigns,
)


# ---------------------------------------------------------------------------
# Minimal ORACC JSON fixture (a single word "lugal" = king)
# ---------------------------------------------------------------------------


SAMPLE_ORACC_JSON = {
    "textid": "P000001",
    "type": "text",
    "cdl": [
        {
            "node": "c.1",
            "type": "discourse",
            "cdl": [
                {
                    "node": "c.1.1",
                    "type": "sentence",
                    "cdl": [
                        {
                            "node": "l.1",
                            "frag": "lugal",
                            "inst": "lugal[king]N",
                            "f": {
                                "form": "lugal",
                                "lang": "akk",
                                "delim": " ",
                                "pos": "N",
                                "epos": "N",
                                "norm": "šarru",
                                "sense": "king",
                                "cf": "šarru",
                                "gw": "king",
                                "gdl": [
                                    {
                                        "v": "lu",
                                        "utf8": "𒇻",
                                        "break": "complete",
                                    },
                                    {
                                        "v": "gal",
                                        "utf8": "𒃲",
                                        "break": "complete",
                                        "delim": " ",
                                    },
                                ],
                            },
                        }
                    ],
                }
            ],
        }
    ],
}


@pytest.fixture
def sample_oracc_json():
    """A minimal ORACC JSON dict with one word."""
    return SAMPLE_ORACC_JSON.copy()


@pytest.fixture
def sample_config():
    """Default RunConfig for testing."""
    return RunConfig(limit=5)


@pytest.fixture
def sample_word():
    """A pre-built Word object."""
    return Word(
        frag="lugal",
        ref="P000001.1",
        inst="lugal[king]N",
        form="lugal",
        lemma_form="šarru",
        sense="king",
        norm="šarru",
        raw_pos="N",
        lang="akk",
        line=1,
        normalized_pos=WordPOSInfo(raw_pos="N", normalized_pos="N"),
        sign_dictionaries=WordSigns(
            signs=[
                Sign(
                    role="phonetic",
                    meaning="lu",
                    breakage="complete",
                    unicode_version="𒇻",
                ),
                Sign(
                    role="phonetic",
                    meaning="gal",
                    breakage="complete",
                    unicode_version="𒃲",
                    optional_delim=" ",
                ),
            ],
            break_percentage=0.0,
        ),
    )


@pytest.fixture
def sample_record(sample_word):
    """A pre-built TabletRecord with one word."""
    content = TabletContent(words=[sample_word])
    content.transliterated_str_representation = TextStringRepresentation(
        text="lugal",
        total_tokens=1,
        tokens_without_broken=1,
    )
    content.normalized_str_representation = TextStringRepresentation(
        text="šarru",
        total_tokens=1,
        tokens_without_broken=1,
    )
    content.unicode_str_representation = UnicodeStringRepresentation(
        text="𒇻𒃲",
        total_chars=2,
        included_chars=2,
    )
    metadata = TabletMetadata(
        identifier="test_P000001",
        project="test",
        id_text="P000001",
    )
    metadata.geographical_information.city = City(city_name="Nineveh")
    return TabletRecord(content=content, metadata=metadata)
