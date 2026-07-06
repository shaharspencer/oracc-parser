"""Tests for settings module and .env loading."""

import os

import pytest

from oracc_parser.settings import get_settings, data_dir, log_level


class TestSettings:
    """Settings should load with sensible defaults."""

    def test_default_log_level(self):
        assert log_level() == "INFO"

    def test_data_dir_is_path(self):
        d = data_dir()
        assert hasattr(d, "exists")  # It's a Path

    def test_settings_returns_dict(self):
        s = get_settings()
        assert isinstance(s, dict)
        assert "zenodo_record_url" in s
        assert "data_dir" in s
        assert "translations_dir" in s

    def test_runtime_override(self):
        """Module-level variables can be overridden at runtime."""
        import oracc_parser.settings as settings_module
        original = settings_module.LOG_LEVEL
        try:
            settings_module.LOG_LEVEL = "DEBUG"
            assert settings_module.log_level() == "DEBUG"
            assert settings_module.get_settings()["log_level"] == "DEBUG"
        finally:
            settings_module.LOG_LEVEL = original
