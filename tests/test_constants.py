"""Tests for constants and warning messages."""

from oracc_parser.constants import (
    CITY_UNKNOWN,
    LANGUAGE_UNKNOWN,
    POS_NOT_PROVIDED,
    SIGN_BROKEN,
    SIGN_UNICODE_FALLBACK,
    STATE_UNMAPPED,
    warn_no_catalogue_entry,
    warn_unmapped_city,
    warn_unmapped_language,
    warn_unmapped_period,
    warn_unmapped_pos,
    warn_unicode_fallback,
)


class TestSentinelValues:
    """Sentinel values should be consistent strings."""

    def test_city_unknown(self):
        assert CITY_UNKNOWN == "unknown"

    def test_state_unmapped(self):
        assert STATE_UNMAPPED == "unmapped"

    def test_pos_not_provided(self):
        assert POS_NOT_PROVIDED == "NOT_PROVIDED"

    def test_language_unknown(self):
        assert LANGUAGE_UNKNOWN == "unknown"

    def test_sign_fallback(self):
        assert SIGN_UNICODE_FALLBACK == "U"

    def test_sign_broken(self):
        assert SIGN_BROKEN == "X"


class TestWarningMessages:
    """Warning generators should produce informative messages."""

    def test_unmapped_city_message(self):
        msg = warn_unmapped_city("saao/saa01", "Nineveh")
        assert "saao/saa01" in msg
        assert "Nineveh" in msg
        assert CITY_UNKNOWN in msg
        assert "provenience.csv" in msg

    def test_unmapped_pos_message(self):
        msg = warn_unmapped_pos("XYZ")
        assert "XYZ" in msg
        assert POS_NOT_PROVIDED in msg

    def test_unmapped_language_message(self):
        msg = warn_unmapped_language("qux-000")
        assert "qux-000" in msg
        assert LANGUAGE_UNKNOWN in msg

    def test_unmapped_period_message(self):
        msg = warn_unmapped_period("saao/saa01", "Ice Age")
        assert "Ice Age" in msg
        assert "period_mapping.csv" in msg

    def test_no_catalogue_entry(self):
        msg = warn_no_catalogue_entry("saao/saa01", "P999999")
        assert "saao/saa01/P999999" in msg

    def test_unicode_fallback_message(self):
        msg = warn_unicode_fallback("xyz₂", "xyz2")
        assert "xyz₂" in msg
        assert SIGN_UNICODE_FALLBACK in msg
